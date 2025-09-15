from typing import Annotated, Any, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import SessionLocal

# Dependency to get DB session
def get_db() -> Generator[Session, Any, None]:
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
