"""Oracle database client with connection pooling"""

import logging
from typing import Any, Dict, List, Optional

import oracledb

logger = logging.getLogger(__name__)


class OracleConnectionPool:
    """Manages Oracle database connection pooling"""

    def __init__(
        self,
        username: str,
        password: str,
        host: str,
        port: int,
        service_name: str,
        min_connections: int = 2,
        max_connections: int = 10,
        timeout: int = 30,
        instance_name: str = "unknown"
    ):
        """Initialize Oracle connection pool"""
        self.username = username
        self.host = host
        self.port = port
        self.service_name = service_name
        self.instance_name = instance_name
        self.pool = None
        self.is_connected = False

        # Build DSN
        self.dsn = oracledb.makedsn(host, port, service_name=service_name)

        try:
            self.pool = oracledb.create_pool(
                user=username,
                password=password,
                dsn=self.dsn,
                min=min_connections,
                max=max_connections,
                timeout=timeout,
                threaded=False,
                wait_timeout=timeout,
            )
            self.is_connected = True
            logger.info(f"Oracle connection pool created for {instance_name}")
        except oracledb.DatabaseError as e:
            logger.error(f"Failed to create Oracle connection pool for {instance_name}: {e}")
            self.is_connected = False

    def get_connection(self):
        """Get a connection from the pool"""
        if not self.is_connected or not self.pool:
            raise RuntimeError(f"Connection pool not available for {self.instance_name}")
        return self.pool.acquire()

    def close(self):
        """Close all pooled connections"""
        if self.pool:
            self.pool.close()
            self.is_connected = False
            logger.info(f"Oracle connection pool closed for {self.instance_name}")

    def test_connection(self) -> bool:
        """Test if database is reachable"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Connection test failed for {self.instance_name}: {e}")
            return False


class OracleMetricsCollector:
    """Collects metrics from Oracle database"""

    def __init__(self, pool: OracleConnectionPool):
        """Initialize collector with a connection pool"""
        self.pool = pool
        self.instance_name = pool.instance_name

    async def collect_active_sessions(self) -> List[Dict[str, Any]]:
        """Collect active session information"""
        query = """
        SELECT
            s.sid,
            s.serial#,
            s.username,
            s.program,
            s.module,
            s.status,
            s.logon_time,
            s.last_call_et,
            SUM(st.value) FILTER (WHERE st.statistic# IN (24, 25)) OVER (PARTITION BY s.sid) as memory_mb,
            SUM(st.value) FILTER (WHERE st.statistic# = 12) OVER (PARTITION BY s.sid) as cpu_time_sec,
            s.sql_id
        FROM v$session s
        LEFT JOIN v$sesstat st ON s.sid = st.sid
        WHERE s.type != 'BACKGROUND'
            AND s.status = 'ACTIVE'
        ORDER BY s.logon_time DESC
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            sessions = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return sessions
        except Exception as e:
            logger.error(f"Error collecting active sessions from {self.instance_name}: {e}")
            return []

    async def collect_locks(self) -> List[Dict[str, Any]]:
        """Collect lock and blocking information"""
        query = """
        SELECT
            bl.sid AS blocker_sid,
            bl.serial# AS blocker_serial,
            w.sid AS blocked_sid,
            w.serial# AS blocked_serial,
            l.type AS lock_type,
            o.owner,
            o.object_name,
            SYSDATE - (SELECT logon_time FROM v$session WHERE sid = w.sid) AS lock_duration_days
        FROM v$lock l
        JOIN v$session bl ON l.sid = bl.sid
        JOIN v$lock l2 ON l.id1 = l2.id1 AND l.id2 = l2.id2
        JOIN v$session w ON l2.sid = w.sid
        LEFT JOIN dba_objects o ON l.id1 = o.object_id
        WHERE l.block > 0
        ORDER BY bl.sid
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            locks = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return locks
        except Exception as e:
            logger.error(f"Error collecting locks from {self.instance_name}: {e}")
            return []

    async def collect_slow_queries(self, threshold_ms: int = 5000) -> List[Dict[str, Any]]:
        """Collect slow queries from v$sql"""
        query = f"""
        SELECT
            sql_id,
            sql_hash_value,
            SUBSTR(sql_text, 1, 200) AS sql_text_snippet,
            executions,
            ROUND(elapsed_time / 1000000 / GREATEST(executions, 1), 2) AS avg_duration_sec,
            ROUND(elapsed_time / 1000000, 2) AS total_duration_sec,
            ROUND(cpu_time / 1000000, 2) AS cpu_time_sec,
            disk_reads,
            buffer_gets,
            rows_processed,
            last_load_time
        FROM v$sql
        WHERE elapsed_time / 1000000 / GREATEST(executions, 1) > {threshold_ms / 1000}
        ORDER BY elapsed_time DESC
        FETCH FIRST 20 ROWS ONLY
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            queries = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return queries
        except Exception as e:
            logger.error(f"Error collecting slow queries from {self.instance_name}: {e}")
            return []

    async def collect_cpu_usage(self) -> Optional[float]:
        """Collect CPU usage percentage"""
        query = """
        SELECT ROUND(value, 2) AS cpu_usage_percent
        FROM gv$sysmetric
        WHERE metric_name = 'CPU Usage Per Sec'
        AND inst_id = (SELECT instance_number FROM v$instance)
        ORDER BY begin_time DESC
        FETCH FIRST 1 ROW ONLY
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error collecting CPU usage from {self.instance_name}: {e}")
            return None

    async def collect_memory_usage(self) -> Dict[str, float]:
        """Collect memory utilization"""
        query = """
        SELECT
            ROUND(SUM(CASE WHEN pool = 'shared pool' THEN bytes ELSE 0 END) / 1024 / 1024, 2) AS shared_pool_mb,
            ROUND(SUM(CASE WHEN pool = 'buffer cache' THEN bytes ELSE 0 END) / 1024 / 1024, 2) AS buffer_cache_mb,
            ROUND(SUM(CASE WHEN pool = 'log buffer' THEN bytes ELSE 0 END) / 1024 / 1024, 2) AS log_buffer_mb,
            ROUND(SUM(CASE WHEN pool IS NULL THEN bytes ELSE 0 END) / 1024 / 1024, 2) AS other_mb
        FROM v$sga_dynamic_free_memory
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return {
                    'shared_pool_mb': result[0] or 0,
                    'buffer_cache_mb': result[1] or 0,
                    'log_buffer_mb': result[2] or 0,
                    'other_mb': result[3] or 0,
                }
            return {}
        except Exception as e:
            logger.error(f"Error collecting memory usage from {self.instance_name}: {e}")
            return {}

    async def collect_tablespace_usage(self) -> List[Dict[str, Any]]:
        """Collect tablespace usage and capacity"""
        query = """
        SELECT
            ts.tablespace_name,
            ROUND(SUM(df.bytes) / 1024 / 1024, 2) AS total_size_mb,
            ROUND(SUM(fs.bytes) / 1024 / 1024, 2) AS free_space_mb,
            ROUND(100 * (1 - SUM(fs.bytes) / SUM(df.bytes)), 2) AS used_percent
        FROM dba_tablespaces ts
        LEFT JOIN dba_data_files df ON ts.tablespace_name = df.tablespace_name
        LEFT JOIN dba_free_space fs ON ts.tablespace_name = fs.tablespace_name
        GROUP BY ts.tablespace_name
        ORDER BY used_percent DESC
        """
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            tablespaces = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tablespaces
        except Exception as e:
            logger.error(f"Error collecting tablespace usage from {self.instance_name}: {e}")
            return []

    async def get_database_version(self) -> Optional[str]:
        """Get Oracle database version"""
        query = "SELECT banner FROM v$version WHERE ROWNUM = 1"
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting database version from {self.instance_name}: {e}")
            return None
