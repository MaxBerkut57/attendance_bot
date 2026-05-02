import io
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import select
from bot.db.database import async_session
from bot.db.models import (Poll, Attendance, User, GroupMembership,
                           Group, GroupCurator, Schedule, PollMessage)
from bot.logger import logger
from aiogram import Bot
from aiogram.types import FSInputFile
from bot.services.bot_instance import get_bot

async def generate_attendance_excel(poll_id: int) -> io.BytesIO:
    """Создаёт Excel‑файл с результатами опроса."""
    async with async_session() as session:
        poll = await session.get(Poll, poll_id)
        if not poll:
            raise ValueError("Опрос не найден")
        schedule = await session.get(Schedule, poll.schedule_id)
        group = await session.get(Group, schedule.group_id)

        # Все студенты группы (с ФИО)
        members = (await session.execute(
            select(User, GroupMembership).join(
                GroupMembership, GroupMembership.user_id == User.user_id
            ).where(GroupMembership.group_id == group.id)
        )).all()

        data = []
        for user, _ in members:
            attendance = await session.get(Attendance, (poll_id, user.user_id))
            if attendance:
                status = "присутствовал" if attendance.status == "present" else "отсутствовал"
            else:
                status = "не отметился"
            data.append((user.full_name, status))

        df = pd.DataFrame(data, columns=["ФИО", "Статус"])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f"Опрос {poll_id}")
        buf.seek(0)
        return buf

async def send_report_to_starosta(poll: Poll):
    """Отправляет отчёт старосте группы."""
    bot = get_bot()
    async with async_session() as session:
        schedule = await session.get(Schedule, poll.schedule_id)
        group = await session.get(Group, schedule.group_id)
        if not group or not group.starosta_id:
            logger.info(f"No starosta for group {group.name if group else '?'}")
            return
        try:
            buf = await generate_attendance_excel(poll.id)
            discipline = schedule.discipline.replace(" ", "_")
            date_str = schedule.date.strftime("%d.%m.%Y")
            caption = f"Отчёт: {schedule.discipline} ({date_str} {schedule.time_start}-{schedule.time_end})"
            file = FSInputFile(buf, filename=f"{discipline}_{date_str}.xlsx")
            await bot.send_document(
                chat_id=group.starosta_id,
                document=file,
                caption=caption
            )
            poll.report_sent = True
            await session.commit()
            logger.info(f"Report sent to starosta {group.starosta_id} for poll {poll.id}")
        except Exception as e:
            logger.error(f"Failed to send report to starosta: {e}")

async def generate_group_report(group_id: int, start_date: str, end_date: str) -> io.BytesIO:
    """Отчёт по группе за период (для старосты/админа)."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте ГГГГ-ММ-ДД")

    async with async_session() as session:
        # Все занятия группы за период, у которых есть завершённые опросы
        schedules = (await session.execute(
            select(Schedule).join(Poll).where(
                Schedule.group_id == group_id,
                Schedule.date >= start,
                Schedule.date <= end,
                Poll.status == 'finished'
            )
        )).scalars().all()

        members = (await session.execute(
            select(User).join(GroupMembership).where(GroupMembership.group_id == group_id)
        )).scalars().all()

        rows = []
        for user in members:
            for sched in schedules:
                poll = (await session.execute(
                    select(Poll).where(Poll.schedule_id == sched.id)
                )).scalars().first()
                if not poll:
                    continue
                att = await session.get(Attendance, (poll.id, user.user_id))
                status = "присутствовал" if att and att.status == "present" else ("отсутствовал" if att else "не отметился")
                rows.append((user.full_name, sched.date, sched.discipline, status))

        df = pd.DataFrame(rows, columns=["ФИО", "Дата", "Дисциплина", "Статус"])
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Посещаемость")
        buf.seek(0)
        return buf

async def generate_curator_attendance_report(group_id: int, start_date: str, end_date: str) -> io.BytesIO:
    """Сводный процент посещаемости для куратора."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Неверный формат дат. Используйте ГГГГ-ММ-ДД")

    async with async_session() as session:
        schedules = (await session.execute(
            select(Schedule).join(Poll).where(
                Schedule.group_id == group_id,
                Schedule.date >= start,
                Schedule.date <= end,
                Poll.status == 'finished'
            )
        )).scalars().all()

        members = (await session.execute(
            select(User).join(GroupMembership).where(GroupMembership.group_id == group_id)
        )).scalars().all()

        total_lessons = len(schedules)
        student_stats = []
        for user in members:
            present = 0
            for sched in schedules:
                poll = (await session.execute(
                    select(Poll).where(Poll.schedule_id == sched.id)
                )).scalars().first()
                if not poll:
                    continue
                att = await session.get(Attendance, (poll.id, user.user_id))
                if att and att.status == 'present':
                    present += 1
            percentage = (present / total_lessons * 100) if total_lessons > 0 else 0
            student_stats.append((user.full_name, present, total_lessons, f"{percentage:.1f}%"))

        # Общий процент по группе
        total_present = sum(s[1] for s in student_stats)
        total_possible = len(members) * total_lessons
        group_percent = (total_present / total_possible * 100) if total_possible > 0 else 0

        df_students = pd.DataFrame(student_stats, columns=["ФИО", "Посещений", "Всего занятий", "Процент"])
        df_summary = pd.DataFrame([
            ["Общий процент посещаемости группы", f"{group_percent:.1f}%", "", ""]
        ], columns=df_students.columns)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df_students.to_excel(writer, index=False, sheet_name="По студентам")
            df_summary.to_excel(writer, startrow=len(student_stats)+2, index=False, sheet_name="По студентам")
        buf.seek(0)
        return buf