"""Celery tasks for metric collection"""

import logging
from datetime import datetime

from sqlalchemy import select, insert
from sqlalchemy.orm import Session

from collector.celery_app import celery_app
from db import async_session
from db.models import (
    Instance, Metric, ActiveSession, Lock, SlowQuery, AlertHistory, AlertRule
)
from db.oracle_client import OracleConnectionPool, OracleMetricsCollector
from app.config import settings
from cache.redis_cache import redis_cache
from alerts.engine import AlertEngine

logger = logging.getLogger(__name__)

# Global pool managers
_oracle_pools = {}


def _get_or_create_pool(instance: Instance) -> OracleConnectionPool:
    """Get or create Oracle connection pool for instance"""
    if instance.id not in _oracle_pools:
        try:
            # Decrypt password (simplified - implement proper encryption in production)
            password = instance.password_encrypted.decode('utf-8')

            pool = OracleConnectionPool(
                username=instance.username,
                password=password,
                host=instance.host,
                port=instance.port,
                service_name=instance.service_name,
                min_connections=instance.pool_min,
                max_connections=instance.pool_max,
                timeout=instance.connection_timeout,
                instance_name=instance.name,
            )
            _oracle_pools[instance.id] = pool
        except Exception as e:
            logger.error(f"Failed to create pool for {instance.name}: {e}")
            raise

    return _oracle_pools[instance.id]


@celery_app.task(bind=True, max_retries=3)
def collect_critical_metrics(self):
    """
    Collect critical metrics: active sessions, locks (10s frequency)
    """
    try:
        import asyncio
        asyncio.run(_collect_critical_metrics_async())
    except Exception as exc:
        logger.error(f"Critical metrics collection failed: {exc}")
        raise self.retry(exc=exc, countdown=5)


async def _collect_critical_metrics_async():
    """Async implementation of critical metrics collection"""
    async with async_session() as session:
        stmt = select(Instance).where(Instance.enabled == True)
        result = await session.execute(stmt)
        instances = result.scalars().all()

        for instance in instances:
            try:
                pool = _get_or_create_pool(instance)

                if not pool.is_connected:
                    logger.warning(f"Skipping collection for {instance.name} - not connected")
                    continue

                collector = OracleMetricsCollector(pool)

                # Collect active sessions
                sessions = await collector.collect_active_sessions()
                await _store_active_sessions(session, instance.id, sessions)

                # Collect locks
                locks = await collector.collect_locks()
                await _store_locks(session, instance.id, locks)

                # Cache results
                await redis_cache.set_json(
                    f"instance:{instance.id}:sessions:latest",
                    {"count": len(sessions), "timestamp": datetime.utcnow().isoformat()},
                    ttl=30
                )

                await redis_cache.set_json(
                    f"instance:{instance.id}:locks:latest",
                    {"count": len(locks), "timestamp": datetime.utcnow().isoformat()},
                    ttl=30
                )

                logger.info(f"Critical metrics collected for {instance.name}")

            except Exception as e:
                logger.error(f"Error collecting critical metrics for {instance.name}: {e}")

        await session.commit()


@celery_app.task(bind=True, max_retries=3)
def collect_standard_metrics(self):
    """
    Collect standard metrics: CPU, memory, connections (30s frequency)
    """
    try:
        import asyncio
        asyncio.run(_collect_standard_metrics_async())
    except Exception as exc:
        logger.error(f"Standard metrics collection failed: {exc}")
        raise self.retry(exc=exc, countdown=10)


async def _collect_standard_metrics_async():
    """Async implementation of standard metrics collection"""
    async with async_session() as session:
        stmt = select(Instance).where(Instance.enabled == True)
        result = await session.execute(stmt)
        instances = result.scalars().all()

        for instance in instances:
            try:
                pool = _get_or_create_pool(instance)

                if not pool.is_connected:
                    continue

                collector = OracleMetricsCollector(pool)

                # Collect CPU usage
                cpu = await collector.collect_cpu_usage()
                if cpu is not None:
                    await _store_metric(session, instance.id, 'cpu_usage', cpu, 'percent')

                # Collect memory usage
                memory = await collector.collect_memory_usage()
                for mem_type, value in memory.items():
                    await _store_metric(session, instance.id, f'memory_{mem_type}', value, 'MB')

                # Collect tablespace usage (brief)
                tablespaces = await collector.collect_tablespace_usage()
                for ts in tablespaces:
                    await _store_metric(
                        session,
                        instance.id,
                        'tablespace_usage',
                        ts.get('used_percent', 0),
                        'percent',
                        tags={'tablespace_name': ts.get('tablespace_name')}
                    )

                logger.info(f"Standard metrics collected for {instance.name}")

            except Exception as e:
                logger.error(f"Error collecting standard metrics for {instance.name}: {e}")

        await session.commit()


@celery_app.task(bind=True, max_retries=3)
def collect_historical_metrics(self):
    """
    Collect historical metrics: slow queries, system events (5min frequency)
    """
    try:
        import asyncio
        asyncio.run(_collect_historical_metrics_async())
    except Exception as exc:
        logger.error(f"Historical metrics collection failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


async def _collect_historical_metrics_async():
    """Async implementation of historical metrics collection"""
    async with async_session() as session:
        stmt = select(Instance).where(Instance.enabled == True)
        result = await session.execute(stmt)
        instances = result.scalars().all()

        for instance in instances:
            try:
                pool = _get_or_create_pool(instance)

                if not pool.is_connected:
                    continue

                collector = OracleMetricsCollector(pool)

                # Collect slow queries
                queries = await collector.collect_slow_queries(
                    threshold_ms=settings.SLOW_QUERY_THRESHOLD_MS
                )
                await _store_slow_queries(session, instance.id, queries)

                logger.info(f"Historical metrics collected for {instance.name}")

            except Exception as e:
                logger.error(f"Error collecting historical metrics for {instance.name}: {e}")

        await session.commit()


@celery_app.task
def evaluate_alerts():
    """
    Evaluate alert rules against recent metrics
    """
    try:
        import asyncio
        asyncio.run(_evaluate_alerts_async())
    except Exception as e:
        logger.error(f"Alert evaluation failed: {e}")


async def _evaluate_alerts_async():
    """Async alert evaluation"""
    async with async_session() as session:
        stmt = select(AlertRule).where(AlertRule.enabled == True)
        result = await session.execute(stmt)
        rules = result.scalars().all()

        engine = AlertEngine()

        for rule in rules:
            try:
                # Get latest metric
                metric_stmt = select(Metric).where(
                    (Metric.instance_id == rule.instance_id) &
                    (Metric.metric_type == rule.metric_type)
                ).order_by(Metric.collected_at.desc()).limit(1)

                metric_result = await session.execute(metric_stmt)
                metric = metric_result.scalar_one_or_none()

                if metric:
                    triggered = engine.evaluate_rule(rule, metric.metric_value)

                    if triggered:
                        # Create alert history entry
                        alert = AlertHistory(
                            rule_id=rule.id,
                            triggered_at=datetime.utcnow(),
                            metric_value=metric.metric_value,
                            metric_unit=metric.metric_unit,
                            status='triggered'
                        )
                        session.add(alert)
                        logger.info(f"Alert triggered for rule: {rule.name}")

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.id}: {e}")

        await session.commit()


# Helper functions

async def _store_metric(
    session: Session,
    instance_id,
    metric_type: str,
    value: float,
    unit: str,
    tags: dict = None
):
    """Store a single metric"""
    metric = Metric(
        instance_id=instance_id,
        metric_type=metric_type,
        metric_value=value,
        metric_unit=unit,
        tags=tags,
        collected_at=datetime.utcnow(),
    )
    session.add(metric)


async def _store_active_sessions(session: Session, instance_id, sessions: list):
    """Store active session snapshots"""
    for sess in sessions:
        active_session = ActiveSession(
            instance_id=instance_id,
            session_id=str(sess.get('sid', '')),
            serial_number=str(sess.get('serial#', '')),
            user_id=sess.get('username', 'unknown'),
            program=sess.get('program'),
            module=sess.get('module'),
            status=sess.get('status', 'UNKNOWN'),
            logon_time=sess.get('logon_time'),
            last_call_et=sess.get('last_call_et'),
            memory_mb=sess.get('memory_mb'),
            cpu_time_sec=sess.get('cpu_time_sec'),
            sql_id=sess.get('sql_id'),
            collected_at=datetime.utcnow(),
        )
        session.add(active_session)


async def _store_locks(session: Session, instance_id, locks: list):
    """Store lock information"""
    for lock in locks:
        lock_record = Lock(
            instance_id=instance_id,
            blocker_session_id=str(lock.get('blocker_sid', '')),
            blocker_serial=str(lock.get('blocker_serial', '')),
            blocked_session_id=str(lock.get('blocked_sid', '')),
            blocked_serial=str(lock.get('blocked_serial', '')),
            lock_type=lock.get('lock_type'),
            object_owner=lock.get('owner'),
            object_name=lock.get('object_name'),
            detected_at=datetime.utcnow(),
        )
        session.add(lock_record)


async def _store_slow_queries(session: Session, instance_id, queries: list):
    """Store slow query information"""
    for query in queries:
        slow_query = SlowQuery(
            instance_id=instance_id,
            sql_id=query.get('sql_id'),
            sql_hash=str(query.get('sql_hash_value', '')),
            sql_text=query.get('sql_text_snippet', '')[:1000],
            executions=query.get('executions'),
            avg_duration_ms=query.get('avg_duration_sec', 0) * 1000,
            total_duration_sec=query.get('total_duration_sec'),
            cpu_time_sec=query.get('cpu_time_sec'),
            disk_reads=query.get('disk_reads'),
            rows_processed=query.get('rows_processed'),
            last_execution=query.get('last_load_time'),
            collected_at=datetime.utcnow(),
        )
        session.add(slow_query)
