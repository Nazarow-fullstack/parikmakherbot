from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta

from database.user import User
from database.service import Service
from database.queue_entry import QueueEntry
from config import db
from keyboards.user_keyboard import user_keyboard
from states.service_states import QueueState
user_router = Router()

@user_router.message(Command('start'))
async def start_handler(msg: Message):
    if msg.from_user.last_name:
        fullname = msg.from_user.first_name + ' ' + msg.from_user.last_name
    else:
        fullname = msg.from_user.first_name
    
    user = User(msg.from_user.id, msg.from_user.username, fullname, db)
    if not await user.get_user():
        await user.save()
    
    await msg.answer('Добро пожаловать в систему записи парикмахерской! 💇‍♀️', reply_markup=user_keyboard)


@user_router.message(lambda m: m.text == '📋 Посмотреть услуги')
async def view_services_handler(msg: Message):
    services = await Service.get_services(db)
    if not services:
        await msg.answer('Услуги пока не добавлены.')
        return
    
    for service in services:
        await msg.answer(
            f"🔹 {service['name']}\n"
            f"⏱ Длительность: {service['duration']} мин\n"
            f"💰 Цена: {service['price']} руб."
        )


@user_router.message(lambda m: m.text == '📝 Записаться в очередь')
async def join_queue_handler(msg: Message, state: FSMContext):
    services = await Service.get_services(db)
    if not services:
        await msg.answer('Услуги пока не добавлены.')
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{service['name']} - {service['price']} руб.",
                callback_data=f"select_service={service['id']}"
            )] for service in services
        ]
    )
    
    await state.set_state(QueueState.select_service)
    await msg.answer('Выберите услугу:', reply_markup=keyboard)


@user_router.callback_query(F.data.contains('select_service'))
async def select_service_handler(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split('=')[1])
    service = await Service.get_service_by_id(service_id, db)
    
    if not service:
        await callback.answer('Услуга не найдена!')
        return
    
    await state.update_data(service_id=service_id)
    

    time_slots = []
    base_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    for day in range(7):
        current_day = base_time + timedelta(days=day)
        for hour in range(9, 18):  
            slot_time = current_day.replace(hour=hour)
            time_slots.append(slot_time)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=slot.strftime('%d.%m %H:%M'),
                callback_data=f"select_time={slot.isoformat()}"
            )] for slot in time_slots[:14] 
        ]
    )
    
    await state.set_state(QueueState.select_time)
    await callback.message.edit_text(
        f"Выбрана услуга: {service['name']}\n"
        f"Выберите время:",
        reply_markup=keyboard
    )
    await callback.answer()


@user_router.callback_query(F.data.contains('select_time'))
async def select_time_handler(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split('=')[1]
    selected_time = datetime.fromisoformat(time_str)
    
    await state.update_data(scheduled_time=selected_time)
    data = await state.get_data()
    
    service = await Service.get_service_by_id(data['service_id'], db)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='✅ Подтвердить', callback_data='confirm_booking'),
                InlineKeyboardButton(text='❌ Отменить', callback_data='cancel_booking')
            ]
        ]
    )
    
    await callback.message.edit_text(
        f"Подтверждение записи:\n\n"
        f"🔹 Услуга: {service['name']}\n"
        f"⏱ Время: {selected_time.strftime('%d.%m.%Y %H:%M')}\n"
        f"💰 Цена: {service['price']} руб.\n\n"
        f"Подтвердить запись?",
        reply_markup=keyboard
    )
    await callback.answer()


@user_router.callback_query(F.data == 'confirm_booking')
async def confirm_booking_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Validate required data exists
    if 'service_id' not in data or 'scheduled_time' not in data:
        await callback.message.edit_text(
            '❌ Ошибка: данные записи не найдены.\n'
            'Пожалуйста, начните процесс записи заново.'
        )
        await state.clear()
        await callback.answer()
        return
    
    user = User(callback.from_user.id, callback.from_user.username, '', db)
    user_data = await user.get_user()
    
    if not user_data:
        await callback.answer('Ошибка: пользователь не найден!')
        return
    
    queue_entry = QueueEntry(
        user_id=user_data['id'],
        service_id=data['service_id'],
        scheduled_time=data['scheduled_time'],
        db=db
    )
    
    entry_id = await queue_entry.save()
    
    if entry_id:
        service = await Service.get_service_by_id(data['service_id'], db)
        await callback.message.edit_text(
            f"✅ Запись подтверждена!\n\n"
            f"🔹 Услуга: {service['name']}\n"
            f"⏱ Время: {data['scheduled_time'].strftime('%d.%m.%Y %H:%M')}\n"
            f"💰 Цена: {service['price']} руб.\n\n"
            f"Вы будете уведомлены о подходе вашей очереди."
        )
    else:
        await callback.message.edit_text('❌ Ошибка при создании записи!')
    
    await state.clear()
    await callback.answer()


@user_router.callback_query(F.data == 'cancel_booking')
async def cancel_booking_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('❌ Запись отменена.')
    await state.clear()
    await callback.answer()


@user_router.message(lambda m: m.text == '👤 Моя очередь')
async def my_queue_handler(msg: Message):
    user = User(msg.from_user.id, msg.from_user.username, '', db)
    user_data = await user.get_user()
    
    if not user_data:
        await msg.answer('Ошибка: пользователь не найден!')
        return
    
    entries = await QueueEntry.get_user_queue(user_data['id'], db)
    
    if not entries:
        await msg.answer('У вас нет активных записей в очереди.')
        return
    
    for entry in entries:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text='❌ Отменить запись',
                    callback_data=f'cancel_entry={entry["id"]}'
                )]
            ]
        )
        
        await msg.answer(
            f"📋 Ваша запись:\n\n"
            f"🔹 Услуга: {entry['service_name']}\n"
            f"⏱ Время: {entry['scheduled_time'].strftime('%d.%m.%Y %H:%M')}\n"
            f"💰 Цена: {entry['price']} руб.\n"
            f"📍 Позиция в очереди: {entry['position']}",
            reply_markup=keyboard
        )


@user_router.callback_query(F.data.contains('cancel_entry'))
async def cancel_entry_handler(callback: CallbackQuery):
    entry_id = int(callback.data.split('=')[1])
    
    user = User(callback.from_user.id, callback.from_user.username, '', db)
    user_data = await user.get_user()
    
    if not user_data:
        await callback.answer('Ошибка: пользователь не найден!')
        return
    
    success = await QueueEntry.cancel_entry(entry_id, user_data['id'], db)
    
    if success:
        await callback.message.edit_text('✅ Запись успешно отменена!')
        await callback.answer('Запись отменена!')
    else:
        await callback.answer('❌ Ошибка при отмене записи!')


@user_router.message(Command('view_services'))
async def view_services_command(msg: Message):
    await view_services_handler(msg)


@user_router.message(Command('join_queue'))
async def join_queue_command(msg: Message, state: FSMContext):
    await join_queue_handler(msg, state)


@user_router.message(Command('my_queue'))
async def my_queue_command(msg: Message):
    await my_queue_handler(msg)