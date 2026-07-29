"""The parser and the recurrence rules — the two places a bug would be silent.

Dates are pinned to Monday 2026-07-27 so weekday arithmetic is easy to read.
"""

from datetime import date

import pytest

from app import tasks

MONDAY = date(2026, 7, 27)


# ---------- quick-add parsing ----------

@pytest.mark.parametrize("line, expected", [
    ("take out the trash tomorrow every week @Maria !high",
     {"title": "Take out the trash", "assignee": "Maria", "priority": "high",
      "repeat_rule": "weekly", "due": "2026-07-28"}),
    ("water the plants every 3 days",
     {"title": "Water the plants", "assignee": "", "priority": "normal",
      "repeat_rule": "every:3", "due": "2026-07-27"}),
    ("pay the condo fee every month !!",
     {"title": "Pay the condo fee", "assignee": "", "priority": "high",
      "repeat_rule": "monthly", "due": "2026-07-27"}),
    ("call the landlord friday",
     {"title": "Call the landlord", "assignee": "", "priority": "normal",
      "repeat_rule": "", "due": "2026-07-31"}),
    ("vacuum the living room",
     {"title": "Vacuum the living room", "assignee": "", "priority": "normal",
      "repeat_rule": "", "due": None}),
    ("clean the filter every other week @Ana-Maria",
     {"title": "Clean the filter", "assignee": "Ana-Maria", "priority": "normal",
      "repeat_rule": "biweekly", "due": "2026-07-27"}),
    ("check the mail weekdays",
     {"title": "Check the mail", "assignee": "", "priority": "normal",
      "repeat_rule": "weekdays", "due": "2026-07-27"}),
    ("renew insurance 2026-09-01 !low",
     {"title": "Renew insurance", "assignee": "", "priority": "low",
      "repeat_rule": "", "due": "2026-09-01"}),
    ("dentist aug 12",
     {"title": "Dentist", "assignee": "", "priority": "normal",
      "repeat_rule": "", "due": "2026-08-12"}),
    ("in 10 days rotate the mattress",
     {"title": "Rotate the mattress", "assignee": "", "priority": "normal",
      "repeat_rule": "", "due": "2026-08-06"}),
])
def test_parses_english(line, expected):
    assert tasks.parse(line, MONDAY) == expected


@pytest.mark.parametrize("line, expected", [
    # accents optional — nobody reaches for the accent key on a phone
    ("levar o lixo amanha toda semana @Maria",
     {"title": "Levar o lixo", "assignee": "Maria", "priority": "normal",
      "repeat_rule": "weekly", "due": "2026-07-28"}),
    ("regar as plantas a cada 3 dias",
     {"title": "Regar as plantas", "assignee": "", "priority": "normal",
      "repeat_rule": "every:3", "due": "2026-07-27"}),
    ("limpar o banheiro todo sabado !alta",
     {"title": "Limpar o banheiro", "assignee": "", "priority": "high",
      "repeat_rule": "weekly", "due": "2026-08-01"}),
    # Portuguese writes the day before the month
    ("12 de agosto marcar dentista",
     {"title": "Marcar dentista", "assignee": "", "priority": "normal",
      "repeat_rule": "", "due": "2026-08-12"}),
])
def test_parses_portuguese(line, expected):
    assert tasks.parse(line, MONDAY) == expected


@pytest.mark.parametrize("line", ["", "   ", "@Maria", "!high", "tomorrow"])
def test_rejects_lines_with_no_title(line):
    assert tasks.parse(line, MONDAY) is None


def test_a_date_already_past_means_next_year():
    assert tasks.parse("taxes apr 30", MONDAY)["due"] == "2027-04-30"


# ---------- recurrence ----------

def test_weekly_keeps_its_weekday_and_skips_missed_runs():
    # two weeks late on a Monday chore: next Monday, not two more this week
    assert tasks.next_due(date(2026, 7, 13), "weekly", MONDAY) == date(2026, 8, 3)


def test_due_today_rolls_a_full_period_forward():
    assert tasks.next_due(MONDAY, "weekly", MONDAY) == date(2026, 8, 3)


def test_weekdays_skips_the_weekend():
    friday = date(2026, 7, 24)
    assert tasks.next_due(friday, "weekdays", MONDAY) == date(2026, 7, 28)


def test_monthly_clamps_to_a_short_month():
    assert tasks.next_due(date(2026, 1, 31), "monthly", date(2026, 2, 1)) \
        == date(2026, 2, 28)


def test_every_n_days_lands_on_the_schedule_not_n_days_from_now():
    # anchored 26 days back on a 3-day cycle, so the next one is 2 days out
    assert tasks.next_due(date(2026, 7, 1), "every:3", MONDAY) == date(2026, 7, 28)


def test_a_task_with_no_due_date_starts_from_today():
    assert tasks.next_due(None, "weekly", MONDAY) == date(2026, 8, 3)


# ---------- completing, repeating, undoing ----------

def test_a_plain_task_closes_when_ticked(clean_db):
    task_id = tasks.add("vacuum the living room today")
    assert tasks.complete(task_id) is None
    row = clean_db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    assert row["done"] == 1


def test_a_repeating_task_rolls_forward_instead_of_closing(clean_db):
    task_id = tasks.add("water the plants every 3 days")
    rolled = tasks.complete(task_id)

    row = clean_db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    assert row["done"] == 0, "a repeating chore never reaches a done state"
    assert row["due"] == rolled
    assert date.fromisoformat(rolled) > date.today()


def test_undo_puts_a_rolled_chore_back_on_its_old_date(clean_db):
    task_id = tasks.add("water the plants every 3 days")
    before = clean_db.query_one("SELECT due FROM tasks WHERE id = ?", (task_id,))["due"]
    tasks.complete(task_id)

    entry = clean_db.query_one("SELECT id FROM task_log ORDER BY id DESC LIMIT 1")
    tasks.undo(entry["id"])

    row = clean_db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
    assert row["due"] == before
    assert row["done"] == 0
    assert clean_db.query("SELECT * FROM task_log") == []


def test_completing_is_recorded_for_the_streak(clean_db):
    tasks.complete(tasks.add("take out the bins today"))
    assert tasks.summary()["done_today"] == 1
    assert tasks.summary()["streak"] == 1


# ---------- the board ----------

def test_tasks_land_in_the_bucket_a_person_would_expect(clean_db):
    tasks.add("late thing 2026-07-01")
    tasks.add("today thing today")
    tasks.add("tomorrow thing tomorrow")
    tasks.add("someday thing")

    buckets = {group["key"] for group in tasks.board()}
    assert buckets == {"overdue", "today", "tomorrow", "someday"}


def test_the_person_filter_only_shows_that_person(clean_db):
    tasks.add("dishes today @Ana")
    tasks.add("laundry today @Bruno")

    titles = [t["title"] for g in tasks.board("Ana") for t in g["tasks"]]
    assert titles == ["Dishes"]


def test_the_same_person_always_gets_the_same_colour():
    assert tasks.hue("Maria") == tasks.hue("maria")
    assert tasks.initials("ana maria") == "AM"
