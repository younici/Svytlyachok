from db.orm.base import Base
from db.orm.session import engine, AsyncSessionLocal, db_available
from sqlalchemy import select, text, inspect

from db.orm.models.subscription import Subscription
from db.orm.models.tg_sub import TgSub

import logging

log = logging.getLogger(__name__)


async def init_db():
    if not db_available():
        log.info("init_db(): DB not available, skipping migrations.")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_subscription_columns)


def _ensure_subscription_columns(sync_conn):
    inspector = inspect(sync_conn)
    columns = {col["name"] for col in inspector.get_columns("subscriptions")}

    if "queue_id" not in columns:
        sync_conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS queue_id INTEGER DEFAULT 0"))


def _extract_subscription_data(data: dict):
    queue = data.get("queue", 0)
    try:
        queue = int(queue)
    except (TypeError, ValueError):
        queue = 0
    queue = max(0, min(queue, 1))

    sub_payload = data.get("subscription") or data
    keys = sub_payload.get("keys") or {}
    endpoint = sub_payload.get("endpoint")
    p256dh = keys.get("p256dh") or sub_payload.get("p256dh")
    auth = keys.get("auth") or sub_payload.get("auth")

    return queue, endpoint, p256dh, auth


async def save_sub(data):
    if AsyncSessionLocal is None:
        log.warning("save_sub(): DB not available, skipping.")
        return False

    queue, endpoint, p256dh, auth = _extract_subscription_data(data)

    if not endpoint or not p256dh or not auth:
        log.warning("save_sub(): invalid data", data)
        return False

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Subscription).where(Subscription.endpoint == endpoint)
            row = await session.execute(stmt)
            existing = row.scalar_one_or_none()

            if existing:
                existing.p256dh = p256dh
                existing.auth = auth
                existing.queue_id = queue

                await session.commit()
                return existing.id

            new_sub = Subscription(
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                queue_id=queue,
            )
            session.add(new_sub)
            await session.commit()

            log.info(f"Subscription saved: {endpoint[:50]}...")
            return new_sub.id

        except Exception:
            await session.rollback()
            raise


async def get_all_http_sub():
    if AsyncSessionLocal is None:
        log.warning("get_all_http_sub(): DB not available, returning empty list.")
        return []

    async with AsyncSessionLocal() as conn:
        res = await conn.execute(
            select(
                Subscription.endpoint,
                Subscription.p256dh,
                Subscription.auth,
                Subscription.queue_id,
            )
        )

        rows = res.all()
        payload = []
        for endpoint, p256dh, auth, queue_id in rows:
            payload.append({
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
                "queue": queue_id,
            })

        return payload


async def delete_sub(endpoint: str):
    if AsyncSessionLocal is None:
        log.info("delete_sub(): DB not available, skipping.")
        return False

    if not endpoint:
        return False

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(Subscription).where(Subscription.endpoint == endpoint)
            res = await session.execute(stmt)
            sub = res.scalar_one_or_none()
            if not sub:
                return False

            await session.delete(sub)
            await session.commit()
            log.info(f"Subscription deleted: {endpoint[:50]}...")
            return True
        except Exception:
            await session.rollback()
            raise


def disable_db():
    """Отключаем доступ к БД, если нет конфига или подключение упало."""
    global AsyncSessionLocal
    try:
        import db.orm.session as session_mod
        session_mod.AsyncSessionLocal = None
        session_mod.engine = None
    except Exception:
        pass
    AsyncSessionLocal = None
    log.warning("Database disabled (config missing or init failed).")


async def add_tg_subscriber(id, queue_iq):
    if AsyncSessionLocal is None:
        log.warning("db is None")
        return
    async with AsyncSessionLocal() as session:
        try:
            ex = select(TgSub).where(TgSub.tg_id == id)
            res = await session.execute(ex)
            if res.scalar_one_or_none() is not None:
                return -1
            user = TgSub(tg_id=id, queue_id=queue_iq)
            session.add(user)
            await session.commit()

            await session.refresh(user)

            log.info(f"added user {user}")
        except Exception as e:
            log.exception("Error while adding tg subscriber")
            await session.rollback()

async def get_tg_subscriber(tg_id: int) -> TgSub | None:
    if AsyncSessionLocal is None:
        log.warning("db is None")
        return None

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(TgSub).where(TgSub.tg_id == tg_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            log.exception(f"Error while getting tg_sub {tg_id}")
            return None

async def get_all_tg_subscribers() -> list[TgSub]:
    if AsyncSessionLocal is None:
        log.warning("db is None")
        return []

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(TgSub))
            return list(result.scalars().all())
        except Exception:
            log.exception("Error while getting all tg_subs")
            return []


async def delete_tg_subscriber(tg_id: int) -> int:
    if AsyncSessionLocal is None:
        log.warning("db is None")
        return 0

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(TgSub).where(TgSub.tg_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                return -1
            
            await session.delete(user)
            await session.commit()

            log.info(f"Deleted tg_sub with tg_id={tg_id}")
            return 1

        except Exception:
            log.exception(f"Error while deleting tg_sub {tg_id}")
            await session.rollback()
            return 0


async def upsert_tg_subscriber(tg_id: int, queue_id: int) -> int:
    if AsyncSessionLocal is None:
        log.warning("db is None")
        return 0
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(TgSub).where(TgSub.tg_id == tg_id)
            )
            user = result.scalar_one_or_none()

            if user is None:
                user = TgSub(tg_id=tg_id, queue_id=queue_id)
                session.add(user)
                action = "created"
                code = 2
            else:
                user.queue_id = queue_id
                action = "updated"
                code = 1

            await session.commit()
            await session.refresh(user)

            log.info(f"{action} tg_sub: tg_id={user.tg_id}, queue_id={user.queue_id}")
            return code

        except Exception:
            log.exception(f"Error while upserting tg_sub tg_id={tg_id}")
            await session.rollback()
            return 0