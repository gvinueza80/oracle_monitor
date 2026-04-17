"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("CREATE TYPE alert_rule_severity AS ENUM ('info', 'warning', 'critical')")

    # instances table
    op.create_table(
        'instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='1521'),
        sa.Column('service_name', sa.String(255), nullable=False),
        sa.Column('username', sa.String(128), nullable=False),
        sa.Column('password_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('ssl_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('connection_timeout', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('pool_min', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('pool_max', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('last_connection_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('connection_status', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(128), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mfa_secret', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # roles table
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # user_roles table (junction)
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )

    # metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('metric_type', sa.String(50), nullable=False, index=True),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('metric_unit', sa.String(20), nullable=True),
        sa.Column('tags', postgresql.JSON(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_metrics_instance_type_collected', 'metrics',
                    ['instance_id', 'metric_type', 'collected_at'])
    op.create_index('idx_metrics_collected_desc', 'metrics',
                    ['collected_at', 'instance_id'])

    # active_sessions table
    op.create_table(
        'active_sessions',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('session_id', sa.String(50), nullable=False),
        sa.Column('serial_number', sa.String(50), nullable=False),
        sa.Column('user_id', sa.String(30), nullable=False),
        sa.Column('program', sa.String(100), nullable=True),
        sa.Column('module', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('logon_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_call_et', sa.Float(), nullable=True),
        sa.Column('memory_mb', sa.Float(), nullable=True),
        sa.Column('cpu_time_sec', sa.Float(), nullable=True),
        sa.Column('disk_reads', sa.BigInteger(), nullable=True),
        sa.Column('disk_writes', sa.BigInteger(), nullable=True),
        sa.Column('rows_processed', sa.BigInteger(), nullable=True),
        sa.Column('sql_id', sa.String(13), nullable=True),
        sa.Column('current_sql', sa.Text(), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'session_id', 'serial_number', 'collected_at',
                           name='uc_session_snapshot'),
    )
    op.create_index('idx_sessions_instance_user', 'active_sessions',
                    ['instance_id', 'user_id'])
    op.create_index('idx_sessions_instance_status', 'active_sessions',
                    ['instance_id', 'status'])

    # locks table
    op.create_table(
        'locks',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('blocker_session_id', sa.String(50), nullable=False),
        sa.Column('blocker_serial', sa.String(50), nullable=False),
        sa.Column('blocked_session_id', sa.String(50), nullable=False),
        sa.Column('blocked_serial', sa.String(50), nullable=False),
        sa.Column('lock_type', sa.String(30), nullable=True),
        sa.Column('object_owner', sa.String(30), nullable=True),
        sa.Column('object_name', sa.String(100), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_sec', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_locks_instance_detected', 'locks',
                    ['instance_id', 'detected_at'])
    op.create_index('idx_locks_unresolved', 'locks',
                    ['instance_id', 'resolved_at'])

    # slow_queries table
    op.create_table(
        'slow_queries',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('sql_id', sa.String(13), nullable=False, index=True),
        sa.Column('sql_hash', sa.String(16), nullable=True, index=True),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('executions', sa.BigInteger(), nullable=True),
        sa.Column('avg_duration_ms', sa.Float(), nullable=True),
        sa.Column('total_duration_sec', sa.Float(), nullable=True),
        sa.Column('min_duration_ms', sa.Float(), nullable=True),
        sa.Column('max_duration_ms', sa.Float(), nullable=True),
        sa.Column('cpu_time_sec', sa.Float(), nullable=True),
        sa.Column('disk_reads', sa.BigInteger(), nullable=True),
        sa.Column('buffer_gets', sa.BigInteger(), nullable=True),
        sa.Column('rows_processed', sa.BigInteger(), nullable=True),
        sa.Column('last_execution', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_slow_queries_instance_duration', 'slow_queries',
                    ['instance_id', 'avg_duration_ms'])
    op.create_index('idx_slow_queries_instance_collected', 'slow_queries',
                    ['instance_id', 'collected_at'])

    # alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('threshold', sa.DECIMAL(10, 2), nullable=False),
        sa.Column('condition', sa.String(20), nullable=False),
        sa.Column('check_duration', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('severity', sa.Enum('info', 'warning', 'critical', name='alert_rule_severity'),
                 nullable=False, server_default='warning'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true', index=True),
        sa.Column('notifications', postgresql.JSON(), nullable=True),
        sa.Column('suppress_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('auto_remediation_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('auto_remediation_action', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_alert_rules_instance_enabled', 'alert_rules',
                    ['instance_id', 'enabled'])

    # alert_history table
    op.create_table(
        'alert_history',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suppressed_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('metric_unit', sa.String(20), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='triggered'),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_alert_history_rule_triggered', 'alert_history',
                    ['rule_id', 'triggered_at'])
    op.create_index('idx_alert_history_status_triggered', 'alert_history',
                    ['status', 'triggered_at'])

    # audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False),
        sa.Column('details', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), index=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_logs_user_created', 'audit_logs',
                    ['user_id', 'created_at'])
    op.create_index('idx_audit_logs_action_created', 'audit_logs',
                    ['action', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_audit_logs_action_created', table_name='audit_logs')
    op.drop_index('idx_audit_logs_user_created', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index('idx_alert_history_status_triggered', table_name='alert_history')
    op.drop_index('idx_alert_history_rule_triggered', table_name='alert_history')
    op.drop_table('alert_history')
    op.drop_index('idx_alert_rules_instance_enabled', table_name='alert_rules')
    op.drop_table('alert_rules')
    op.drop_index('idx_slow_queries_instance_collected', table_name='slow_queries')
    op.drop_index('idx_slow_queries_instance_duration', table_name='slow_queries')
    op.drop_table('slow_queries')
    op.drop_index('idx_locks_unresolved', table_name='locks')
    op.drop_index('idx_locks_instance_detected', table_name='locks')
    op.drop_table('locks')
    op.drop_index('idx_sessions_instance_status', table_name='active_sessions')
    op.drop_index('idx_sessions_instance_user', table_name='active_sessions')
    op.drop_table('active_sessions')
    op.drop_index('idx_metrics_collected_desc', table_name='metrics')
    op.drop_index('idx_metrics_instance_type_collected', table_name='metrics')
    op.drop_table('metrics')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('instances')
    op.execute("DROP TYPE alert_rule_severity")
