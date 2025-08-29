from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

user_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='📝 Записаться в очередь'),KeyboardButton(text='👤 Моя очередь')],
        [KeyboardButton(text='📋 Посмотреть услуги')]
    ],
    resize_keyboard=True
)