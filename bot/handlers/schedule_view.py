from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import Group, Schedule
from datetime import datetime, date
from bot.keyboards.calendar import generate_calendar

router = Router()

async def show_calendar_for_schedule(message: types.Message, state: FSMContext):
    today = date.today()
    await message.answer("Выберите дату:", reply_markup=generate_calendar(today, "view_sched"))
    await state.set_state("schedule_view:waiting_date")

@router.message(F.text == "📅 Расписание")
async def schedule_view_start(message: types.Message, state: FSMContext):
    await state.clear()
    await show_calendar_for_schedule(message, state)

@router.callback_query(F.data.startswith("view_sched:"))
async def show_schedule_on_date(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    # Здесь нужно определить, какую группу смотреть: для студента – из членства, для старосты – свою, для админа – можно предложить выбор, но пока упростим: ищем пользователя и его группу.
    user_id = callback.from_user.id
    async with async_session() as session:
        from bot.db.models import GroupMembership, Group
        # Предполагаем, что студент/староста состоит в одной группе (или берём первую)
        membership = (await session.execute(
            select(GroupMembership).where(GroupMembership.user_id == user_id)
        )).scalars().first()
        if not membership:
            await callback.message.answer("Вы не состоите в группе. Расписание недоступно.")
            await callback.answer()
            return
        group = await session.get(Group, membership.group_id)
        schedules = (await session.execute(
            select(Schedule).where(Schedule.group_id == group.id, Schedule.date == selected_date)
        )).scalars().all()
        if not schedules:
            await callback.message.answer("На эту дату занятий нет.")
        else:
            text = f"📅 Расписание на {date_str} (группа {group.name}):\n"
            for s in schedules:
                text += f"{s.time_start.strftime('%H:%M')} – {s.time_end.strftime('%H:%M')} {s.discipline} ({s.type}) {s.audience or ''}\n"
            await callback.message.answer(text)
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "calendar_ignore")
async def ignore_calendar(callback: types.CallbackQuery):
    await callback.answer()