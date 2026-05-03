# AGENTS.md

## Project Overview
Telegram-bot for exercise reminders using aiogram 3.x. Sends scheduled workouts hourly and tracks weight.

## Run
```bash
python -m bot
```
Requires `.env` with `tg_token` and `my_tg_id`.

## Docker
```bash
docker-compose up --build
```

## Code Structure
- `bot.py` - Entry point
- `app/handlers/` - Command handlers (main, workout, weight, workout_selection, street_workout)
- `app/draw_weight_plot.py` - Weight plotting with matplotlib
- `app/draw_street_workout_plot.py` - Street workout plotting
- `app/workout_utils.py` - Workout logic
- JSON data files in `data/`: `{user_id}_weights.json`, `{user_id}_pullups.json`, `{user_id}_pushups.json`, `workout_cards.json`
- JSON config: `exercises_list.json`, `face_exercises.json`, `schedule.json`

## No test/lint/typecheck configured.