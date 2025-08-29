import asyncio
from aiogram import Dispatcher

from config import db, Bot_Tokken
from handlers.admin_handler import admin_router
from handlers.user_handler import user_router


dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(user_router)

async def main():
    print('Starting barbershop queue bot...')
    await db.connect()
    await db.create_tables()
    
    try:
        await dp.start_polling(Bot_Tokken)
    finally:
        await db.close()

if __name__ == '__main__':
    asyncio.run(main())