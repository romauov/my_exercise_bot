import json
import random
from datetime import datetime
from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from app.draw_plot import draw_plot
from app.settings import secrets as s


def pick_exercises(path):
    with open(path) as f:
        exercises = json.load(f)
    return random.choice(exercises)

def get_full_schedule(schedule, timeshift):
    full_schedule = {}
    for day in schedule:
        hours = [i - timeshift + 24 if i - timeshift < 0 else i - timeshift for i in range(schedule[day][0], schedule[day][1] + 1)]
        full_schedule[day] = hours
    return full_schedule

async def send_scheduled_message(bot: Bot):
    chat_id = s.my_tg_id
    await bot.send_message(chat_id=chat_id, text="Делай " + pick_exercises('exercises_list.json') + " и " + pick_exercises('face_exercises.json'))
    
def set_schedule(scheduler, bot):
    
    with open('schedule.json') as f:
        schedule = json.load(f)
        
    full_schedule = get_full_schedule(schedule, timeshift=4)
    
    for day in full_schedule:
        for hour in full_schedule[day]:
            scheduler.add_job(send_scheduled_message, 
                              CronTrigger(day_of_week=day, hour=hour, minute=00, start_date=datetime.now()), 
                              kwargs={'bot': bot})

    scheduler.start()

     
def save_weight_json(user_id, weight, date):
    data = {
        "weight": weight,
        "date": date
    }
    try:
        with open(f'{user_id}_weights.json', 'r') as file:
            weights = json.load(file)
    except FileNotFoundError:
        weights = []

    weights.append(data)

    with open(f'{user_id}_weights.json', 'w') as file:
        json.dump(weights, file, indent=4)
    draw_plot(user_id=user_id)
