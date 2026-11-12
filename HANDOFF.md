# Handoff

_Last updated: 2026-11-12_

## What this is

A shared household chore board. Tasks are added in one line of plain language
(`take out the trash tomorrow every week @Maria !high`) and parsed into a title,
due date, assignee, priority and repeat rule. FastAPI, Jinja templates, SQLite,
no front-end framework, English and Brazilian Portuguese.

It is the standalone version of the Tasks page in HomeDash. `app/tasks.py` is the
same code in both repos; a fix to the parser or the recurrence rules belongs in
both.

## Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
python -m pytest -q
```

`HOUSETASKS_DB` picks the SQLite file (default `housetasks.db`). No login: LAN
use only.

## State

- 44 tests pass (parser, recurrence, writes, buckets, people, streak).
- Not deployed anywhere.
- 2026-11-12: removed `clear_done` and `due_today_count` (unused here and in HomeDash; both copies of `app/tasks.py` still match).
- 2026-10-15: picked up the fixes made in HomeDash the same day. Editing an
  "every N days" chore no longer drops its repeat, a monthly or weekdays chore
  ticked before its date moves on, "feb 29" typed after a leap February no longer
  crashes, and word-like abbreviations ("take out 2 bags", "clean the sun room")
  stay in the title instead of becoming dates.

## Open

- Whether this is still wanted alongside the HomeDash Tasks page is Lucca's call.
- Monthly repeats anchored on the 29th to 31st drift to the 28th after February.
