import asyncio
from aiogram import Dispatcher

from config import db, Bot_Tokken
from handlers.admin_handler import admin_router
from handlers.user_handler import user_router


dp = Dispatcher()

dp.include_router(admin_router)
dp.include_router(user_router)

async def main():

    await db.connect()
    await db.create_tables()
    

    await dp.start_polling(Bot_Tokken)

    await db.close()

if __name__ == '__main__':
    asyncio.run(main())