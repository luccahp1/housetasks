# HouseTasks

Shared chore board for a household where adding a chore takes one line of plain language, and repeats actually repeat.

**Stack:** python, fastapi · **Repo:** luccahp1/housetasks · **Status:** paused

## Run

```
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000   # HOUSETASKS_DB picks the SQLite file
python -m pytest -q                                # 44 tests
```

## Project memory (required)
This project's memory lives in `.assistant/`. Read `goal.md` and `state.md` before starting work.
Before you finish work that changed files, update:
- `state.md`: the new current state
- `issues.md`: add new issues; move fixed ones to Fixed with today's date
- `roadmap.md`: check off completed items, add new ones
- `history.md`: one dated line describing what changed
Keep entries short. These files are how the Assistant knows what's going on.
