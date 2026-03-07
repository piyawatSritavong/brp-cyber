from sqlalchemy import text

from fastapi import APIRouter

from app.db.models import Base
from app.db.session import engine

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("/phase0/init-db")
def init_db() -> dict[str, str]:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
    Base.metadata.create_all(bind=engine)
    return {"status": "ok", "detail": "timescaledb extension and tables created"}
