from sqlalchemy import Column, Integer, String
from src.app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    phone_hash = Column(String, unique=True, index=True)
