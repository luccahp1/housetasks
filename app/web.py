"""Template plumbing: the Jinja environment and the render helper."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app import i18n

_here = Path(__file__).parent
templates = Jinja2Templates(directory=_here / "templates")
# Cache-buster keyed to the stylesheet's own mtime, so a phone that has the page
# open never holds on to yesterday's CSS after a deploy.
templates.env.globals["css_v"] = int((_here / "static" / "style.css").stat().st_mtime)


def render(request, template, **context):
    lang = request.cookies.get("lang", "en")
    context["lang"] = lang
    context["t"] = lambda key: i18n.translate(key, lang)
    context["fmt_date"] = lambda iso: i18n.format_date(iso, lang)
    context["weekday"] = lambda iso: i18n.weekday_name(iso, lang)
    return templates.TemplateResponse(request, template, context)
