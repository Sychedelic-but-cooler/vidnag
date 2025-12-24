"""
Vidnag Database Manager
Handles database connections, sessions, and transactions with MVCC optimization
"""

from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


class DatabaseManager:
    """
    Database connection manager with connection pooling and MVCC optimization

    PostgreSQL uses MVCC (Multi-Version Concurrency Control) by default,
    which allows readers and writers to not block each other. This manager
    optimizes for that behavior.
    """

    def __init__(self, settings_manager):
        self.settings = settings_manager
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._setup_engine()

    def _get_database_url(self) -> str:
        """Construct database URL from settings"""
        from backend.core.settings import SettingsLevel

        host = self.settings.get(SettingsLevel.APP, "database.host")
        port = self.settings.get(SettingsLevel.APP, "database.port")
        name = self.settings.get(SettingsLevel.APP, "database.name")
        user = self.settings.get(SettingsLevel.APP, "database.user")
        password = self.settings.get(SettingsLevel.APP, "database.password")

        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    def _setup_engine(self) -> None:
        """Set up SQLAlchemy engine with connection pooling"""
        from backend.core.settings import SettingsLevel

        database_url = self._get_database_url()

        # Connection pool settings
        pool_size = self.settings.get(SettingsLevel.ADMIN, "server.workers", 4) * 2
        max_overflow = pool_size * 2

        # Create engine with optimized settings
        self.engine = create_engine(
            database_url,
            # Connection pooling - prevents connection exhaustion
            poolclass=QueuePool,
            pool_size=pool_size,  # Number of connections to maintain
            max_overflow=max_overflow,  # Extra connections under load
            pool_pre_ping=True,  # Test connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour

            # Performance settings
            echo=False,  # Set to True for SQL debugging
            future=True,  # Use SQLAlchemy 2.0 style

            # Connection parameters for PostgreSQL
            connect_args={
                "connect_timeout": 10,
                "options": "-c timezone=utc",
                # Statement timeout prevents long-running queries from holding locks
                "options": "-c statement_timeout=30000",  # 30 seconds
            }
        )

        # Set up event listeners
        self._setup_event_listeners()

        # Create session factory
        # READ COMMITTED is PostgreSQL's default isolation level and works
        # perfectly with MVCC - readers never block writers
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False  # Don't expire objects after commit
        )

    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners for optimization"""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Configure connection when established"""
            # PostgreSQL-specific optimizations
            cursor = dbapi_conn.cursor()

            # Set timezone to UTC
            cursor.execute("SET timezone='UTC'")

            # Use READ COMMITTED isolation level (default, but explicit)
            # This level ensures readers don't block writers
            cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED")

            # Set statement timeout (already in connect_args, but double-check)
            cursor.execute("SET statement_timeout = '30s'")

            cursor.close()

        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Called when connection is retrieved from pool"""
            # Log pool stats for monitoring
            pool_stats = self.engine.pool.status()
            if pool_stats:
                from backend.core.logging import get_logger
                try:
                    logger = get_logger()
                    logger.app.debug(f"Connection pool: {pool_stats}")
                except RuntimeError:
                    pass  # Logger not initialized yet

    def get_session(self) -> Session:
        """
        Get a database session

        Use this for manual session management:
        ```python
        session = db.get_session()
        try:
            # Do work
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
        ```
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self, read_only: bool = False) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations

        Args:
            read_only: If True, session is marked as read-only (optimization)

        Usage:
        ```python
        with db.session_scope() as session:
            user = session.query(User).filter_by(id=1).first()
            user.username = "new_name"
            # Automatically commits on success, rollbacks on exception
        ```

        For read-only operations (doesn't block writes):
        ```python
        with db.session_scope(read_only=True) as session:
            users = session.query(User).all()
            # Read-only, no commit needed
        ```
        """
        session = self.SessionLocal()

        # Set transaction as read-only if specified
        if read_only:
            session.execute("SET TRANSACTION READ ONLY")

        try:
            yield session
            if not read_only:
                session.commit()
        except Exception:
            if not read_only:
                session.rollback()
            raise
        finally:
            session.close()

    def get_dependency(self) -> Generator[Session, None, None]:
        """
        FastAPI dependency for database sessions

        Usage in FastAPI routes:
        ```python
        @app.get("/users/{user_id}")
        def get_user(user_id: int, db: Session = Depends(get_db)):
            return db.query(User).filter(User.id == user_id).first()
        ```
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def create_all_tables(self) -> None:
        """
        Create all tables in the database
        WARNING: Use migrations instead in production
        """
        from backend.models import Base
        Base.metadata.create_all(bind=self.engine)

    def drop_all_tables(self) -> None:
        """
        Drop all tables in the database
        WARNING: This deletes all data!
        """
        from backend.models import Base
        Base.metadata.drop_all(bind=self.engine)

    def get_pool_status(self) -> dict:
        """Get connection pool statistics"""
        return {
            "size": self.engine.pool.size(),
            "checked_in": self.engine.pool.checkedin(),
            "checked_out": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
            "status": self.engine.pool.status()
        }

    def dispose(self) -> None:
        """Dispose of the connection pool"""
        if self.engine:
            self.engine.dispose()


# MVCC Best Practices Documentation
"""
PostgreSQL MVCC (Multi-Version Concurrency Control) Best Practices
==================================================================

1. READERS NEVER BLOCK WRITERS
   - PostgreSQL maintains multiple versions of rows
   - Readers see a consistent snapshot of data
   - Writers can modify data while readers are reading
   - This is automatic with READ COMMITTED isolation

2. KEEP TRANSACTIONS SHORT
   - Long transactions hold old row versions
   - This causes table bloat
   - Aim for <1 second transaction duration

3. USE PROPER INDEXES
   - Well-indexed queries are faster
   - Faster queries = shorter locks
   - Our models already include key indexes

4. AVOID EXPLICIT LOCKS
   - Don't use SELECT FOR UPDATE unless necessary
   - Don't use table-level locks
   - Let PostgreSQL's MVCC handle concurrency

5. USE CONNECTION POOLING
   - Reduces connection overhead
   - Maintains optimal number of connections
   - Our DatabaseManager implements this

6. MONITOR POOL STATUS
   - Watch for connection exhaustion
   - Adjust pool_size if needed
   - Use get_pool_status() for monitoring

7. BATCH READ OPERATIONS
   - Use read_only=True for read operations
   - This allows PostgreSQL to optimize
   - Example: with db.session_scope(read_only=True) as session:

8. VACUUM REGULARLY
   - PostgreSQL autovacuum handles this
   - Monitor table bloat
   - Tune autovacuum settings if needed

Example Usage
=============

# Short write transaction (doesn't block readers)
with db.session_scope() as session:
    user = User(username="alice", email="alice@example.com")
    session.add(user)
    # Auto-commits here

# Read-only query (doesn't block writers)
with db.session_scope(read_only=True) as session:
    users = session.query(User).filter(User.is_active == True).all()
    # No commit needed

# FastAPI endpoint (automatic session management)
@app.get("/users")
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
"""


# Global database instance
db: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get the global database instance"""
    if db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return db


def init_db(settings_manager) -> DatabaseManager:
    """Initialize the global database instance"""
    global db
    db = DatabaseManager(settings_manager)
    return db
