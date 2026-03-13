import logging

from app.db.base import Base
from app.db.session import get_engine, get_session_factory
from app.models.message_log import MessageLog

logger = logging.getLogger(__name__)
_table_initialized = False


def _ensure_table():
    global _table_initialized
    if _table_initialized:
        return

    engine = get_engine()
    Base.metadata.create_all(bind=engine, tables=[MessageLog.__table__])
    _table_initialized = True


def write_message_log(
    *,
    user_number: str | None,
    inbound_text: str | None,
    query_text: str | None,
    transcript: str | None,
    answer_text: str | None,
    media_count: int,
    media_types: str | None,
    status: str,
    error_message: str | None = None,
    raw_payload: str | None = None,
) -> None:
    """Persist webhook processing logs to Postgres without breaking message flow."""
    try:
        _ensure_table()
        session_factory = get_session_factory()
        db = session_factory()
        try:
            row = MessageLog(
                user_number=user_number,
                inbound_text=inbound_text,
                query_text=query_text,
                transcript=transcript,
                answer_text=answer_text,
                media_count=media_count,
                media_types=media_types,
                status=status,
                error_message=error_message,
                raw_payload=raw_payload,
            )
            db.add(row)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Failed to write message log to Postgres: %s", exc)
