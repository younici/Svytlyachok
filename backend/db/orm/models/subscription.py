from sqlalchemy import Column, Integer, Text
from db.orm.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    endpoint = Column(Text, unique=True, nullable=False)
    p256dh = Column(Text, nullable=False)
    auth = Column(Text, nullable=False)
    queue_id = Column(Integer, nullable=False, default=1)
