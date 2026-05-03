import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json


def draw_street_workout_plot(user_id, exercise):
    if exercise == 'pullups':
        file_path = f'data/{user_id}_pullups.json'
        title = 'Подтягивания на турнике'
    else:
        file_path = f'data/{user_id}_pushups.json'
        title = 'Отжимания на брусьях'

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        return f'Нет данных для {exercise}'

    if not data:
        return f'Нет данных для {exercise}'

    dates = []
    sets_counts = []
    avgs = []
    totals = []

    sorted_data = sorted(data, key=lambda x: pd.to_datetime(x['date'], dayfirst=True), reverse=True)[:14]
    sorted_data = sorted_data[::-1]

    for entry in sorted_data:
        dates.append(entry['date'][-5:])
        sets = entry['sets']
        sets_counts.append(len(sets))
        avgs.append(round(sum(sets) / len(sets), 2))
        totals.append(sum(sets))

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(dates))

    ax.plot(x, sets_counts, 'o-', label='Подходы', color='blue', linewidth=2, markersize=6)
    ax.plot(x, avgs, 's-', label='Среднее за подход', color='green', linewidth=2, markersize=6)
    ax.plot(x, totals, '^-', label='Общее кол-во', color='red', linewidth=2, markersize=6)

    ax.set_xlabel('Дата')
    ax.set_ylabel('Кол-во')
    ax.set_title(f'{title} за последние {len(dates)} дней')
    ax.set_xticks(x)
    ax.set_xticklabels(dates, rotation=45)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    
    if exercise == 'pullups':
        plt.savefig('data/street_workout_pullups.png')
    else:
        plt.savefig('data/street_workout_pushups.png')
    
    plt.close()

    return None


def draw_all_street_workout_plots(user_id):
    errors = []
    
    error = draw_street_workout_plot(user_id, 'pullups')
    if error:
        errors.append(error)
    
    error = draw_street_workout_plot(user_id, 'pushups')
    if error:
        errors.append(error)
    
    if errors:
        return ', '.join(errors)
    return None