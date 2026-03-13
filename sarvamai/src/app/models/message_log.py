from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.sql import func

from app.db.base import Base


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user_number = Column(Text, nullable=True)
    inbound_text = Column(Text, nullable=True)
    query_text = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    answer_text = Column(Text, nullable=True)

    media_count = Column(Integer, nullable=False, default=0)
    media_types = Column(Text, nullable=True)

    status = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    raw_payload = Column(Text, nullable=True)
