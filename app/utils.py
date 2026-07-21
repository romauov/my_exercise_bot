import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Bot
from apscheduler.triggers.cron import CronTrigger
from openai import AsyncOpenAI
from app.draw_weight_plot import draw_plot
from app.settings import secrets as s

TZ = ZoneInfo("Europe/Samara")

_client = None
def get_client():
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=s.openrouter_api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/romauov/my_exercise_bot",
            },
        )
    return _client


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

     
def save_weight_json(user_id, weight, date):
    data = {
        "weight": weight,
        "date": date
    }
    try:
        with open(f'data/{user_id}_weights.json', 'r') as file:
            weights = json.load(file)
    except FileNotFoundError:
        weights = []
    
    weights = [w for w in weights if w.get('date') != date]
    weights.append(data)

    with open(f'data/{user_id}_weights.json', 'w') as file:
        json.dump(weights, file, indent=4)
    draw_plot(user_id=user_id)


def get_quotes():
    with open('data/quotes.json') as f:
        return json.load(f)


async def generate_quote():
    quotes = get_quotes()
    examples = "\n".join(f"- {q}" for q in quotes)
    prompt = (
        "Сгенерируй короткую мотивирующую цитату (1-2 предложения) "
        "про спорт, тренировки, здоровье, похожую по стилю на эти примеры:\n"
        f"{examples}\n\n"
        "Только текст цитаты, без кавычек и пояснений."
    )
    messages = [{"role": "user", "content": prompt}]

    for model in ["google/gemini-2.0-flash-001", "openai/gpt-4o-mini"]:
        try:
            response = await get_client().chat.completions.create(
                model=model,
                messages=messages,
                temperature=2.0,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            continue
    return "💪 Нет мотивации, но тренировка всё равно будет!"


async def send_random_quote(bot: Bot):
    quote = await generate_quote()
    await bot.send_message(chat_id=s.my_tg_id, text=quote)


def schedule_random_quotes(scheduler, bot):
    def schedule_next_day_jobs():
        for job in scheduler.get_jobs():
            if job.id.startswith("quote_job_"):
                job.remove()

        messages_count = random.randint(2, 5)

        now = datetime.now(TZ)
        start_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=22, minute=0, second=0, microsecond=0)

        for i in range(messages_count):
            delta_seconds = random.randint(0, int((end_time - start_time).total_seconds()))
            run_date = start_time + timedelta(seconds=delta_seconds)

            if run_date > now:
                scheduler.add_job(
                    send_random_quote,
                    'date',
                    run_date=run_date,
                    id=f"quote_job_{i}",
                    kwargs={'bot': bot}
                )

    schedule_next_day_jobs()

    scheduler.add_job(schedule_next_day_jobs, 'cron', hour=0, minute=1, timezone=TZ)
