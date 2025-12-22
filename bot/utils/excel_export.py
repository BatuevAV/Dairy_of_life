"""
Excel export functionality
"""
from datetime import date, timedelta
from typing import List
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
import io

from bot.database.models import User, DayEntry


def create_excel_export(user: User, entries: List[DayEntry], days: int = 7) -> io.BytesIO:
    """
    Create Excel file with diary data
    
    Args:
        user: User object
        entries: List of DayEntry objects
        days: Number of days in report
    
    Returns:
        BytesIO buffer with Excel file
    """
    wb = Workbook()
    
    # Remove default sheet
    wb.remove(wb.active)
    
    # Create sheets
    _create_profile_sheet(wb, user)
    _create_diary_sheet(wb, entries)
    _create_summary_sheet(wb, entries, days)
    
    # Save to BytesIO
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer


def _create_profile_sheet(wb: Workbook, user: User):
    """Create profile sheet"""
    ws = wb.create_sheet("Профиль", 0)
    
    # Header
    ws['A1'] = 'Профиль пользователя'
    ws['A1'].font = Font(bold=True, size=14)
    
    # Profile data
    profile_data = [
        ['Параметр', 'Значение'],
        ['Telegram ID', user.telegram_user_id],
        ['Пол', 'Мужской' if user.gender == 'male' else 'Женский'],
        ['Возраст', f'{user.age} лет'],
        ['Рост', f'{user.height} см'],
        ['Режим ввода', 'Свободный' if user.input_mode.value == 'free' else 'Пошаговый'],
        ['Часовой пояс', user.timezone],
        ['', ''],
        ['Коэффициенты расчёта', ''],
        ['Ккал на шаг', user.step_kcal_coef],
        ['Зал (ккал/час)', user.gym_kcal_per_hour],
        ['Плавание (ккал/час)', user.swim_kcal_per_hour],
        ['Бег (ккал/час)', user.running_kcal_per_hour],
        ['Велосипед (ккал/час)', user.cycling_kcal_per_hour],
    ]
    
    for row_idx, row_data in enumerate(profile_data, start=3):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 3:  # Header row
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 20


def _create_diary_sheet(wb: Workbook, entries: List[DayEntry]):
    """Create diary sheet with all entries"""
    ws = wb.create_sheet("Дневник")
    
    # Prepare data
    data = []
    for entry in sorted(entries, key=lambda x: x.entry_date):
        data.append({
            'Дата': entry.entry_date.strftime('%Y-%m-%d'),
            'Вес (кг)': entry.weight or '',
            'Талия (см)': entry.waist or '',
            'Сон (ч)': entry.sleep_hours or '',
            'Шаги': entry.steps or '',
            'Тренировка': entry.workout_type.value if entry.workout_type else '',
            'Трен. (мин)': entry.workout_minutes or '',
            'BMR': entry.bmr or '',
            'Ккал шаги': entry.kcal_steps or '',
            'Ккал трен.': entry.kcal_workout or '',
            'Расход всего': entry.kcal_burned_total or '',
            'Съедено': entry.kcal_eaten or '',
            'Баланс': entry.kcal_balance or '',
            'Белки (г)': entry.protein or '',
            'Жиры (г)': entry.fat or '',
            'Углеводы (г)': entry.carbs or '',
        })
    
    if not data:
        ws['A1'] = 'Нет данных'
        return
    
    df = pd.DataFrame(data)
    
    # Write to sheet
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), 1):
        for c_idx, value in enumerate(row, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            
            # Header formatting
            if r_idx == 1:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                cell.font = Font(bold=True, color='FFFFFF')
                cell.alignment = Alignment(horizontal='center')
            
            # Highlight balance
            if r_idx > 1 and c_idx == 13:  # Balance column
                try:
                    balance_val = float(value) if value else 0
                    if balance_val > 0:
                        cell.fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                    elif balance_val < -500:
                        cell.fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                except:
                    pass
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 20)
        ws.column_dimensions[column_letter].width = adjusted_width


def _create_summary_sheet(wb: Workbook, entries: List[DayEntry], days: int):
    """Create summary sheet with statistics"""
    ws = wb.create_sheet("Сводка")
    
    # Title
    ws['A1'] = f'Сводка за {days} дней'
    ws['A1'].font = Font(bold=True, size=14)
    
    if not entries:
        ws['A3'] = 'Нет данных'
        return
    
    # Calculate statistics
    total_entries = len(entries)
    
    # Averages
    avg_weight = sum(e.weight for e in entries if e.weight) / len([e for e in entries if e.weight]) if any(e.weight for e in entries) else 0
    avg_sleep = sum(e.sleep_hours for e in entries if e.sleep_hours) / len([e for e in entries if e.sleep_hours]) if any(e.sleep_hours for e in entries) else 0
    avg_steps = sum(e.steps for e in entries if e.steps) / len([e for e in entries if e.steps]) if any(e.steps for e in entries) else 0
    avg_eaten = sum(e.kcal_eaten for e in entries if e.kcal_eaten) / len([e for e in entries if e.kcal_eaten]) if any(e.kcal_eaten for e in entries) else 0
    avg_burned = sum(e.kcal_burned_total for e in entries if e.kcal_burned_total) / len([e for e in entries if e.kcal_burned_total]) if any(e.kcal_burned_total for e in entries) else 0
    avg_balance = sum(e.kcal_balance for e in entries if e.kcal_balance) / len([e for e in entries if e.kcal_balance]) if any(e.kcal_balance for e in entries) else 0
    
    # Workout count
    workout_count = len([e for e in entries if e.workout_type])
    
    summary_data = [
        ['Показатель', 'Значение'],
        ['Всего записей', total_entries],
        ['Период', f'{entries[0].entry_date.strftime("%Y-%m-%d")} - {entries[-1].entry_date.strftime("%Y-%m-%d")}'],
        ['', ''],
        ['Средние значения', ''],
        ['Вес (кг)', f'{avg_weight:.1f}' if avg_weight else '-'],
        ['Сон (ч)', f'{avg_sleep:.1f}' if avg_sleep else '-'],
        ['Шаги', f'{avg_steps:.0f}' if avg_steps else '-'],
        ['Съедено (ккал)', f'{avg_eaten:.0f}' if avg_eaten else '-'],
        ['Расход (ккал)', f'{avg_burned:.0f}' if avg_burned else '-'],
        ['Баланс (ккал)', f'{avg_balance:.0f}' if avg_balance else '-'],
        ['', ''],
        ['Тренировок за период', workout_count],
    ]
    
    for row_idx, row_data in enumerate(summary_data, start=3):
        for col_idx, value in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            if row_idx == 3 or (isinstance(value, str) and value.endswith('значения')):
                cell.font = Font(bold=True)
                if row_idx == 3:
                    cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
    
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 20
