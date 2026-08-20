from psycopg_pool import ConnectionPool

from app.core.config import settings

# Global connection pool
db_pool = ConnectionPool(conninfo=settings.database_url, open=True)

def get_db_pool() -> ConnectionPool:
    if db_pool.closed:
        db_pool.open()
    return db_pool
