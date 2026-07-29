# HouseTasks

A shared chore board for a household, where adding something takes **one line of
plain language** — and chores that repeat actually repeat.

```
take out the trash tomorrow every week @Maria !high
```

becomes a task due tomorrow, assigned to Maria, high priority, repeating weekly.
No date picker, no dropdowns, no six-field form. That is the whole point: a chore
list nobody wants to fill in is a chore list nobody fills in.

Dark, responsive, works on a phone, prints as a fridge sheet, speaks **English and
Brazilian Portuguese**, and runs on a Raspberry Pi. One Python process, one SQLite
file, **no build step and no front-end framework**.

---

## What it does

**One-line quick add.** Type it the way you'd say it. The date, the person, the
priority and the repeat schedule are picked out of the sentence.

**It shows you what it understood, as you type.** Chips appear under the box —
`Clean the bathroom` · `Saturday` · `every week` · `Ana` · `High` — so you never
find out tomorrow that it guessed wrong. That preview calls the *same parser that
saves the task*; a second copy of the rules in JavaScript would drift, and then
the preview would be a polite lie.

**Recurring chores that behave.** Ticking a repeating chore doesn't close it — it
rolls to its next date. Missed runs are skipped rather than piling up, and the
weekday anchor holds: a weekly Monday chore you forgot twice is due **next
Monday**, not twice more this week.

**A day that reads at a glance.** A progress ring for today, a headline that
changes with your situation — *"2 things left today"* → *"1 of them is already
late"* → *"All clear"* — plus a streak counter and a weekly total.

**Buckets, not a wall.** Late · Today · Tomorrow · This week · Later · Someday.

**People.** Assign with `@name`, filter by person, everyone gets a stable colour
derived from their name.

**Instant ticking.** Rows animate out and the ring fills without a page reload —
and clearing the day sets off some confetti, because finishing should feel like
something.

**Exact undo.** Every completion is logged with the date the task came from, so
undoing a rolled-forward chore puts it back on *its* date, not an approximation.

---

## Quick-add syntax

Everything is optional. Anything not recognised stays in the title.

| You type | It means |
| --- | --- |
| `@maria` | assign to Maria |
| `!high` · `!!` · `!low` | priority |
| `today` · `tomorrow` | due date |
| `friday`, `on monday` | the coming Friday/Monday |
| `in 3 days` | three days out |
| `aug 12` · `2026-08-12` | a specific date |
| `every day` · `weekdays` | daily / Mon–Fri |
| `every week` · `every monday` | weekly, anchored to that day |
| `every other week` | fortnightly |
| `every month` | monthly, clamped to short months |
| `every 3 days` | any interval you like |

**Portuguese works too, accents optional** — nobody reaches for the accent key on
a phone:

| Você escreve | Significa |
| --- | --- |
| `hoje` · `amanha` · `amanhã` | hoje / amanhã |
| `sexta` · `todo sabado` | sexta-feira / todo sábado |
| `em 3 dias` · `12 de agosto` | data |
| `todo dia` · `toda semana` · `todo mês` | frequência |
| `a cada 3 dias` · `a cada 2 semanas` | intervalo |
| `!alta` · `!baixa` | prioridade |

A date that has already passed this year is read as next year, so `taxes apr 30`
typed in July means next April.

---

## Run it

Needs Python 3.10+.

```bash
git clone https://github.com/luccahp1/housetasks.git
cd housetasks
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. That's it — the database creates itself on first
run.

| Environment variable | Default | What it does |
| --- | --- | --- |
| `HOUSETASKS_DB` | `housetasks.db` | where the SQLite file lives |

To keep it running on a home server, point a systemd unit at that same uvicorn
command. There is no login and no user accounts — it is built for a household on
one LAN, so **don't expose it to the open internet**.

---

## Tests

```bash
pip install pytest
pytest -q
```

33 tests covering the parser in both languages, the recurrence rules, and the
complete → roll-forward → undo round trip.

---

## How it works

```
app/
  main.py      routes; every action is a form post + 303 redirect
  tasks.py     the parser, the recurrence rules, and the board's read models
  db.py        SQLite schema and query helpers
  i18n.py      EN/PT-BR strings and the two date orders
  web.py       Jinja environment and the render helper
  templates/   base.html · tasks.html · _icons.html (inline SVG macro)
  static/      one stylesheet
```

Two tables. `tasks` is the open list; `task_log` records every completion —
including for repeating chores, which never reach a "done" state — and carries
`prev_due` so undo is exact. Streaks are counted from the log.

**JavaScript is enhancement, never a dependency.** It makes ticking instant and
powers the live preview, but every button is a real `<form>`. Turn JavaScript off
and the entire app still works, just with a page reload per action.

---

## Notes from building it

A few decisions that took more than one attempt, in case they're useful to you:

- **Missed recurrences are skipped, not queued.** The alternative — a chore that
  reappears once for every occurrence you missed — turns a two-week holiday into
  a wall of guilt, and nobody re-mops a floor four times.
- **One parser, on the server.** The live preview is a `fetch` to the same
  endpoint logic that saves, so there is exactly one definition of what
  `every other week` means.
- **A CSS class that sets `display` beats the browser's `[hidden]` rule.**
  Anything toggled with the `hidden` attribute needs its own `[hidden]` rule, or
  it is never actually hidden.
- **`requestAnimationFrame` doesn't fire in a tab that isn't compositing.** The
  progress ring animated from a timer instead, so it reaches its correct value in
  a background tab rather than sitting on empty.
- **Recurring tasks don't need an "undo" button of their own.** Storing the date
  a chore came from turned undo into one row lookup and removed a whole category
  of edge case.

---

## License

MIT — see [LICENSE](LICENSE).
