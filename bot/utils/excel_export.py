"""
Excel export functionality
"""
from datetime import date, timedelta
from typing import List
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import LineChart, BarChart, PieChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.drawing.fill import ColorChoice
import io

from bot.database.models import User, DayEntry, MealEntry


def create_excel_export(user: User, entries: List[DayEntry], meal_entries: List[MealEntry] = None, days: int = 7) -> io.BytesIO:
    """
    Create Excel file with diary data and charts
    
    Args:
        user: User object
        entries: List of DayEntry objects
        meal_entries: List of MealEntry objects (optional, for meal distribution chart)
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
    _create_charts_sheet(wb, entries, meal_entries or [])
    
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


def _create_charts_sheet(wb: Workbook, entries: List[DayEntry], meal_entries: List[MealEntry]):
    """Create charts sheet with visualizations"""
    ws = wb.create_sheet("Графики")
    
    if not entries or len(entries) < 2:
        ws['A1'] = 'Недостаточно данных для графиков (минимум 2 дня)'
        ws['A1'].font = Font(bold=True, size=12)
        return
    
    # Title
    ws['A1'] = 'Визуализация данных'
    ws['A1'].font = Font(bold=True, size=14)
    
    # ========== CHART 1: Line Chart - Calories (eaten vs burned) ==========
    ws['A3'] = 'График калорий (съедено vs расход)'
    ws['A3'].font = Font(bold=True, size=12)
    
    # Prepare data for line chart
    ws['A5'] = 'Дата'
    ws['B5'] = 'Съедено'
    ws['C5'] = 'Расход'
    
    row = 6
    for entry in sorted(entries, key=lambda x: x.entry_date):
        ws.cell(row=row, column=1, value=entry.entry_date.strftime('%d.%m'))
        ws.cell(row=row, column=2, value=entry.kcal_eaten or 0)
        ws.cell(row=row, column=3, value=entry.kcal_burned_total or 0)
        row += 1
    
    # Create line chart
    line_chart = LineChart()
    line_chart.title = "Калории: съедено vs расход"
    line_chart.style = 10
    line_chart.y_axis.title = 'Ккал'
    line_chart.x_axis.title = 'Дата'
    line_chart.height = 10
    line_chart.width = 20
    
    data = Reference(ws, min_col=2, min_row=5, max_row=row-1, max_col=3)
    cats = Reference(ws, min_col=1, min_row=6, max_row=row-1)
    line_chart.add_data(data, titles_from_data=True)
    line_chart.set_categories(cats)
    
    # Add chart to sheet
    ws.add_chart(line_chart, "E5")
    
    # ========== CHART 2: Bar Chart - Daily Balance ==========
    balance_start_row = row + 3
    ws.cell(row=balance_start_row, column=1, value='Баланс калорий по дням')
    ws.cell(row=balance_start_row, column=1).font = Font(bold=True, size=12)
    
    ws.cell(row=balance_start_row + 2, column=1, value='Дата')
    ws.cell(row=balance_start_row + 2, column=2, value='Баланс')
    
    balance_data_row = balance_start_row + 3
    for entry in sorted(entries, key=lambda x: x.entry_date):
        ws.cell(row=balance_data_row, column=1, value=entry.entry_date.strftime('%d.%m'))
        ws.cell(row=balance_data_row, column=2, value=entry.kcal_balance or 0)
        balance_data_row += 1
    
    # Create bar chart
    bar_chart = BarChart()
    bar_chart.type = "col"
    bar_chart.title = "Баланс калорий (дефицит/профицит)"
    bar_chart.style = 10
    bar_chart.y_axis.title = 'Ккал'
    bar_chart.x_axis.title = 'Дата'
    bar_chart.height = 10
    bar_chart.width = 20
    
    data = Reference(ws, min_col=2, min_row=balance_start_row + 2, max_row=balance_data_row - 1)
    cats = Reference(ws, min_col=1, min_row=balance_start_row + 3, max_row=balance_data_row - 1)
    bar_chart.add_data(data, titles_from_data=True)
    bar_chart.set_categories(cats)
    
    ws.add_chart(bar_chart, f"E{balance_start_row}")
    
    # ========== CHART 3: Pie Chart - Macronutrients Distribution ==========
    macro_start_row = balance_data_row + 3
    ws.cell(row=macro_start_row, column=1, value='Распределение макронутриентов (средние за период)')
    ws.cell(row=macro_start_row, column=1).font = Font(bold=True, size=12)
    
    # Calculate averages
    avg_protein = sum(e.protein for e in entries if e.protein) / len([e for e in entries if e.protein]) if any(e.protein for e in entries) else 0
    avg_fat = sum(e.fat for e in entries if e.fat) / len([e for e in entries if e.fat]) if any(e.fat for e in entries) else 0
    avg_carbs = sum(e.carbs for e in entries if e.carbs) / len([e for e in entries if e.carbs]) if any(e.carbs for e in entries) else 0
    
    if avg_protein + avg_fat + avg_carbs > 0:
        ws.cell(row=macro_start_row + 2, column=1, value='Нутриент')
        ws.cell(row=macro_start_row + 2, column=2, value='Граммы')
        ws.cell(row=macro_start_row + 3, column=1, value='Белки')
        ws.cell(row=macro_start_row + 3, column=2, value=round(avg_protein, 1))
        ws.cell(row=macro_start_row + 4, column=1, value='Жиры')
        ws.cell(row=macro_start_row + 4, column=2, value=round(avg_fat, 1))
        ws.cell(row=macro_start_row + 5, column=1, value='Углеводы')
        ws.cell(row=macro_start_row + 5, column=2, value=round(avg_carbs, 1))
        
        # Create pie chart
        pie_chart = PieChart()
        pie_chart.title = "Распределение БЖУ (г)"
        pie_chart.height = 10
        pie_chart.width = 12
        
        labels = Reference(ws, min_col=1, min_row=macro_start_row + 3, max_row=macro_start_row + 5)
        data = Reference(ws, min_col=2, min_row=macro_start_row + 2, max_row=macro_start_row + 5)
        pie_chart.add_data(data, titles_from_data=True)
        pie_chart.set_categories(labels)
        
        ws.add_chart(pie_chart, f"E{macro_start_row}")
    else:
        ws.cell(row=macro_start_row + 2, column=1, value='Нет данных о макронутриентах')
    
    # ========== CHART 4: Pie Chart - Meal Type Distribution ==========
    if meal_entries:
        meal_start_row = macro_start_row + 8
        ws.cell(row=meal_start_row, column=1, value='Распределение приёмов пищи')
        ws.cell(row=meal_start_row, column=1).font = Font(bold=True, size=12)
        
        # Count meals by type
        from bot.database.models import MealType
        meal_counts = {}
        for meal in meal_entries:
            meal_type = meal.meal_type.value if meal.meal_type else 'unknown'
            meal_counts[meal_type] = meal_counts.get(meal_type, 0) + 1
        
        if meal_counts:
            # Map English to Russian
            meal_names = {
                'breakfast': 'Завтрак',
                'lunch': 'Обед',
                'dinner': 'Ужин',
                'snack': 'Перекус'
            }
            
            ws.cell(row=meal_start_row + 2, column=1, value='Тип приёма')
            ws.cell(row=meal_start_row + 2, column=2, value='Количество')
            
            meal_data_row = meal_start_row + 3
            for meal_type, count in sorted(meal_counts.items()):
                meal_name = meal_names.get(meal_type, meal_type.capitalize())
                ws.cell(row=meal_data_row, column=1, value=meal_name)
                ws.cell(row=meal_data_row, column=2, value=count)
                meal_data_row += 1
            
            # Create pie chart
            meal_pie_chart = PieChart()
            meal_pie_chart.title = "Распределение приёмов пищи"
            meal_pie_chart.height = 10
            meal_pie_chart.width = 12
            
            labels = Reference(ws, min_col=1, min_row=meal_start_row + 3, max_row=meal_data_row - 1)
            data = Reference(ws, min_col=2, min_row=meal_start_row + 2, max_row=meal_data_row - 1)
            meal_pie_chart.add_data(data, titles_from_data=True)
            meal_pie_chart.set_categories(labels)
            
            ws.add_chart(meal_pie_chart, f"E{meal_start_row}")
        else:
            ws.cell(row=meal_start_row + 2, column=1, value='Нет данных о приёмах пищи')
    
    # Auto-adjust column widths
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
