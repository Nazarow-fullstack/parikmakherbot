from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from database.user import User
from database.service import Service
from database.queue_entry import QueueEntry
from config import db
from keyboards.admin_keyboards import admin_keyboard
from keyboards.user_keyboard import user_keyboard
from states.service_states import ServiceState

admin_router = Router()


@admin_router.message(Command('start'))
async def start_handler(msg: Message):
    if msg.from_user.last_name:
        fullname = msg.from_user.first_name + ' ' + msg.from_user.last_name
    else:
        fullname = msg.from_user.first_name
    
    user = User(msg.from_user.id, msg.from_user.username, fullname, db)
    if not await user.get_user():
        await user.save()
    
    keyboard = admin_keyboard if await user.check_status() else user_keyboard
    await msg.answer('Добро пожаловать в систему управления парикмахерской! 💇‍♀️', reply_markup=keyboard)


@admin_router.message(lambda m: m.text == '➕ Добавить услугу')
async def add_service_handler(msg: Message, state: FSMContext):
    user = User(msg.from_user.id, msg.from_user.username, '', db)
    if not await user.check_status():
        await msg.answer('❌ У вас нет прав администратора!')
        return
    
    await state.set_state(ServiceState.name)
    await msg.answer('Введите название услуги:')


@admin_router.message(ServiceState.name)
async def service_name_handler(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(ServiceState.duration)
    await msg.answer('Введите длительность услуги (в минутах):')


@admin_router.message(ServiceState.duration)
async def service_duration_handler(msg: Message, state: FSMContext):
    try:
        duration = int(msg.text)
        await state.update_data(duration=duration)
        await state.set_state(ServiceState.price)
        await msg.answer('Введите цену услуги:')
    except ValueError:
        await msg.answer('Неверный формат. Введите число (минуты):')


@admin_router.message(ServiceState.price)
async def service_price_handler(msg: Message, state: FSMContext):
    try:
        price = float(msg.text)
        await state.update_data(price=price)
        data = await state.get_data()
        
        service = Service(
            name=data['name'],
            duration=data['duration'],
            price=data['price'],
            db=db
        )
        
        service_id = await service.save()
        
        if service_id:
            await msg.answer(
                f'✅ Услуга успешно добавлена!\n\n'
                f'🔹 Название: {service.name}\n'
                f'⏱ Длительность: {service.duration} мин\n'
                f'💰 Цена: {service.price} руб.',
                reply_markup=admin_keyboard
            )
        else:
            await msg.answer('❌ Ошибка при добавлении услуги!', reply_markup=admin_keyboard)
        
        await state.clear()
        
    except ValueError:
        await msg.answer('Неверный формат цены. Введите число:')


@admin_router.message(lambda m: m.text == '📋 Посмотреть услуги')
async def view_services_admin_handler(msg: Message):
    user = User(msg.from_user.id, msg.from_user.username, '', db)
    if not await user.check_status():
        await msg.answer('❌ У вас нет прав администратора!')
        return
    
    services = await Service.get_services(db)
    if not services:
        await msg.answer('Услуги пока не добавлены.')
        return
    
    for service in services:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text='✏️ Редактировать', callback_data=f'update_service={service["id"]}'),
                    InlineKeyboardButton(text='🗑 Удалить', callback_data=f'delete_service={service["id"]}')
                ]
            ]
        )
        
        await msg.answer(
            f"🔹 {service['name']}\n"
            f"⏱ Длительность: {service['duration']} мин\n"
            f"💰 Цена: {service['price']} руб.",
            reply_markup=keyboard
        )


@admin_router.callback_query(F.data.contains('delete_service'))
async def delete_service_handler(callback: CallbackQuery):
    service_id = int(callback.data.split('=')[1])
    
    success = await Service.delete_service(service_id, db)
    
    if success:
        await callback.message.delete()
        await callback.answer('✅ Услуга успешно удалена!', show_alert=True)
    else:
        await callback.answer('❌ Ошибка при удалении услуги!')


@admin_router.callback_query(F.data.contains('update_service'))
async def update_service_handler(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split('=')[1])
    await state.update_data(update_service_id=service_id)
    await state.set_state(ServiceState.update_name)
    await callback.message.answer('Введите новое название услуги:')
    await callback.answer()


@admin_router.message(ServiceState.update_name)
async def update_service_name_handler(msg: Message, state: FSMContext):
    await state.update_data(update_name=msg.text)
    await state.set_state(ServiceState.update_duration)
    await msg.answer('Введите новую длительность услуги (в минутах):')


@admin_router.message(ServiceState.update_duration)
async def update_service_duration_handler(msg: Message, state: FSMContext):
    try:
        duration = int(msg.text)
        await state.update_data(update_duration=duration)
        await state.set_state(ServiceState.update_price)
        await msg.answer('Введите новую цену услуги:')
    except ValueError:
        await msg.answer('Неверный формат. Введите число (минуты):')


@admin_router.message(ServiceState.update_price)
async def update_service_price_handler(msg: Message, state: FSMContext):
    try:
        price = float(msg.text)
        await state.update_data(update_price=price)
        data = await state.get_data()
        
        success = await Service.update_service(
            service_id=data['update_service_id'],
            name=data['update_name'],
            duration=data['update_duration'],
            price=data['update_price'],
            db=db
        )
        
        if success:
            await msg.answer('✅ Услуга успешно обновлена!', reply_markup=admin_keyboard)
        else:
            await msg.answer('❌ Ошибка при обновлении услуги!', reply_markup=admin_keyboard)
        
        await state.clear()
        
    except ValueError:
        await msg.answer('Неверный формат цены. Введите число:')


@admin_router.message(lambda m: m.text == '📊 Посмотреть очередь')
async def view_queue_handler(msg: Message):
    user = User(msg.from_user.id, msg.from_user.username, '', db)
    if not await user.check_status():
        await msg.answer('❌ У вас нет прав администратора!')
        return
    
    entries = await QueueEntry.get_all_queue(db)
    
    if not entries:
        await msg.answer('Очередь пуста.')
        return
    
    for entry in entries:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text='✅ Выполнено', callback_data=f'complete_entry={entry["id"]}'),
                    InlineKeyboardButton(text='❌ Отменить', callback_data=f'cancel_admin_entry={entry["id"]}')
                ],
                [
                    InlineKeyboardButton(text='🔼 Вверх', callback_data=f'move_up={entry["id"]}'),
                    InlineKeyboardButton(text='🔽 Вниз', callback_data=f'move_down={entry["id"]}')
                ]
            ]
        )
        
        await msg.answer(
            f"📋 Запись #{entry['position']}\n\n"
            f"👤 Клиент: {entry['full_name']} (@{entry['username'] or 'нет'})\n"
            f"🔹 Услуга: {entry['service_name']}\n"
            f"⏱ Время: {entry['scheduled_time'].strftime('%d.%m.%Y %H:%M')}\n"
            f"💰 Цена: {entry['price']} руб.\n"
            f"📅 Создано: {entry['created_at'].strftime('%d.%m.%Y %H:%M')}",
            reply_markup=keyboard
        )


@admin_router.callback_query(F.data.contains('complete_entry'))
async def complete_entry_handler(callback: CallbackQuery):
    entry_id = int(callback.data.split('=')[1])
    
    success = await QueueEntry.update_status(entry_id, 'completed', db)
    
    if success:
        await callback.message.edit_text('✅ Запись отмечена как выполненная!')
        await callback.answer('Запись выполнена!')
    else:
        await callback.answer('❌ Ошибка при обновлении записи!')


@admin_router.callback_query(F.data.contains('cancel_admin_entry'))
async def cancel_admin_entry_handler(callback: CallbackQuery):
    entry_id = int(callback.data.split('=')[1])
    
    success = await QueueEntry.update_status(entry_id, 'cancelled', db)
    
    if success:
        await callback.message.edit_text('❌ Запись отменена администратором!')
        await callback.answer('Запись отменена!')
    else:
        await callback.answer('❌ Ошибка при отмене записи!')


@admin_router.callback_query(F.data.contains('move_up'))
async def move_up_handler(callback: CallbackQuery):
    entry_id = int(callback.data.split('=')[1])
    
    success = await QueueEntry.change_position(entry_id, 'up', db)
    
    if success:
        await callback.answer('✅ Запись перемещена вверх!', show_alert=True)
        await callback.message.answer('Очередь обновлена. Используйте "📊 Посмотреть очередь" для просмотра изменений.')
    else:
        await callback.answer('❌ Невозможно переместить выше! Запись уже первая в очереди.', show_alert=True)


@admin_router.callback_query(F.data.contains('move_down'))
async def move_down_handler(callback: CallbackQuery):
    entry_id = int(callback.data.split('=')[1])
    
    success = await QueueEntry.change_position(entry_id, 'down', db)
    
    if success:
        await callback.answer('✅ Запись перемещена вниз!', show_alert=True)
        await callback.message.answer('Очередь обновлена. Используйте "📊 Посмотреть очередь" для просмотра изменений.')
    else:
        await callback.answer('❌ Невозможно переместить ниже! Запись уже последняя в очереди.', show_alert=True)


@admin_router.message(lambda m: m.text == '👥 Посмотреть пользователей')
async def view_users_handler(msg: Message):
    user = User(msg.from_user.id, msg.from_user.username, '', db)
    if not await user.check_status():
        await msg.answer('❌ У вас нет прав администратора!')
        return
    
    users = await User.get_all_users(db)
    
    if not users:
        await msg.answer('Пользователи не найдены.')
        return
    
    for user_data in users:
        status = "👑 Администратор" if user_data['is_staff'] else "👤 Пользователь"
        await msg.answer(
            f"{status}\n\n"
            f"🆔 ID: {user_data['telegram_id']}\n"
            f"👤 Имя: {user_data['full_name']}\n"
            f"📱 Username: @{user_data['username'] or 'нет'}\n"
            f"📅 Регистрация: {user_data['created_at'].strftime('%d.%m.%Y %H:%M')}"
        )



@admin_router.message(Command('add_service'))
async def add_service_command(msg: Message, state: FSMContext):
    await add_service_handler(msg, state)


@admin_router.message(Command('view_services'))
async def view_services_command(msg: Message):
    await view_services_admin_handler(msg)


@admin_router.message(Command('view_queue'))
async def view_queue_command(msg: Message):
    await view_queue_handler(msg)