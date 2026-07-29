"""HouseTasks: a shared chore board you add to in one line of plain language.

Every action works as a plain form post and a 303 redirect. The JavaScript on the
page is enhancement only — it makes ticking something off instant instead of a
reload, and it previews what the quick-add box understood — but nothing depends
on it. Turn JavaScript off and the whole app still works.
"""

from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import i18n, tasks
from app.web import render as _render

app = FastAPI(title="HouseTasks")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"),
          name="static")


def _lang(request):
    return request.cookies.get("lang", "en")


def _who(request):
    """The person filter that was on screen, recovered from the referring URL.

    Keeps every form on the page free of a hidden field just to survive the
    redirect, and the JSON path needs it too so the counts match what is shown.
    """
    referer = request.headers.get("referer", "")
    if not referer:
        return ""
    return parse_qs(urlsplit(referer).query).get("who", [""])[0].strip()


def _back(request):
    who = _who(request)
    return RedirectResponse(f"/?who={quote(who)}" if who else "/", status_code=303)


def _summary(request, person=""):
    """The numbers, plus the one line that names the state of the day."""
    lang = _lang(request)
    summary = tasks.summary(person)
    if not summary["today_total"]:
        headline, sub = "t_head_free", "t_sub_free"
    elif not summary["left"]:
        headline, sub = "t_head_clear", "t_sub_clear"
    else:
        headline = "t_head_left_one" if summary["left"] == 1 else "t_head_left"
        sub = "t_sub_left"
        if summary["overdue"]:
            sub = "t_sub_overdue_one" if summary["overdue"] == 1 else "t_sub_overdue"
    summary["headline"] = i18n.translate(headline, lang).replace(
        "%n", str(summary["left"]))
    summary["sub"] = i18n.translate(sub, lang).replace("%n", str(summary["overdue"]))
    return summary


def _repeat_label(rule, lang):
    if rule.startswith("every:"):
        return i18n.translate("t_rep_every", lang).replace("%n", rule.split(":", 1)[1])
    return i18n.translate(f"t_rep_{rule}", lang)


def _due_label(iso, lang):
    """How a person would say that date: today, tomorrow, Friday, or Aug 12."""
    days = (date.fromisoformat(iso) - date.today()).days
    if days == 0:
        return i18n.translate("t_due_today", lang).capitalize()
    if days == 1:
        return i18n.translate("t_due_tomorrow", lang).capitalize()
    if 0 < days <= 7:
        return i18n.weekday_name(iso, lang).capitalize()
    return i18n.format_date(iso, lang)


@app.get("/", response_class=HTMLResponse)
def board(request: Request):
    who = request.query_params.get("who", "").strip()
    return _render(request, "tasks.html",
                   board=tasks.board(who),
                   summary=_summary(request, who),
                   done_today=tasks.done_today(who),
                   people=tasks.people(),
                   who=who)


@app.get("/lang/{code}")
def set_language(request: Request, code: str):
    """Persist the UI language for a year — it gets set once and forgotten."""
    response = RedirectResponse(request.headers.get("referer") or "/", status_code=303)
    response.set_cookie("lang", code if code in ("en", "pt") else "en",
                        max_age=60 * 60 * 24 * 365)
    return response


@app.get("/parse")
def parse_preview(request: Request):
    """What the quick-add box would create — shown as chips while you type.

    Deliberately the same parser that the add route uses. A second copy in
    JavaScript would drift, and then the preview would be a polite lie.
    """
    lang = _lang(request)
    fields = tasks.parse(request.query_params.get("text", ""))
    if not fields:
        return JSONResponse({"title": ""})
    chips = [{"kind": "title", "text": fields["title"]}]
    if fields["due"]:
        chips.append({"kind": "date", "text": _due_label(fields["due"], lang)})
    if fields["repeat_rule"]:
        chips.append({"kind": "rep", "text": _repeat_label(fields["repeat_rule"], lang)})
    if fields["assignee"]:
        chips.append({"kind": "who", "text": fields["assignee"]})
    if fields["priority"] != "normal":
        chips.append({"kind": "prio",
                      "text": i18n.translate(f"t_p_{fields['priority']}", lang)})
    return JSONResponse({"title": fields["title"], "chips": chips})


@app.post("/add")
def add(request: Request, text: str = Form("")):
    tasks.add(text)
    return _back(request)


@app.post("/{task_id}/done")
def complete(request: Request, task_id: int):
    rolled = tasks.complete(task_id)
    if "application/json" not in request.headers.get("accept", ""):
        return _back(request)
    lang = _lang(request)
    summary = _summary(request, _who(request))
    # Worth a celebration only if there was something to clear in the first place.
    summary["cleared"] = bool(summary["today_total"]) and not summary["left"]
    summary["flash"] = (i18n.translate("t_back_on", lang)
                        .replace("%n", i18n.format_date(rolled, lang))
                        if rolled else "")
    return JSONResponse(summary)


@app.post("/log/{log_id}/undo")
def undo(request: Request, log_id: int):
    tasks.undo(log_id)
    return _back(request)


@app.post("/{task_id}/update")
async def update(request: Request, task_id: int):
    form = await request.form()
    tasks.update(task_id, form.get("title", ""), form.get("assignee", ""),
                 form.get("due", ""), form.get("priority", "normal"),
                 form.get("repeat_rule", ""))
    return _back(request)


@app.post("/{task_id}/delete")
def delete(request: Request, task_id: int):
    tasks.delete(task_id)
    return _back(request)
