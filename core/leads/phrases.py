"""
Phrases that tell a lead's kind, in Russian and English, written for mentions(): a * at the end matches every
word that starts with it. They hardly depend on the niche; tests/lead_corpus.py checks them.
"""

REQUEST = (
    "ищу", "ищем", "нужен", "нужна", "нужны", "кто сделает", "кто может", "кто возьмется", "кто возьмётся",
    "посоветуйте", "порекомендуйте", "есть задача", "тз", "бюджет",
    "looking for", "need a", "need an", "who can", "recommend*",
)

PROBLEM = (
    "не работает", "не открывается", "перестал*", "сломал*", "ошибк*", "помогите", "подскажите", "что делать",
    "проблема", "проблемы",
    "doesn't work", "does not work", "not working", "broken", "help", "issue", "error*",
)

VACANCY = (
    "вакансия", "вакансии", "в штат", "в команду", "зарплата", "зп", "з/п", "оклад",
    "hiring", "salary", "full-time", "full time", "position", "vacancy",
)

# A message with any of these is not a lead: people offering their own services or looking for work.
EXCLUDE = (
    "#резюме", "#помогу", "#предлагаю", "ищу работу", "ищу заказ*", "ищу клиентов", "предлагаю услуги",
    "наша студия", "скидк*",
    "#resume", "#cv", "looking for a job", "open to work",
)

# Hashtags of job boards in chats name the kind outright, before any phrase is looked at.
HASHTAG_KINDS = {
    "#ищу": "request", "#заказ": "request", "#задача": "request",
    "#вакансия": "vacancy", "#vacancy": "vacancy", "#hiring": "vacancy",
}
