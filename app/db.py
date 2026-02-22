import os
import asyncpg
from contextlib import asynccontextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

@asynccontextmanager
async def get_conn():
    """
    Lightweight connection helper.
    Opens a connection for the request and closes it after.
    Good enough for v1; later we can switch to a pool.
    """
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()
