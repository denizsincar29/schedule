# lazy to fix the incorrect date parsing. Lets just not use it for now xD

from datetime import date # where is datedelta? If we add some days to 31th of a month, it should go to the next month
from dateutil.relativedelta import relativedelta
import re

months=['января','февраля','марта','апреля','мая','июня', 'июля','августа','сентября','октября','ноября','декабря']
weekdays=['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье']

# dates must be with optional month and year. e.g. 13 is 13th of current month and year, 13.12 is 13th of December of current year, 13.12.2019 is 13th of December of 2019
dotsep=re.compile(r"(\d{1,2})(?:\.(\d{1,2})(?:\.(\d{4}))?)?")
slashsep=re.compile(r"(\d{1,2})(?:/(\d{1,2})(?:/(\d{4}))?)?")
humandate=re.compile(r"(\d{1,2})\D*(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\D*(\d{4})?")
# weekdays are just the name of the day. Before it can be optionally следующ** / прошл** (to get all genders like прошлый, прошлая...)
humanweekday=re.compile(r"(?:следующ|прошл)(?:ый|ая|ое|ие)?\s*(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье)")
# wish we could have a regex creator object e.g.
# russian=RegexCreator().add_digits(1,2, regex_group=True).add_alnum(negative=True).add_words(months, regex_group=True).add_digits(4,4, regex_group=True).compile()

def russian_date(d, include_year=False):
    msg=""
    if d==date.today():
        msg="сегодня, "
    elif d==date.today()-relativedelta(days=+1):
        msg="вчера, "
    elif d==date.today()+relativedelta(days=1):
        msg="завтра, "
    #  понедельник, 12 марта 2019 года
    msg+=weekdays[d.weekday()]+", "+str(d.day)+" "+months[d.month-1]
    if include_year:
        msg+=" "+str(d.year)+" года"
    return msg

def parse_date(s):
    s=s.lower()
    if "сегодня" in s:
        return date.today()
    if "вчера" in s:
        befores=s.count("поза") # if there are multiple "поза" we can subtract more days
        return date.today()-relativedelta(days=1+befores)  # позапозапоза...вчера
    if "завтра" in s:
        afters=s.count("после") # if there are multiple "после" we can add more days
        return date.today()+relativedelta(days=1+afters)  # послепослепосле...завтра
    m=dotsep.match(s)
    if m:
        d=date.today()
        if m.group(1):
            d=d.replace(day=int(m.group(1)))
        if m.group(2):
            d=d.replace(month=int(m.group(2)))
        if m.group(3):
            d=d.replace(year=int(m.group(3)))
        return d
    m=slashsep.match(s)
    if m:
        d=date.today()
        if m.group(1):
            d=d.replace(day=int(m.group(1)))
        if m.group(2):
            d=d.replace(month=int(m.group(2)))
        if m.group(3):
            d=d.replace(year=int(m.group(3)))
        return d
    m=humandate.match(s)
    if m:
        d=date.today()
        if m.group(1):
            d=d.replace(day=int(m.group(1)))
        if m.group(2):
            d=d.replace(month=months.index(m.group(2))+1)
        if m.group(3):
            d=d.replace(year=int(m.group(3)))
        return d
    m=humanweekday.match(s)
    if m:
        weekday=weekdays.index(m.group(1))
        past_monday=date.today()-relativedelta(days=date.today().weekday())  # it can be this monday if today is monday
        if "следующ" in s:
            return past_monday+relativedelta(days=weekday+7)  # past_monday+weekday+7
        if "прошл" in s:
            return past_monday-relativedelta(days=weekday)  # past_monday
        return 
    return None



