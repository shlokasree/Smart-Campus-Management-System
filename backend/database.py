import os
from pathlib import Path
from contextlib import contextmanager
from dotenv import load_dotenv
import psycopg2
import psycopg2.extensions
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "campus_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

_pool: ThreadedConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 20) -> None:
    """Initializes the thread-safe PostgreSQL connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )


def close_pool() -> None:
    """Closes all connections in the pool on shutdown."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None


class PooledConnectionWrapper:
    """
    Transparent connection wrapper for PostgreSQL connection pool:
    1. .cursor() returns RealDictCursor for dict-like row access (row['id']).
    2. Active cursors are tracked and closed upon connection close.
    3. Transactions are cleanly rolled back if uncommitted or in error before
       returning the connection to the pool, guaranteeing an IDLE state.
    4. Broken or corrupted connections are closed and discarded from the pool.
    """
    def __init__(self, raw_conn, pool: ThreadedConnectionPool):
        self._conn = raw_conn
        self._pool = pool
        self._closed = False
        self._cursors = []

    def cursor(self):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        self._cursors.append(cur)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._closed:
            return

        # 1. Close all open cursors created by this wrapper
        for cur in self._cursors:
            try:
                if not cur.closed:
                    cur.close()
            except Exception:
                pass
        self._cursors.clear()

        # 2. Reset transaction state back to clean IDLE
        try:
            status = self._conn.get_transaction_status()
            if status != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                self._conn.rollback()
        except Exception:
            # Socket corrupted; discard connection from pool permanently
            try:
                self._pool.putconn(self._conn, close=True)
                self._closed = True
                return
            except Exception:
                pass

        # 3. Return clean, idle connection to pool
        try:
            self._pool.putconn(self._conn)
        except Exception:
            pass
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_connection() -> PooledConnectionWrapper:
    """
    Backward-compatible connection factory.
    Returns a wrapped pooled connection that returns cleanly to the pool upon .close().
    """
    if _pool is None or _pool.closed:
        init_pool()
    raw_conn = _pool.getconn()
    return PooledConnectionWrapper(raw_conn, _pool)


@contextmanager
def get_db_cursor():
    """Context manager for direct cursor checkout with automatic commit/rollback."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_database() -> None:
    """Verifies PostgreSQL connection pool and tests database connectivity."""
    init_pool()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT current_database(), current_user;")
        row = cursor.fetchone()
        cursor.close()
        print(f"Connected to PostgreSQL database: {row['current_database']} as {row['current_user']}")
    finally:
        conn.close()