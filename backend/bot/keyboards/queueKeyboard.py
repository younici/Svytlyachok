from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import untils.variebles as variables
import untils.tools as tools

_rows: list[list[InlineKeyboardButton]] = []

for _queue, _label in variables.QUEUE_LABELS.items():
    _idx = tools.queue_to_index(_queue)
    _rows.append([
        InlineKeyboardButton(
            text=_label,
            callback_data=f"qi:{_idx}"
        )
    ])

queue_select_kb = InlineKeyboardMarkup(inline_keyboard=_rows)
