import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)
n_boxes = 150

# Генерируем даты: год назад → сегодня + 7 дней
today = datetime.today()
dates = pd.date_range(start=today - timedelta(days=365), end=today + timedelta(days=7), freq='D')

breakdowns = []
for box_id in range(1, n_boxes + 1):
    for date in dates:
        if np.random.random() < 0.03:
            breakdowns.append({
                'box_id': box_id,
                'breakdown_date': date,
                'downtime_hours': np.random.randint(2, 48),
                'last_maintenance_date': date - timedelta(days=np.random.randint(30, 180)),
            })

df = pd.DataFrame(breakdowns)
# Смотрим, сколько поломок в ближайшие 7 дней от today
future = df[(df['breakdown_date'] > today) & (df['breakdown_date'] <= today + timedelta(days=7))]
print(f"Поломок с today ({today.date()}) по today+7: {len(future)}")
print(f"Уникальных боксов с поломками в будущем: {future['box_id'].nunique()}")
