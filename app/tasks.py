"""House tasks: one-line quick add, recurring chores, and the page's read models.

A chore list only gets used if adding something takes one line, so the whole
task — what, who, when, how often, how urgent — is typed in plain language
("take out the trash tomorrow every week @Maria !high") and pulled apart here.
The page previews what it understood by asking this same parser over fetch, so
there is never a second implementation drifting out of sync in JavaScript.
"""

import re
from calendar import monthrange
from datetime import date, datetime, timedelta

from app import db

PRIORITIES = ("low", "normal", "high")
REPEAT_OPTIONS = ("", "daily", "weekdays", "weekly", "biweekly", "monthly")

# Hues (not hex) so one number drives both the tint and the text colour of a
# person's avatar chip. Stable per name: the same person is always the same hue.
_HUES = (232, 158, 38, 330, 265, 190)

_WEEKDAYS = {
    "monday": 0, "mon": 0, "segunda": 0, "segunda-feira": 0, "seg": 0,
    "tuesday": 1, "tue": 1, "tues": 1, "terca": 1, "terça": 1, "ter": 1,
    "terca-feira": 1, "terça-feira": 1,
    "wednesday": 2, "wed": 2, "quarta": 2, "quarta-feira": 2, "qua": 2,
    "thursday": 3, "thu": 3, "thurs": 3, "quinta": 3, "quinta-feira": 3, "qui": 3,
    "friday": 4, "fri": 4, "sexta": 4, "sexta-feira": 4, "sex": 4,
    "saturday": 5, "sat": 5, "sabado": 5, "sábado": 5, "sab": 5,
    "sunday": 6, "sun": 6, "domingo": 6, "dom": 6,
}
_MONTHS = {
    "jan": 1, "january": 1, "janeiro": 1,
    "feb": 2, "february": 2, "fev": 2, "fevereiro": 2,
    "mar": 3, "march": 3, "marco": 3, "março": 3,
    "apr": 4, "april": 4, "abr": 4, "abril": 4,
    "may": 5, "mai": 5, "maio": 5,
    "jun": 6, "june": 6, "junho": 6,
    "jul": 7, "july": 7, "julho": 7,
    "aug": 8, "august": 8, "ago": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "set": 9, "setembro": 9,
    "oct": 10, "october": 10, "out": 10, "outubro": 10,
    "nov": 11, "november": 11, "novembro": 11,
    "dec": 12, "december": 12, "dez": 12, "dezembro": 12,
}
_WEEKDAY_RE = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

# Longest phrasings first: "every 2 weeks" and "every other week" both contain
# "every week", so they have to win the race.
_REPEAT_PATTERNS = [
    (r"\b(?:every|a cada) (\d+) (?:days?|dias?)\b", lambda m: f"every:{m.group(1)}"),
    (r"\b(?:every|a cada) (\d+) (?:weeks?|semanas?)\b",
     lambda m: f"every:{int(m.group(1)) * 7}"),
    (r"\b(?:every other week|biweekly|fortnightly|quinzenal(?:mente)?)\b",
     lambda m: "biweekly"),
    (r"\b(?:weekdays|every weekday|dias [úu]teis)\b", lambda m: "weekdays"),
    (r"\b(?:every ?day|daily|todo dia|diariamente|di[áa]rio)\b", lambda m: "daily"),
    (r"\b(?:every week|weekly|toda semana|semanal(?:mente)?)\b", lambda m: "weekly"),
    (r"\b(?:every month|monthly|todo m[êe]s|mensal(?:mente)?)\b", lambda m: "monthly"),
]


# ---------- quick-add parsing ----------

def _cut(text, pattern):
    """Lift the first match out of the line; return the remainder and the match."""
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return text, None
    return text[:match.start()] + " " + text[match.end():], match


def _next_weekday(today, weekday):
    """The coming Friday — and if today is Friday, today."""
    return today + timedelta(days=(weekday - today.weekday()) % 7)


def _clean_title(text):
    title = re.sub(r"\s+", " ", text).strip(" -–—,;:.")
    return title[:1].upper() + title[1:] if title else ""


def _parse_repeat(text, today):
    """Pull a recurrence out of the line, plus the day it should anchor to."""
    # "every monday" both repeats weekly and pins the first occurrence.
    text, match = _cut(text, rf"\b(?:every|toda|todo|todas as|todos os) ({_WEEKDAY_RE})\b")
    if match:
        return text, "weekly", _next_weekday(today, _WEEKDAYS[match.group(1).lower()])
    for pattern, build in _REPEAT_PATTERNS:
        text, match = _cut(text, pattern)
        if match:
            return text, build(match), None
    return text, "", None


def _parse_due(text, today):
    """Pull a date out of the line. Bare month/day in the past means next year."""
    text, match = _cut(text, r"\b(today|hoje)\b")
    if match:
        return text, today
    text, match = _cut(text, r"\b(tomorrow|amanh[ãa])\b")
    if match:
        return text, today + timedelta(days=1)
    text, match = _cut(text, r"\b(?:in|em) (\d+) (?:days?|dias?)\b")
    if match:
        return text, today + timedelta(days=int(match.group(1)))
    text, match = _cut(text, r"\b(\d{4}-\d{2}-\d{2})\b")
    if match:
        try:
            return text, date.fromisoformat(match.group(1))
        except ValueError:
            return text, None
    text, match = _cut(text, rf"\b({_MONTH_RE})\.? (\d{{1,2}})\b")   # "Aug 12"
    if match:
        return text, _calendar_date(today, _MONTHS[match.group(1).lower()],
                                    int(match.group(2)))
    text, match = _cut(text, rf"\b(\d{{1,2}})(?: de)? ({_MONTH_RE})\b")  # "12 de agosto"
    if match:
        return text, _calendar_date(today, _MONTHS[match.group(2).lower()],
                                    int(match.group(1)))
    text, match = _cut(text, rf"\b(?:on|next|na|no|pr[óo]xima?) ({_WEEKDAY_RE})\b")
    if not match:
        text, match = _cut(text, rf"\b({_WEEKDAY_RE})\b")
    if match:
        return text, _next_weekday(today, _WEEKDAYS[match.group(1).lower()])
    return text, None


def _calendar_date(today, month, day):
    day = min(day, monthrange(today.year, month)[1])
    guess = date(today.year, month, day)
    return guess if guess >= today else date(today.year + 1, month, day)


def parse(text, today=None):
    """Turn one typed line into task fields, or None if no title survives."""
    today = today or date.today()
    line = f" {text.strip()} "

    line, match = _cut(line, r"@([\w'-]+)")
    assignee = match.group(1).strip("-'").title() if match else ""

    line, match = _cut(line, r"!(high|alta|urgent|urgente|low|baixa|!)")
    priority = "normal"
    if match:
        priority = "low" if match.group(1).lower() in ("low", "baixa") else "high"

    line, repeat_rule, anchor = _parse_repeat(line, today)
    line, due = _parse_due(line, today)
    if repeat_rule and due is None:
        # A chore that repeats has to start somewhere; today is the fair guess.
        due = anchor or today

    title = _clean_title(line)
    if not title:
        return None
    return {"title": title, "assignee": assignee, "priority": priority,
            "repeat_rule": repeat_rule,
            "due": due.isoformat() if due else None}


# ---------- recurrence ----------

def _add_month(day):
    year, month = day.year + day.month // 12, day.month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def next_due(due, rule, today):
    """Where a finished chore lands next.

    Missed occurrences are skipped rather than piled up — a weekly bin run you
    forgot twice is due next Tuesday, not twice more this week — and the anchor
    weekday survives, so "every Monday" stays on Mondays.
    """
    day = due or today
    fixed_step = {"daily": 1, "weekly": 7, "biweekly": 14}.get(rule)
    if rule.startswith("every:"):
        fixed_step = max(1, int(rule.split(":", 1)[1]))
    if fixed_step:
        behind = (today - day).days
        jumps = (behind // fixed_step) + 1 if behind >= 0 else 1
        return day + timedelta(days=jumps * fixed_step)
    while day <= today:
        if rule == "monthly":
            day = _add_month(day)
        elif rule == "weekdays":
            day += timedelta(days=1)
            while day.weekday() >= 5:
                day += timedelta(days=1)
        else:
            return today
    return day


# ---------- writes ----------

def add(text, today=None):
    fields = parse(text, today)
    if not fields:
        return None
    return db.execute(
        "INSERT INTO tasks (title, assignee, due, priority, repeat_rule, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (fields["title"], fields["assignee"], fields["due"], fields["priority"],
         fields["repeat_rule"], datetime.now().isoformat(timespec="seconds")))


def complete(task_id):
    """Tick a task off. Returns the date a repeating chore came back on, if any.

    A repeating chore never reaches a 'done' state — it rolls forward to its
    next date — so the log row remembers where it came from and undo can put it
    back exactly.
    """
    task = db.query_one("SELECT * FROM tasks WHERE id = ? AND done = 0", (task_id,))
    if not task:
        return None
    now = datetime.now()
    db.execute(
        "INSERT INTO task_log (task_id, title, assignee, prev_due, done_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (task_id, task["title"], task["assignee"], task["due"],
         now.isoformat(timespec="seconds")))
    if task["repeat_rule"]:
        rolled = next_due(
            date.fromisoformat(task["due"]) if task["due"] else None,
            task["repeat_rule"], now.date())
        db.execute("UPDATE tasks SET due = ? WHERE id = ?",
                   (rolled.isoformat(), task_id))
        return rolled.isoformat()
    db.execute("UPDATE tasks SET done = 1, done_at = ? WHERE id = ?",
               (now.isoformat(timespec="seconds"), task_id))
    return None


def undo(log_id):
    entry = db.query_one("SELECT * FROM task_log WHERE id = ?", (log_id,))
    if not entry:
        return
    db.execute("DELETE FROM task_log WHERE id = ?", (log_id,))
    db.execute("UPDATE tasks SET done = 0, done_at = NULL, due = ? WHERE id = ?",
               (entry["prev_due"], entry["task_id"]))


def update(task_id, title, assignee, due, priority, repeat_rule):
    db.execute(
        "UPDATE tasks SET title = ?, assignee = ?, due = ?, priority = ?,"
        " repeat_rule = ? WHERE id = ?",
        (title.strip(), assignee.strip().title(), due or None,
         priority if priority in PRIORITIES else "normal",
         repeat_rule if repeat_rule in REPEAT_OPTIONS else "", task_id))


def delete(task_id):
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def clear_done():
    db.execute("DELETE FROM tasks WHERE done = 1")


# ---------- read models ----------

def initials(name):
    parts = [p for p in re.split(r"[\s-]+", name) if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def hue(name):
    return _HUES[sum(name.lower().encode()) % len(_HUES)]


def _decorate(row, today):
    """Everything the template needs to draw one row, worked out once here."""
    task = dict(row)
    due = date.fromisoformat(task["due"]) if task["due"] else None
    days = (due - today).days if due else None
    task["days"] = days
    task["initials"] = initials(task["assignee"]) if task["assignee"] else ""
    task["hue"] = hue(task["assignee"]) if task["assignee"] else 0
    if task["repeat_rule"].startswith("every:"):
        task["repeat_key"] = "t_rep_every"
        task["repeat_n"] = task["repeat_rule"].split(":", 1)[1]
    else:
        task["repeat_key"] = f"t_rep_{task['repeat_rule']}" if task["repeat_rule"] else ""
        task["repeat_n"] = ""

    if days is None:
        task["bucket"], task["when_key"] = "someday", ""
    elif days < 0:
        task["bucket"] = "overdue"
        task["when_key"] = "t_late_one" if days == -1 else "t_late"
        task["when_n"] = str(-days)
    elif days == 0:
        task["bucket"], task["when_key"] = "today", "t_due_today"
    elif days == 1:
        task["bucket"], task["when_key"] = "tomorrow", "t_due_tomorrow"
    elif days <= 7:
        task["bucket"], task["when_key"] = "week", ""
    else:
        task["bucket"], task["when_key"] = "later", ""
    return task


BUCKETS = ("overdue", "today", "tomorrow", "week", "later", "someday")


def board(person=""):
    """Open tasks bucketed the way a person actually reads their day."""
    today = date.today()
    where = " AND assignee = ?" if person else ""
    rows = db.query(
        f"SELECT * FROM tasks WHERE done = 0{where}"
        " ORDER BY (due IS NULL), due,"
        " CASE priority WHEN 'high' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END, id",
        (person,) if person else ())
    grouped = {key: [] for key in BUCKETS}
    for row in rows:
        task = _decorate(row, today)
        grouped[task["bucket"]].append(task)
    return [{"key": key, "tasks": grouped[key]} for key in BUCKETS if grouped[key]]


def done_today(person=""):
    where = " AND assignee = ?" if person else ""
    return db.query(
        f"SELECT * FROM task_log WHERE substr(done_at, 1, 10) = ?{where}"
        " ORDER BY done_at DESC",
        (date.today().isoformat(), person) if person else (date.today().isoformat(),))


def people():
    """Whoever currently has something on their plate, busiest first."""
    rows = db.query(
        "SELECT assignee, COUNT(*) AS n FROM tasks WHERE done = 0 AND assignee <> ''"
        " GROUP BY assignee ORDER BY n DESC, assignee")
    return [{"name": r["assignee"], "n": r["n"], "initials": initials(r["assignee"]),
             "hue": hue(r["assignee"])} for r in rows]


def _streak():
    """Consecutive days finishing something, counted back from today.

    Yesterday still counts as alive — the streak only breaks once a whole day
    passes with nothing done, so an early-morning look doesn't show a zero.
    """
    days = [r["d"] for r in db.query(
        "SELECT DISTINCT substr(done_at, 1, 10) AS d FROM task_log"
        " ORDER BY d DESC LIMIT 400")]
    if not days:
        return 0
    cursor = date.today()
    if date.fromisoformat(days[0]) < cursor - timedelta(days=1):
        return 0
    if date.fromisoformat(days[0]) < cursor:
        cursor -= timedelta(days=1)
    run = 0
    for day in days:
        if date.fromisoformat(day) != cursor:
            break
        run += 1
        cursor -= timedelta(days=1)
    return run


def summary(person=""):
    """The numbers behind the progress ring and the headline."""
    today = date.today().isoformat()
    where = " AND assignee = ?" if person else ""
    params = (today, person) if person else (today,)
    left = db.query_one(
        f"SELECT COUNT(*) AS c FROM tasks WHERE done = 0 AND due IS NOT NULL"
        f" AND due <= ?{where}", params)["c"]
    overdue = db.query_one(
        f"SELECT COUNT(*) AS c FROM tasks WHERE done = 0 AND due IS NOT NULL"
        f" AND due < ?{where}", params)["c"]
    finished = db.query_one(
        f"SELECT COUNT(*) AS c FROM task_log WHERE substr(done_at, 1, 10) = ?{where}",
        params)["c"]
    total = left + finished
    since = (date.today() - timedelta(days=6)).isoformat()
    week_done = db.query_one(
        f"SELECT COUNT(*) AS c FROM task_log WHERE substr(done_at, 1, 10) >= ?{where}",
        (since, person) if person else (since,))["c"]
    return {"left": left, "overdue": overdue, "done_today": finished,
            "today_total": total, "week_done": week_done, "streak": _streak(),
            "pct": round(finished / total * 100) if total else 100}


def due_today_count():
    """Open tasks that are due now or already late — the number for the tile."""
    return db.query_one(
        "SELECT COUNT(*) AS c FROM tasks WHERE done = 0 AND due IS NOT NULL"
        " AND due <= ?", (date.today().isoformat(),))["c"]
