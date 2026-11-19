"""
Invented chat messages with the answer the rules must give: the kind of lead, or None for no lead.
None of them comes from a real chat. Add a case whenever the phrases change.
"""
from core.leads.rules import Niche

WEB = Niche(1, 1, "Websites and SEO", ("сайт*", "лендинг*", "интернет-магазин*", "seo", "next.js", "wordpress",
                                       "tilda", "website*", "landing page"))
POWER = Niche(2, 1, "Electricity", ("электрик*", "проводк*", "electrician*"))

CORPUS: list[tuple[str, str | None]] = [
    # Requests
    ("Нужен сайт для студии йоги, бюджет до 1500$, кто возьмётся?", "request"),
    ("Ищу SEO-специалиста для интернет-магазина детской одежды", "request"),
    ("Кто сделает лендинг на Tilda за неделю? Пишите в личку", "request"),
    ("НУЖЕН ЛЕНДИНГ СРОЧНО", "request"),
    ("#ищу: разработчика сайта на WordPress", "request"),
    ("Looking for a Next.js developer to rebuild our website", "request"),
    ("Есть задача: перенести сайт на новый хостинг", "request"),
    ("Нужен электрик, сгорела проводка", "request"),
    # Problems
    ("Сайт перестал открываться после обновления, что делать?", "problem"),
    ("Google не видит сайт уже месяц, помогите", "problem"),
    ("Our website is broken after the update, any help?", "problem"),
    # Vacancies
    ("#вакансия Ищем Next.js-разработчика в штат, зарплата от 3000$", "vacancy"),
    ("Hiring: full-time SEO specialist, salary $2500", "vacancy"),
    # A request phrase and a vacancy phrase: the request comes first.
    ("В команду нужен верстальщик сайтов, оклад 120к", "request"),
    # Not leads
    ("#резюме Ищу работу frontend-разработчиком, делаю сайты на React", None),
    ("Делаю сайты под ключ, наша студия даёт скидку 20%", None),
    ("#помогу Настрою SEO для вашего сайта", None),
    # Sellers with a request phrase: only the exclusion keeps them out.
    ("Наша студия сделает сайт под ключ, бюджет обсудим", None),
    ("#помогу Если нужен лендинг, пишите", None),
    ("Ищу заказы на лендинги, портфолио в профиле", None),
    ("Обновил сайт на Next.js 16, полёт нормальный", None),
    ("Нужна помощь с переездом в Тбилиси", None),
]
