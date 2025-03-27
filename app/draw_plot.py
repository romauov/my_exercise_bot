import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json

def draw_plot(user_id, period='last'):
    with open(f'{user_id}_weights.json', 'r') as file:
        json_data = json.load(file)
    
    df = pd.DataFrame(json_data)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df = df.sort_values('date')
    

    period_map = {
        'last': 14,
        'month': 30,
        'quarter': 90,
        'year': 365,
        'all': 0
    }
    
    if period not in period_map:
        raise ValueError(f"Недопустимый период: {period}. Допустимые значения: {list(period_map.keys())}")
    
    n = period_map[period]
    if n != 0:
        last_records = df.tail(n)
    else:
        last_records = df

    avg_weight = round(np.nanmean(last_records['weight']), 2)

    resampled_data = None
    title_suffix = ''
    
    if period == 'quarter':
        last_records = last_records.set_index('date')
        resampled_data = last_records.resample('W').mean().reset_index()
        resampled_data.dropna(subset=['weight'], inplace=True)
        title_suffix = ' (усреднено по неделям)'
    elif period in ['year', 'all']:
        last_records = last_records.set_index('date')
        resampled_data = last_records.resample('ME').mean().reset_index()
        resampled_data.dropna(subset=['weight'], inplace=True)
        title_suffix = ' (усреднено по месяцам)'
    
    titles = {
        'last': 'Вес за последние 14 дней',
        'month': 'Вес за последние 30 дней',
        'quarter': f'Вес за последние 90 дней{title_suffix}',
        'year': f'Вес за последние 365 дней{title_suffix}',
        'all': f'Вес за всё время{title_suffix}'
    }
    title = titles[period]

    plot_data = resampled_data if resampled_data is not None else last_records
    

    plt.figure(figsize=(10, 5))
    plt.plot(plot_data['date'], plot_data['weight'], 'o-r', label='Вес')
    plt.axhline(y=avg_weight, color='gray', linestyle='--', label=f'Средний вес: {avg_weight} кг')
    plt.xlabel('Дата')
    plt.ylabel('Вес (кг)')
    plt.title(title)
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    plt.savefig('plot.png')
    plt.close()