from psycopg_pool import ConnectionPool

from app.core.config import settings

# Global connection pool
db_pool = ConnectionPool(conninfo=settings.database_url, open=False)

def get_db_pool() -> ConnectionPool:
    return db_pool
