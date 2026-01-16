import logging
import os

from datetime import datetime, timedelta

from sqlalchemy import inspect, select, text

from db.orm.base import Base
from db.orm.models import Subscription, SupportAdmin, SupportBan, SupportTicket, SupportTicketMessage, TgSub
from db.orm.session import AsyncSessionLocal, db_available, engine

log = logging.getLogger(__name__)

PRIMARY_SUPPORT_ADMIN = int(os.getenv("HELP_BASE_ADMIN_ID", "0") or 0)


async def init_db():
    if not db_available():
        log.info("init_db(): DB not available, skipping migrations.")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_subscription_columns)
        await conn.run_sync(_ensure_support_tables)


def _ensure_subscription_columns(sync_conn):
    inspector = inspect(sync_conn)
    columns = {col["name"] for col in inspector.get_columns("subscriptions")}

    if "queue_id" not in columns:
        sync_conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS queue_id INTEGER DEFAULT 0"))


def _ensure_support_tables(sync_conn):
    inspector = inspect(sync_conn)
    tables = set(inspector.get_table_names())

    if "support_admins" not in tables:
        SupportAdmin.__table__.create(sync_conn, checkfirst=True)
    if "support_tickets" not in tables:
        SupportTicket.__table__.create(sync_conn, checkfirst=True)
    if "support_bans" not in tables:
        SupportBan.__table__.create(sync_conn, checkfirst=True)
    if "support_ticket_messages" not in tables:
        SupportTicketMessage.__table__.create(sync_conn, checkfirst=True)


async def ensure_support_admin(tg_id: int, is_primary: bool = False) -> bool:
    if AsyncSessionLocal is None or not tg_id:
        return False

    async with AsyncSessionLocal() as session:
        stmt = select(SupportAdmin).where(SupportAdmin.tg_id == tg_id)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if is_primary and not existing.is_primary:
                existing.is_primary = True
                await session.commit()
            return True

        session.add(SupportAdmin(tg_id=tg_id, is_primary=is_primary))
        await session.commit()
        return True


async def ensure_primary_support_admin():
    if PRIMARY_SUPPORT_ADMIN:
        try:
            return await ensure_support_admin(PRIMARY_SUPPORT_ADMIN, is_primary=True)
        except Exception:
            try:
                await init_db()
                return await ensure_support_admin(PRIMARY_SUPPORT_ADMIN, is_primary=True)
            except Exception:
                log.exception("Failed to ensure primary support admin")
                return False
    return False


async def get_active_ban(user_id: int) -> SupportBan | None:
    if AsyncSessionLocal is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SupportBan).where(SupportBan.user_id == user_id))
        ban = res.scalar_one_or_none()
        if not ban:
            return None
        if ban.until and ban.until < datetime.now(tz=ban.until.tzinfo):
            # ban expired -> cleanup
            await session.delete(ban)
            await session.commit()
            return None
        return ban


async def set_support_ban(user_id: int, until: datetime | None, reason: str | None) -> bool:
    if AsyncSessionLocal is None:
        return False
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(SupportBan).where(SupportBan.user_id == user_id))
            ban = res.scalar_one_or_none()
            if ban:
                ban.until = until
                ban.reason = reason
            else:
                session.add(SupportBan(user_id=user_id, until=until, reason=reason))
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            log.exception("Failed to set support ban")
            return False


async def remove_support_ban(user_id: int) -> bool:
    if AsyncSessionLocal is None:
        return False
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(SupportBan).where(SupportBan.user_id == user_id))
            ban = res.scalar_one_or_none()
            if not ban:
                return False
            await session.delete(ban)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            log.exception("Failed to remove support ban")
            return False


async def list_support_admin_ids() -> list[int]:
    if AsyncSessionLocal is None:
        return [PRIMARY_SUPPORT_ADMIN] if PRIMARY_SUPPORT_ADMIN else []

    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SupportAdmin.tg_id))
        ids = [row[0] for row in res.all()]

        if PRIMARY_SUPPORT_ADMIN and PRIMARY_SUPPORT_ADMIN not in ids:
            ids.append(PRIMARY_SUPPORT_ADMIN)
        return ids


async def is_support_admin(tg_id: int) -> bool:
    if not tg_id:
        return False
    admins = await list_support_admin_ids()
    return tg_id in admins


async def remove_support_admin(tg_id: int) -> bool:
    if AsyncSessionLocal is None or not tg_id:
        return False
    if tg_id == PRIMARY_SUPPORT_ADMIN:
        # базового адміна не видаляємо
        return False

    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(SupportAdmin).where(SupportAdmin.tg_id == tg_id))
            admin = res.scalar_one_or_none()
            if not admin:
                return False
            await session.delete(admin)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            log.exception("Failed to remove support admin %s", tg_id)
            return False


async def is_help_bot_admin(tg_id: int) -> bool:
    """Alias for підтримки-бoта, щоб не плодити зависимости."""
    return await is_support_admin(tg_id)


async def create_support_ticket(user_id: int, username: str | None, message: str) -> SupportTicket | None:
    if AsyncSessionLocal is None:
        log.warning("DB not available, skipping ticket creation")
        return None

    async with AsyncSessionLocal() as session:
        try:
            ticket = SupportTicket(user_id=user_id, username=username, message=message, status="open")
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            return ticket
        except Exception:
            await session.rollback()
            log.exception("Failed to create support ticket")
            return None


async def get_ticket(ticket_id: int) -> SupportTicket | None:
    if AsyncSessionLocal is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
        return res.scalar_one_or_none()


async def get_last_ticket_time(user_id: int) -> datetime | None:
    if AsyncSessionLocal is None:
        return None
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(SupportTicket.created_at)
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(1)
        )
        row = res.first()
        return row[0] if row else None


async def can_create_ticket(user_id: int, cooldown_minutes: int = 30) -> tuple[bool, int]:
    """
    Returns (allowed, wait_seconds).
    """
    last_ts = await get_last_ticket_time(user_id)
    if not last_ts:
        return True, 0
    now = datetime.now(tz=last_ts.tzinfo)
    delta = (now - last_ts).total_seconds()
    cooldown = cooldown_minutes * 60
    if delta >= cooldown:
        return True, 0
    return False, int(cooldown - delta)


async def mark_ticket_answered(ticket_id: int, admin_id: int, answer_text: str) -> bool:
    if AsyncSessionLocal is None:
        return False

    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
            ticket = res.scalar_one_or_none()
            if not ticket:
                return False

            ticket.status = "answered"
            ticket.answer_text = answer_text
            ticket.answered_by = admin_id
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            log.exception("Failed to mark ticket answered")
            return False


async def delete_ticket(ticket_id: int) -> bool:
    if AsyncSessionLocal is None:
        return False
    async with AsyncSessionLocal() as session:
        try:
            res = await session.execute(select(SupportTicket).where(SupportTicket.id == ticket_id))
            ticket = res.scalar_one_or_none()
            if not ticket:
                return False
            await session.delete(ticket)
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            log.exception("Failed to delete support ticket")
            return False


async def save_ticket_message(ticket_id: int, admin_id: int, chat_id: int, message_id: int) -> None:
    if AsyncSessionLocal is None:
        return
    async with AsyncSessionLocal() as session:
        try:
            session.add(
                SupportTicketMessage(
                    ticket_id=ticket_id,
                    admin_id=admin_id,
                    chat_id=chat_id,
                    message_id=message_id,
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("Failed to save ticket message mapping")


async def get_ticket_messages(ticket_id: int) -> list[SupportTicketMessage]:
    if AsyncSessionLocal is None:
        return []
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(SupportTicketMessage).where(SupportTicketMessage.ticket_id == ticket_id))
        return list(res.scalars().all())


async def delete_ticket_messages(ticket_id: int) -> None:
    if AsyncSessionLocal is None:
        return
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                SupportTicketMessage.__table__.delete().where(SupportTicketMessage.ticket_id == ticket_id)
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("Failed to delete ticket message mappings")


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
