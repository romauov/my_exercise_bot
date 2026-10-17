import json
import random
from datetime import datetime
from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from app.draw_weight_plot import draw_plot
from app.settings import secrets as s
from app.db import upsert_weight, normalize_date


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
    await bot.send_message(chat_id=chat_id, 
                        #    text="Делай " + pick_exercises('data/exercises_list.json') + " и " + pick_exercises('data/face_exercises.json')
                        text=pick_exercises('data/face_exercises.json'))
    
def set_schedule(scheduler, bot):
    
    with open('data/schedule.json') as f:
        schedule = json.load(f)
        
    full_schedule = get_full_schedule(schedule, timeshift=4)
    
    for day in full_schedule:
        for hour in full_schedule[day]:
            scheduler.add_job(send_scheduled_message, 
                              CronTrigger(day_of_week=day, hour=hour, minute=00, start_date=datetime.now()), 
                              kwargs={'bot': bot})

    scheduler.start()

     
def save_weight_db(weight, date_ddmmyyyy):
    """Store one weighing (bot date format DD-MM-YYYY) and redraw the plot."""
    upsert_weight(normalize_date(date_ddmmyyyy), float(weight))
    draw_plot()
