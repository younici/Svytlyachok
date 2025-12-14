from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

HELP_MESSAGE = """
/help - показує цей список
/queue - посилання на сайт з графіками відключень світла
/set_queue - увімкнути та вибрати або оновити чергу для сповіщеннь
/delete_queue - вимкнути сповіщення
"""

START_MESSAGE = """
Привіт, цей бот створений для сайту https://likhtarychok.org
через нього ви можете отримувати сповіщення про відключення світла за годину, якщо у вас не працюють сповіщення з сайту

Для перегляду доступних команд напишіть /help
"""

@router.message(Command("start"))
async def bot_start_cmd(msg: Message):
    await msg.answer(START_MESSAGE)

@router.message(Command("help"))
async def bot_help_cmd(msg: Message):
    await msg.answer(HELP_MESSAGE)