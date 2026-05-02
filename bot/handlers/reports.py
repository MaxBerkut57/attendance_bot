from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.types import BufferedInputFile
from bot.db.database import async_session
from bot.services.report_service import (
    generate_group_report_for_date,
    generate_curator_attendance_report_for_date,
    generate_curator_attendance_report_for_period
)
from bot.logger import logger
from datetime import date, datetime, timedelta
from bot.keyboards.calendar import generate_calendar
from sqlalchemy import select
from bot.db.models import Schedule, Poll

router = Router()

cancel_kb = types.InlineKeyboardMarkup(
    inline_keyboard=[[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]]
)

class ReportState(StatesGroup):
    waiting_date = State()
    waiting_subject = State()
    waiting_start_date = State()
    waiting_end_date = State()

async def show_calendar(message: types.Message, state: FSMContext, prefix: str):
    today = date.today()
    await message.answer(
        "Выберите дату:",
        reply_markup=generate_calendar(today, prefix)
    )
    await state.set_state(ReportState.waiting_date)

@router.callback_query(F.data.startswith("reportgroup_"))
async def choose_group_for_report(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id, report_type="general")
    await show_calendar(callback.message, state, "report_date")
    await callback.answer()

@router.callback_query(F.data.startswith("curatt_"))
async def curator_attendance_request(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id, report_type="curator")
    await show_calendar(callback.message, state, "cur_start")
    await state.set_state(ReportState.waiting_start_date)
    await callback.answer()

@router.callback_query(F.data.startswith("cur_start:"), StateFilter(ReportState.waiting_start_date))
async def curator_start_date_selected(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    start_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    await state.update_data(start_date=start_date)
    await callback.message.answer(
        "Теперь выберите конечную дату периода:",
        reply_markup=generate_calendar(start_date, "cur_end")
    )
    await state.set_state(ReportState.waiting_end_date)
    await callback.answer()

@router.callback_query(F.data.startswith("cur_end:"), StateFilter(ReportState.waiting_end_date))
async def curator_end_date_selected(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    end_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    data = await state.get_data()
    start_date = data["start_date"]
    group_id = data["group_id"]
    if end_date < start_date:
        await callback.message.answer("Конечная дата не может быть раньше начальной.")
        await state.clear()
        await callback.answer()
        return
    try:
        buf_bytes = await generate_curator_attendance_report_for_period(group_id, start_date, end_date)
        caption = f"Посещаемость группы с {start_date} по {end_date}"
        file = BufferedInputFile(buf_bytes, filename="attendance.xlsx")
        await callback.message.answer_document(file, caption=caption)
    except Exception as e:
        logger.error(f"Curator report error: {e}")
        await callback.message.answer(f"Ошибка: {e}")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("cal_shift:"))
async def calendar_shift(callback: types.CallbackQuery, state: FSMContext):
    _, prefix, date_str = callback.data.split(":")
    shift_date = date.fromisoformat(date_str)
    await callback.message.edit_reply_markup(
        reply_markup=generate_calendar(shift_date, prefix)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("report_date:"), StateFilter(ReportState.waiting_date))
async def general_report_date_selected(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    await state.update_data(selected_date=selected_date)
    await state.set_state(ReportState.waiting_subject)
    async with async_session() as session:
        data = await state.get_data()
        group_id = data["group_id"]
        schedules = (await session.execute(
            select(Schedule).join(Poll).where(
                Schedule.group_id == group_id,
                Schedule.date == selected_date,
                Poll.status.in_(['active', 'finished'])
            )
        )).scalars().all()
        if not schedules:
            await callback.message.answer("Занятий с опросами на эту дату нет.")
            await state.clear()
            await callback.answer()
            return
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=s.discipline, callback_data=f"subj_{s.id}")] for s in schedules
        ] + [[types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]])
        await callback.message.answer("Выберите дисциплину:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("cur_date:"), StateFilter(ReportState.waiting_date))
async def curator_date_selected(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    data = await state.get_data()
    group_id = data["group_id"]
    try:
        buf_bytes = await generate_curator_attendance_report_for_date(group_id, selected_date)
        caption = f"Посещаемость за {date_str}"
        file = BufferedInputFile(buf_bytes, filename="attendance.xlsx")
        await callback.message.answer_document(file, caption=caption)
    except Exception as e:
        logger.error(f"Curator report error: {e}")
        await callback.message.answer(f"Ошибка: {e}")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("subj_"), StateFilter(ReportState.waiting_subject))
async def subject_selected(callback: types.CallbackQuery, state: FSMContext):
    sched_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    group_id = data["group_id"]
    try:
        buf_bytes = await generate_group_report_for_date(group_id, sched_id)
        caption = "Отчёт по занятию"
        file = BufferedInputFile(buf_bytes, filename="report.xlsx")
        await callback.message.answer_document(file, caption=caption)
    except Exception as e:
        logger.error(f"Report error: {e}")
        await callback.message.answer(f"Ошибка: {e}")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_action", StateFilter(ReportState.waiting_date, ReportState.waiting_subject))
async def cancel_report(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer()