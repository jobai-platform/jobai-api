import asyncio
import importlib
import os.path
import pkgutil
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.infrastructure.config.database import Base

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models' MetaData object for 'autogenerate' support
def import_all_models(package_name: str = "app.infrastructure.persistence.models") -> None:
    try:
        pkg = importlib.import_module(package_name)
    except ModuleNotFoundError as e:
        raise RuntimeError(f"Package '{package_name}' not found") from e

    prefix = pkg.__name__ + "."
    for _, modname, ispkg in pkgutil.walk_packages(pkg.__path__, prefix):
        # Ignore packages, only import modules
        if ispkg:
            continue
        # Skip test, helper, and utility modules
        if modname.endswith((".tests", ".helpers", ".utils")):
            continue
        importlib.import_module(modname)

import_all_models()

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_sync_db_url() -> str:
    # postgresql+asyncpg://postgres:postgres@db:5432/jobai_db
    return settings.DATABASE_URL

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_sync_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def _run_sync(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    engine = create_async_engine(
        get_sync_db_url(),
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
