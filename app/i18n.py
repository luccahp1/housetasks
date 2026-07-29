"""EN / PT-BR strings and the two date formats that differ between them.

Unknown keys fall back to the key itself, so a new string shows up as an obvious
placeholder rather than an empty gap. `%n` is the one substitution, applied by
the caller — Jinja does it with `| replace('%n', value)`.
"""

from datetime import date

STRINGS = {
    # chrome
    "app_name": ("HouseTasks", "HouseTasks"),
    "tsk_title": ("Tasks", "Tarefas"),
    "tsk_sub": ("Who's doing what around the house.",
                "Quem está fazendo o quê pela casa."),
    "add": ("Add", "Adicionar"),
    "delete": ("Delete", "Excluir"),
    "print": ("Print", "Imprimir"),
    "cancel": ("Cancel", "Cancelar"),
    "undo": ("Undo", "Desfazer"),
    "everyone": ("Everyone", "Todos"),
    "done_today": ("Done today", "Feito hoje"),

    # the hero headline, one line per state of the day
    "t_head_free": ("Nothing due today", "Nada para hoje"),
    "t_sub_free": ("The house is caught up. Add something below when it comes up.",
                   "A casa está em dia. Adicione algo abaixo quando aparecer."),
    "t_head_clear": ("All clear", "Tudo limpo"),
    "t_sub_clear": ("Everything due today is done. Go enjoy the evening.",
                    "Tudo que vencia hoje está feito. Aproveite a noite."),
    "t_head_left_one": ("1 thing left today", "Falta 1 coisa hoje"),
    "t_head_left": ("%n things left today", "Faltam %n coisas hoje"),
    "t_sub_left": ("Tick them off as you go — the ring fills up.",
                   "Vá marcando — o anel vai enchendo."),
    "t_sub_overdue_one": ("1 of them is already late.", "1 delas já está atrasada."),
    "t_sub_overdue": ("%n of them are already late.", "%n delas já estão atrasadas."),
    "t_streak": ("%n-day streak", "%n dias seguidos"),
    "t_streak_one": ("First day of a streak", "Primeiro dia da sequência"),
    "t_week_done": ("%n done this week", "%n feitas esta semana"),
    "t_of_today": ("done today", "feitas hoje"),

    # buckets
    "t_b_overdue": ("Late", "Atrasadas"),
    "t_b_today": ("Today", "Hoje"),
    "t_b_tomorrow": ("Tomorrow", "Amanhã"),
    "t_b_week": ("This week", "Esta semana"),
    "t_b_later": ("Later", "Mais tarde"),
    "t_b_someday": ("Someday", "Algum dia"),

    # when a row is due
    "t_late_one": ("1 day late", "1 dia atrasada"),
    "t_late": ("%n days late", "%n dias atrasada"),
    "t_due_today": ("today", "hoje"),
    "t_due_tomorrow": ("tomorrow", "amanhã"),

    # recurrence
    "t_rep_daily": ("every day", "todo dia"),
    "t_rep_weekdays": ("weekdays", "dias úteis"),
    "t_rep_weekly": ("every week", "toda semana"),
    "t_rep_biweekly": ("every 2 weeks", "a cada 2 semanas"),
    "t_rep_monthly": ("every month", "todo mês"),
    "t_rep_every": ("every %n days", "a cada %n dias"),
    "t_repeats": ("Repeats", "Repete"),
    "t_never": ("Doesn't repeat", "Não repete"),
    "t_back_on": ("Nice. It's back on %n.", "Boa. Volta em %n."),

    # quick add
    "t_add_ph": ("Add a task… “take out the trash tomorrow every week @Maria”",
                 "Adicione uma tarefa… “levar o lixo amanhã toda semana @Maria”"),
    "t_add_help": ("Type it like you'd say it — the date, the person and how often "
                   "it repeats are picked out for you.",
                   "Escreva como você falaria — a data, a pessoa e a frequência "
                   "são reconhecidas sozinhas."),
    "t_reads_as": ("Reading that as", "Entendendo isso como"),
    "t_empty": ("No tasks yet. Type the first one above — try “water the plants "
                "every 3 days”.",
                "Nenhuma tarefa ainda. Escreva a primeira acima — tente “regar as "
                "plantas a cada 3 dias”."),
    "t_empty_person": ("%n has nothing on their plate.", "%n está sem tarefas."),

    # edit dialog
    "t_edit": ("Edit task", "Editar tarefa"),
    "t_what": ("What needs doing", "O que precisa ser feito"),
    "t_who": ("Who", "Quem"),
    "t_who_ph": ("Anyone", "Qualquer um"),
    "t_when": ("When", "Quando"),
    "t_priority": ("Priority", "Prioridade"),
    "t_p_low": ("Low", "Baixa"),
    "t_p_normal": ("Normal", "Normal"),
    "t_p_high": ("High", "Alta"),
    "t_save": ("Save", "Salvar"),
}

_MONTHS_SHORT = (("Jan", "jan"), ("Feb", "fev"), ("Mar", "mar"), ("Apr", "abr"),
                 ("May", "mai"), ("Jun", "jun"), ("Jul", "jul"), ("Aug", "ago"),
                 ("Sep", "set"), ("Oct", "out"), ("Nov", "nov"), ("Dec", "dez"))
_WEEKDAYS_LONG = (("Monday", "segunda"), ("Tuesday", "terça"),
                  ("Wednesday", "quarta"), ("Thursday", "quinta"),
                  ("Friday", "sexta"), ("Saturday", "sábado"),
                  ("Sunday", "domingo"))


def translate(key, lang):
    """Look a key up; unknown keys pass through so raw messages still show."""
    pair = STRINGS.get(key)
    if not pair:
        return key
    return pair[1] if lang == "pt" else pair[0]


def format_date(iso, lang):
    """'Aug 5' in English, '5 ago' in Portuguese — the two orders differ."""
    if not iso:
        return ""
    month, day = _MONTHS_SHORT[int(iso[5:7]) - 1], int(iso[8:10])
    return f"{day} {month[1]}" if lang == "pt" else f"{month[0]} {day}"


def weekday_name(iso, lang):
    if not iso:
        return ""
    return _WEEKDAYS_LONG[date.fromisoformat(iso).weekday()][1 if lang == "pt" else 0]
