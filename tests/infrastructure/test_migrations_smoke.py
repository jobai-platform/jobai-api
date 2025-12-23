import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"


def _alembic_config() -> Config:
    """
    Create an Alembic Config pointing to the project's alembic.ini.

    We keep this helper minimal: it only ensures that alembic.ini is found
    and can be parsed, and that Alembic can load the migration scripts
    (env.py) via the Alembic runtime (NOT via importing migrations.env).
    """
    if not ALEMBIC_INI_PATH.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ALEMBIC_INI_PATH}")

    # Ensure predictable relative resolution.
    os.chdir(str(PROJECT_ROOT))

    return Config(str(ALEMBIC_INI_PATH))


def test_alembic_history_loads_offline() -> None:
    """
    Offline smoke test:
    - Alembic can read config
    - Alembic can load migration env.py
    - env.py can import Base + models and build metadata
    No DB connection required
    """
    cfg = _alembic_config()
    command.history(cfg)


# @pytest.mark.integration
# def test_alembic_upgrade_head_integration() -> None:
#     """
#     Integration test:
#     Requires a reachable Postgres (e.g. docker compose network).
#     Runs alembic upgrade head to validate end-to-end migration.
#     """
#     cfg = _alembic_config()
#     command.upgrade(cfg, "head")
