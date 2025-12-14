from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging

import db.orm.utils as db
import untils.redis_db as redisdb
from untils import subcription, tools, variebles

import bot.keyboards.queueKeyboard as keyboard

redis = None
log = logging.getLogger(__name__)

router = Router()

QUEUE_MESSAGE = """
Сайт з графіками відключення світла: https://likhtarychok.org
"""

@router.message(Command("queue"))
async def bot_queue_cmd(msg: Message):
    await msg.answer(QUEUE_MESSAGE)

@router.message(Command("set_queue"))
async def bot_set_queue(msg: Message):
    await msg.answer("Виберіть чергу", reply_markup=keyboard.queue_select_kb)

@router.message(Command("delete_queue"))
async def bot_delete_queue(msg: Message):
    id = msg.from_user.id
    status = await db.delete_tg_subscriber(id)
    log.info(f"status: {status}")
    match status:
        case -1:
            await msg.answer("У вас немає підписок")
        case 0:
            await msg.answer("На жаль зараз у нашого бота немає змоги видалити вашу підписку, будь-ласка спробуйте пізніше")
        case 1:
            await msg.answer("Ваша підписка успішно видалена")
    await redisdb.delete_tg_subscription(id)
     

@router.callback_query(F.data.startswith("qi"))
async def bot_callback_queue(cb: CallbackQuery):
    try:
        raw = cb.data.split(":", maxsplit=1)[1]
        queue_idx = int(raw)
    except Exception:
        await cb.answer("Невідома черга", show_alert=True)
        return

    queue = tools.index_to_queue(queue_idx)
    await cb.answer()

    tg_id = cb.from_user.id

    await db.upsert_tg_subscriber(tg_id, queue)
    subcription.remember_telegram_subscription({"id": tg_id, "queue": queue})

    global redis
    if not redis:
        redis = redisdb.get_redis_client()

    if redis:
        try:
            await redisdb.save_tg_subscription(tg_id, queue)
        except Exception as exc:
            log.warning("Failed to store tg subscription in Redis: %s", exc)

    await cb.message.delete()
    await cb.message.answer(f"Ви вибрали чергу {variebles.QUEUE_LABELS[queue]}\nМи будемо надсилати вам сповіщення за годину до планового відключення світла")
