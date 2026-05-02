from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import Group, User, GroupCurator
from bot.services.report_service import generate_group_report, generate_curator_attendance_report
from bot.logger import logger
from aiogram.types import FSInputFile
import io

router = Router()

class ReportStates(StatesGroup):
    waiting_dates = State()

async def get_starosta_group(session, user_id):
    stmt = select(Group).where(Group.starosta_id == user_id)
    return (await session.execute(stmt)).scalars().first()

@router.callback_query(F.data.startswith("reportgroup_"))
async def choose_group_for_report(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id, report_type="general")
    await callback.message.answer("Введите начальную и конечную дату (ГГГГ-ММ-ДД ГГГГ-ММ-ДД) или одну дату (ГГГГ-ММ-ДД):")
    await state.set_state(ReportStates.waiting_dates)
    await callback.answer()

@router.callback_query(F.data.startswith("curatt_"))
async def curator_attendance_request(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[1])
    await state.update_data(group_id=group_id, report_type="curator")
    await callback.message.answer("Введите начальную и конечную дату (ГГГГ-ММ-ДД ГГГГ-ММ-ДД) или одну дату:")
    await state.set_state(ReportStates.waiting_dates)
    await callback.answer()

@router.message(StateFilter(ReportStates.waiting_dates))
async def process_dates_and_generate(message: types.Message, state: FSMContext):
    data = await state.get_data()
    group_id = data["group_id"]
    report_type = data.get("report_type", "general")
    dates = message.text.strip().split()
    try:
        if len(dates) == 1:
            start_date = end_date = dates[0]
        elif len(dates) == 2:
            start_date, end_date = dates[0], dates[1]
        else:
            raise ValueError("Неверное количество дат")
        # Проверим формат
        from datetime import datetime
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except Exception:
        await message.answer("Ошибка формата дат. Введите даты в формате ГГГГ-ММ-ДД (одну или две через пробел).")
        return

    try:
        if report_type == "general":
            buf = await generate_group_report(group_id, start_date, end_date)
            caption = f"Отчёт по группе за {start_date} — {end_date}"
        else:  # curator
            buf = await generate_curator_attendance_report(group_id, start_date, end_date)
            caption = f"Процент посещаемости группы за {start_date} — {end_date}"

        file = FSInputFile(buf, filename="report.xlsx")
        await message.answer_document(file, caption=caption)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        await message.answer(f"Ошибка при создании отчёта: {e}")
    finally:
        await state.clear()