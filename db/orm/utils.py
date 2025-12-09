from db.orm.base import Base
from db.orm.session import engine, AsyncSessionLocal, db_available
from sqlalchemy import select, text, inspect

from db.orm.models.subscription import Subscription
from db.orm.models.user import User

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

    if "user_id" not in columns:
        sync_conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS user_id INTEGER"))

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
            stmt = (
                select(Subscription, User)
                .join(User, Subscription.user_id == User.id, isouter=True)
                .where(Subscription.endpoint == endpoint)
            )
            row = await session.execute(stmt)
            result = row.first()

            if result:
                existing, user = result
                existing.p256dh = p256dh
                existing.auth = auth

                if user:
                    user.queue_id = queue
                else:
                    new_user = User(queue_id=queue)
                    session.add(new_user)
                    await session.flush()
                    existing.user_id = new_user.id

                await session.commit()
                return existing.user_id

            user = User(queue_id=queue)
            session.add(user)
            await session.flush()

            new_sub = Subscription(
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_id=user.id,
            )
            session.add(new_sub)
            await session.commit()

            log.info(f"Subscription saved: {endpoint[:50]}...")
            return new_sub.user_id

        except Exception:
            await session.rollback()
            raise

async def get_all_sub():
    if AsyncSessionLocal is None:
        log.warning("get_all_sub(): DB not available, returning empty list.")
        return []

    async with AsyncSessionLocal() as conn:
        res = await conn.execute(
            select(
                Subscription.endpoint,
                Subscription.p256dh,
                Subscription.auth,
                User.queue_id,
            ).join(User)
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