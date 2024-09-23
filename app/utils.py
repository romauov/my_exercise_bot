import json
import random
from datetime import datetime
from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from app.settings import secrets as s


def pick_exercises():
    with open('exercises_list.json') as f:
        exercises = json.load(f)
    return random.choice(exercises)

def get_full_schedule(schedule):
    full_schedule = {}
    for day in schedule:
        hours = [i for i in range(schedule[day][0], schedule[day][1] + 1)]
        full_schedule[day] = hours
    return full_schedule

async def send_scheduled_message(bot: Bot):
    chat_id = s.my_tg_id
    await bot.send_message(chat_id=chat_id, text="Делай " + pick_exercises())
    
def set_schedule(scheduler, bot):
    
    with open('schedule.json') as f:
        schedule = json.load(f)
        
    full_schedule = get_full_schedule(schedule)
    
    for day in full_schedule:
        for hour in full_schedule[day]:
            scheduler.add_job(send_scheduled_message, CronTrigger(day_of_week=day, hour=hour, minute=00, start_date=datetime.now()), kwargs={'bot': bot})

    scheduler.start()
