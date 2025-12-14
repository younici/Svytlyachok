from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship
from db.orm.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, autoincrement=True, primary_key=True)
    queue_id = Column(Integer, nullable=False)

    subscription = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")