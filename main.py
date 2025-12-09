from apscheduler.schedulers.asyncio import AsyncIOScheduler

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json, os

from typing import Any

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dotenv import load_dotenv

import untils.redis_db as redis_un
from untils import notifier
from untils import subcription
from untils import cache
from db.orm.session import AsyncSessionLocal
import db.orm.utils as db

load_dotenv()

import logging as log

log.basicConfig(
    level=log.DEBUG,
    format="! [%(levelname)s] %(message)s"
)

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ISDB = True

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
NOTIFY_PASS = os.getenv("NOTIFY_PASS")
BASE_DIR = Path(__file__).resolve().parent
SITE_DIR = BASE_DIR / "site"

OFFLINE = os.getenv("OFFLINE", "false").lower() == "true"

app.mount("/site", StaticFiles(directory=SITE_DIR), name="site")

@app.get("/vapid_public_key")
def vapid_key():
    return {"key": VAPID_PUBLIC_KEY}

@app.post("/subscribe")
async def subscribe(req: Request):
    data = await req.json()

    sub = data.get("subscription")
    if not isinstance(sub, dict):
        return {"ok": False, "msg": "Invalid subscription data"}

    queue = subcription.queue_code_from_input(data.get("queue"))

    endpoint = sub.get("endpoint")
    keys = sub.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return {"ok": False, "msg": "Invalid subscription data"}

    sub_push = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
        "queue": queue,
    }

    existing_queue, existing_idx = subcription.find_push_subscription(endpoint)

    if existing_idx is None:
        subcription.remember_push_subscription(sub_push)
        created = True
    else:
        subcription.forget_push_subscription(endpoint)
        subcription.remember_push_subscription(sub_push)
        created = False

    await subcription.save_subscription_db(queue, sub_push)

    await subcription.save_all_to_redis()

    return {"ok": True, "msg": "Ви пiдписались на сповiщення" if created else "Данi пiдписки оновлено"}

@app.post("/unsubscribe")
async def unsubscribe(req: Request):
    data = await req.json()
    sub = data.get("subscription")

    normalized = subcription.normalize_subscription(sub)
    if not normalized:
        return {"ok": False, "msg": "Invalid subscription data"}

    endpoint = normalized.get("endpoint")
    removed = subcription.forget_push_subscription(endpoint)

    if ISDB:
        try:
            await db.delete_sub(endpoint)
        except Exception as ex:
            log.warning(f"delete_sub failed: {ex}")

    await subcription.save_all_to_redis()

    # Отменяем подписку в базе/кэше, даже если на клиенте уже нет подписи
    return {"ok": True, "msg": "Підписку скасовано" if removed else "Підписка не знайдена"}


@app.post("/notify")
async def notify(req: Request):
    body: dict[str, Any] = await req.json()
    message = body.get("message")
    title = body.get("title")

    if NOTIFY_PASS != body.get("pass"):
        return {"msg": "incorrect password"}

    return await notifier.notify_all(title=title, message=message)

@app.get("/")
def index():
    return FileResponse(SITE_DIR / "index.html")

@app.get("/robots.txt")
def robots():
    return FileResponse(SITE_DIR / "robots.txt")

@app.get("/sitemap.xml")
def sitemap():
    return FileResponse(SITE_DIR / "sitemap.xml")

@app.get("/ads.txt")
def ads():
    return FileResponse(SITE_DIR / "ads.txt")

@app.get("/sw.js")
def service_worker():
    return FileResponse(SITE_DIR / "sw.js")

@app.get("/count")
def get_count():
    all_subs = [json.dumps(sub) for sub in notifier.get_subs() if sub]
    return len(all_subs)

@app.get("/status")
async def get_status(queue: str | None = None):
    queue_code = subcription.queue_code_from_input(queue)
    return {"Status": await notifier.parse_status_for_queue(queue_code)}

@app.on_event("startup")
async def start():
    scheduler = AsyncIOScheduler()
    if not OFFLINE:
        scheduler.add_job(notifier.check_and_notify, "cron", minute="0,30")
    else:
        log.info("app started in offline mode")

    scheduler.add_job(cache.cache_loop, "cron", minute="0,05")
    scheduler.start()

    log.info("scheduler started")

    if not OFFLINE:
        try:
            await db.init_db()
        except Exception as exc:
            log.warning(f"init_db() failed: {exc}")
            db.disable_db()
            global ISDB
            ISDB = False
    else:
        log.info("db disabled, offline mode")
    

    redis_client = await redis_un.init_redis()
    subcription.set_redis_client(redis_client)
    await subcription.load_subscriptions_from_storage()