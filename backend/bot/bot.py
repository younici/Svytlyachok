from aiogram import Bot, Dispatcher
import os

import bot.handlers.queue as queue
import bot.handlers.start as start

BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()
bot = Bot(BOT_TOKEN)

async def start_bot():
    dp.include_routers(queue.router, start.router)
    await dp.start_polling(bot)

def get_bot() -> Bot:
    return bot 