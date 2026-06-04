#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from pathlib import Path

path = Path("pyproject.toml")
content = path.read_text()
strict_constraint = 'python = "^3.13"'
vercel_constraint = 'python = ">=3.12,<4.0"'
if strict_constraint not in content:
    raise SystemExit("Expected Python constraint not found in pyproject.toml")
path.write_text(content.replace(strict_constraint, vercel_constraint, 1))
print("Temporarily relaxed Python constraint for Vercel build: >=3.12,<4.0")
PY

python -m pip install \
  "fastapi[standard]>=0.116.1,<0.117.0" \
  "uvicorn>=0.35.0,<0.36.0" \
  "python-jose[cryptography]>=3.5.0,<4.0.0" \
  "passlib[bcrypt]>=1.7.4,<2.0.0" \
  "pydantic>=2.11.9,<3.0.0" \
  "sqlalchemy>=2.0.43,<3.0.0" \
  "asyncpg>=0.30.0,<0.31.0" \
  "marshmallow>=4.0.1,<5.0.0" \
  "bcrypt>=5.0.0,<6.0.0" \
  "httpx>=0.28.1,<0.29.0" \
  "slowapi>=0.1.9,<0.2.0" \
  "stripe>=14.4.1,<15.0.0" \
  "structlog>=24.0,<25.0" \
  "python-dotenv>=1.0.0,<2.0.0" \
  "greenlet>=3.0.0,<4.0.0"
