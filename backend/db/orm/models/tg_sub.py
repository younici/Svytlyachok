from db.orm.base import Base
from sqlalchemy import Column, Integer, BigInteger


class TgSub(Base):
    __tablename__ = "tg_sub"

    id = Column(Integer, autoincrement=True)
    tg_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)

    queue_id = Column(Integer, nullable=False, default=1)
