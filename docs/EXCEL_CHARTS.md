# Excel Export with Interactive Charts

## Overview

Excel export feature has been enhanced with 4 interactive charts that visualize user's diary data in a clear and actionable way.

## Charts Included

### 1. Line Chart - Calories Eaten vs Burned
**Sheet:** Графики  
**Purpose:** Shows daily trend of calorie intake vs expenditure over time  
**Axes:**
- X-axis: Date (DD.MM format)
- Y-axis: Calories (kcal)
- Two lines: "Съедено" (eaten) and "Расход" (burned)

**Insights:** Helps users see if they're consistently eating more or less than they burn

### 2. Bar Chart - Daily Calorie Balance
**Sheet:** Графики  
**Purpose:** Shows daily calorie deficit or surplus  
**Axes:**
- X-axis: Date (DD.MM format)
- Y-axis: Balance (kcal)
- Positive values = surplus (eating more than burning)
- Negative values = deficit (eating less than burning)

**Insights:** Quickly identifies which days had largest deficits/surpluses

### 3. Pie Chart - Macronutrient Distribution
**Sheet:** Графики  
**Purpose:** Shows average distribution of protein, fat, and carbs over the period  
**Data:** Average grams per day for each macronutrient  
**Sections:**
- Белки (Protein)
- Жиры (Fat)
- Углеводы (Carbs)

**Insights:** Helps users see if their diet is balanced or if one macro is dominating

### 4. Pie Chart - Meal Type Distribution
**Sheet:** Графики  
**Purpose:** Shows distribution of meals by type (breakfast/lunch/dinner/snack)  
**Data:** Count of each meal type over the period  
**Sections:**
- Завтрак (Breakfast)
- Обед (Lunch)
- Ужин (Dinner)
- Перекус (Snack)

**Insights:** Shows eating patterns - e.g., if user is skipping breakfast or snacking too much

## Implementation Details

### Files Modified
- `bot/handlers/export.py`: Added MealEntry query for meal distribution
- `bot/utils/excel_export.py`: Added `_create_charts_sheet()` function

### Dependencies
```python
from openpyxl.chart import LineChart, BarChart, PieChart, Reference
```

These are already included in `openpyxl` package (no additional dependencies needed)

### Data Requirements
- **Minimum:** 2 DayEntry records for charts to be generated
- **Meal chart:** Requires MealEntry records (optional, gracefully skipped if missing)
- **Macro chart:** Requires protein/fat/carbs data (gracefully skipped if missing)

## Testing

Run the test script to generate sample Excel with all charts:
```bash
python3 test_charts.py
```

This will:
1. Create 14 days of test DayEntry data
2. Create ~47 test MealEntry records (breakfast/lunch/dinner/snacks)
3. Generate `test_export_with_charts.xlsx`
4. Open the file in Excel/Numbers

## Chart Specifications

| Chart Type | Height | Width | Position | Style |
|------------|--------|-------|----------|-------|
| Line Chart | 10     | 20    | E5       | 10    |
| Bar Chart  | 10     | 20    | Dynamic  | 10    |
| Pie Chart (Macros) | 10 | 12 | Dynamic | Default |
| Pie Chart (Meals) | 10 | 12 | Dynamic | Default |

## Error Handling

### Insufficient Data
If less than 2 days of data:
```
"Недостаточно данных для графиков (минимум 2 дня)"
```

### Missing Macro Data
If no protein/fat/carbs data:
```
"Нет данных о макронутриентах"
```

### Missing Meal Data
If no MealEntry records:
- Meal distribution chart is gracefully skipped
- Other 3 charts still render

## Future Enhancements (Not Implemented Yet)

### Optional: Telegram Graph Visualization
- Generate PNG images using matplotlib/plotly
- Send directly in Telegram (no need to open Excel)
- Command: `/stats` or button in menu

### Optional: AI Insights
- Analyze patterns in chart data
- Generate text recommendations
- Example: "Ты ешь на 200 ккал больше по выходным"

### Optional: Gamification
- Streak tracking (consecutive days in deficit)
- Achievements (e.g., "7 дней подряд в дефиците!")
- Progress badges

## Notes

- Charts are non-intrusive - they enhance existing export without changing UX
- All text is in Russian for user consistency
- Chart titles clearly explain what each visualization shows
- Data is sorted chronologically for meaningful trends
