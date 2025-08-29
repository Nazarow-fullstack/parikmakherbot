from aiogram.fsm.state import State, StatesGroup


class ServiceState(StatesGroup):
    name = State()
    duration = State()
    price = State()
   
    update_name = State()
    update_duration = State()
    update_price = State()


class QueueState(StatesGroup):
    select_service = State()
    select_time = State()
    confirm_booking = State()
