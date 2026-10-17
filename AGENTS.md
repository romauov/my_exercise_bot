# AGENTS.md

## Project Overview
Telegram-bot for exercise reminders using aiogram 3.x. Sends scheduled workouts hourly and tracks weight.

## Run
```bash
python -m bot
```
Requires `.env` with `tg_token` and `my_tg_id` (+ `WEB_TOKEN` for the web service).

## Run web
```bash
uvicorn web.main:app --host 0.0.0.0 --port 8080
```

## Tests
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest app/tests
```

## Docker
```bash
docker-compose up --build
```
Data persists in `./data` volume.

## Architecture
- **Entry point**: `bot.py` — creates `Bot`, `Dispatcher`, includes routers, starts `AsyncIOScheduler` (runs `init_db()` + JSON migration at start)
- **Web service**: `web/main.py` — FastAPI (token auth via `WEB_TOKEN`), charts UI in `web/static/`; runs with `uvicorn web.main:app` (also as the `web` service in docker-compose)
- **Routers**: only `weight_router` and `street_workout_router` are included in `main_handlers.py`; `workout_handlers` and `workout_selection_handlers` are **defined but not wired in** (commented out)
- **FSM**: heavy use of `StatesGroup` for multi-step inline-keyboard input (weight, street workout, workout CRUD, workout selection)
- **Scheduler**: `schedule_random_quotes` is active (2-5 random quotes between 10:00-22:00); `set_schedule` (hourly exercises from `schedule.json`) is commented out in `bot.py`
- **Data**: weight data now lives in SQLite (`data/app.db`, WAL) shared by the bot and the web service; `app/db.py` owns it, one-time JSON import migrates `data/*_weights.json` at first start (file stays as backup). Other domains (pullups/pushups, workout cards) still JSON in `data/`. User-specific JSON files (`{user_id}_weights.json` etc.) are gitignored; `weight_cards.json` is also gitignored (but the code reads it from `data/`)

## Key Files
- `bot.py` — entry point
- `app/settings.py` — env loading via `pydantic-settings`
- `app/handlers/` — command handlers split by domain
- `app/utils.py` — scheduler setup, weight save
- `app/workout_utils.py` — CRUD for workout cards
- `app/keyboard_utils.py` — Reply/Inline keyboard builders
- `app/response_formatters.py` — message formatting
- `app/draw_weight_plot.py` / `app/draw_street_workout_plot.py` — matplotlib plotting

## Commands
- `/kettlebell` — random workout by difficulty (morning/easy/medium/hard) with Done/Another flow
- `/weight` — add weight via inline keyboard → auto-plot 14-day chart
- `/weight_` — plot weight chart for period (last/month/quarter/year/all)
- `/weight_save` — export weight JSON
- `/street_wo` — log pullups/pushups sets via inline keyboard → auto-plot
- `/add_workout`, `/remove_workout`, `/list_workout`, `/save_workout` — workout CRUD

## No test/lint/typecheck configured.
