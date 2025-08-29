from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

admin_keyboard =  ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='➕ Добавить услугу'),KeyboardButton(text='📋 Посмотреть услуги')],
        [KeyboardButton(text='📊 Посмотреть очередь'),KeyboardButton(text='👥 Посмотреть пользователей')],
    ],
    resize_keyboard=True
)