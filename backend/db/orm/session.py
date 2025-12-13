from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import os

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

_has_db_config = all([DB_USER, DB_PASS, DB_HOST, DB_NAME])

if _has_db_config:
    db_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_async_engine(db_url)
    AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
else:
    engine = None
    AsyncSessionLocal = None
    print("[warn] DB config is incomplete; DB features are disabled.")

def db_available():
    return engine is not None and AsyncSessionLocal is not None
