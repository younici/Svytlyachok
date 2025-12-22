from sqlalchemy import Column, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from db.orm.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    queue_id = Column(Integer, nullable=False, default=0)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    user = relationship("User", back_populates="subscription")
