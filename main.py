from schedule import Schedule, noone
from datetime import datetime, date, time
from pytz import timezone
import os
import dotenv
from sys import exit  # pyinstaller can't find it in some cases

from inputval import inputwhile, input_int, inputwhile_ctrlc, ContinueLoop
import re
VERSION="1.0.0-beta2"

# compile regex for date with possible omitting of month or year
regex=re.compile(r"^((?:\d{1,2}))(?:/((?:\d{1,2}))(?:/((?:\d{4}|\d{2})))?)?(?: +((?:together)))?$")

def search_person_cb(fio, itsme=True):
    s.search_person(fio, False)
    results=s.results
    if len(results)==0:
        raise ContinueLoop("Не нашёл тебя в базе данных, попробуй еще раз!")  # raise exception to continue loop
    elif len(results)>1:
        print("Нашёл несколько человек с таким именем, уточни пожалуйста!")
        s.results.pprint()
        choice=input_int("Выбери номер ->", 1, len(results))
        if not s.save_result(choice-1, itsme):
            raise ContinueLoop("Ошибка сохранения! Попробуй еще раз!")  # raise exception to continue loop
    else:
        if not s.save_result(0, itsme):
            raise ContinueLoop("Ошибка сохранения! Попробуй ещё раз!")
    print("Нашёл тебя! Вот твои данные:" if itsme else "Нашёл человека! Вот его данные:")
    whos=s.people.current if itsme else s.people.friend
    if whos==noone:
        raise ValueError("Person not saved! whos is None! Debug info: ", s.people.current, s.people.friend)
    whos.pprint()
    # get month and notify about diffs
    s.get_month(-1).pprint_diff()


def command(cmd):  # inputwhile callback
    cmd=cmd.lower()
    whos=s.people.current if s.people.friend==noone or "together" in cmd  else s.people.friend  # if together, then
    overlap=noone
    if "together" in cmd:
        if s.people.friend==noone:
            print("Сначала выбери человека, с которым хочешь посмотреть расписание! Используй friend или search.")
            return  # really we don't need to proceed!
        overlap=s.people.friend
    if cmd=="exit" or cmd=="" or cmd=="quit":  # or just press enter
        print("Выход")
        exit()
    if cmd=="resave":
        inputwhile("Как тебя зовут? ->", search_person_cb)  # resave
        return
    if cmd=="search" or cmd=="friend":
        inputwhile("Как зовут? ->", search_person_cb, False)
        return
    if cmd.startswith("today"):
        #print(whos, "overlapped with", overlap)  # debug
        s.last_msg=s.schedule(whos, date.today(), overlap=overlap).pprint(whos)
        return
    if (reg:=regex.match(cmd)):  # if matches date
        c=reg.groups()
        start_time=date.today()
        if c[0] is not None: start_time=start_time.replace(day=int(c[0]))
        if c[1] is not None: start_time=start_time.replace(month=int(c[1]))
        if c[2] is not None: start_time=start_time.replace(year=int(c[2]))
        s.last_msg=s.schedule(whos, start_time, overlap=overlap).pprint(whos)
        return
    elif cmd.startswith("reset"):
        s.people.friend=noone
        print("Всё, ты прекратил следить за другим человеком. Теперь ты снова один!")
        return
    elif cmd.startswith("txt"):
        with open("schedule.txt", "w", encoding="UTF-8") as f:
            f.write(s.last_msg)
        print("Сохранил расписание в файл schedule.txt")
        return
    elif cmd.startswith("thisweek"):
        # set start_time to the beginning of the week and end_time to the end of the week
        now=date.today()
        wd=now.weekday()
        monday=now.replace(day=now.day-wd)
        sunday=monday.replace(day=monday.day+6)
        s.last_msg=s.schedule(whos, monday, sunday, overlap=overlap).pprint(whos)
        return
    elif cmd.startswith("nextweek"):
        # set start_time to the beginning of the week and end_time to the end of the week
        now=date.today()
        wd=now.weekday()
        monday=now.replace(day=now.day-wd+7)
        sunday=monday.replace(day=monday.day+6)
        s.last_msg=s.schedule(whos, monday, sunday, overlap=overlap).pprint(whos)
        return
    elif cmd.startswith("help"):
        print(f"Schedule {VERSION} by Дениз Синджар")
        print("Программа для просмотра расписания студентов, преподавателей и прочих людей в САФУ.")
        print("Поддерживает поиск людей, просмотр расписания на сегодня, на определённый день и пересечение расписания с другим человеком.")
        print("Команды вводятся на английском языке. Если в выводе отображается явно питонячья ошибка, обратитесь к разработчику.")
        print("чтобы получить расписание на определённый день, введите дату в формате дд/мм/гггг,. Если вы опустите год или месяц/год, то они будут взяты из текущей даты. Можно вводить только день, только месяц или день/месяц.")
        print("Будьте внимательны! Параметр года обычно не используется, так как расписание на долгое время не известно. Обычно он используется с декабря, чтобы получить расписание на январь следующего года.")
        print("Команда today - расписание на сегодня")
        print("К командам получения расписания можно добавить together, чтобы получить пересечение расписания с другим человеком. Например, today together, 1/1 together, 1 together и т.д.")
        print("Команда reset - прекратить следить за другим человеком. Теперь вы снова один. Используйте, если снова хотите смотреть своё расписание.")
        print("Команда resave - Поменять / пересохранить профиль. Используйте, если вы поменяли профиль или личность ахахахаха. Для поиска друга используйте friend или search.")
        print("Команда search или friend - поиск человека по имени. Используйте, чтобы получить расписание другого человека- одногруппника, преподавателя  и т.д.")
        print("exit, quit  или просто нажмите Enter - выход из программы. Ctrl+c для любителей консоли тоже работает. Если программа зависла, нажмите Ctrl+break, но это как удар по башке, не забудьте сохранить данные!")
        print("Ну и самая интуитивная команда- вы её уже сюда ввели, это help. Вот и всё. Пользуйтесь на здоровье!")

        return  
    raise ContinueLoop("Неизвестная команда!")  # raise exception to continue loop


# main code bookmark
dotenv.load_dotenv(".env")
print("Программа для просмотра расписания студентов, преподавателей и прочих людей в САФУ.")
print(f"Автор: Дениз Синджар <deniz@r1oaz.ru> 2024, версия {VERSION}")
print("Введите help для справки, когда вы попадёте в консоль программы.")
email=os.environ.get("MODEUS_EMAIL", "")
password=os.environ.get("MODEUS_PASSWORD", "")
if email=="" or password=="":
    email = input("Введите email ->")
    password = input("Введите пароль ->")
    os.environ["MODEUS_EMAIL"]=email
    os.environ["MODEUS_PASSWORD"]=password
    # we can't save directly to .env file, so we need to save it to a file and then append it to .env file
    with open(".env", "w", encoding="UTF-8") as f:
        f.write(f"MODEUS_EMAIL={email}\nMODEUS_PASSWORD={password}\n")
s=Schedule(email, password)
# load me from cache. If not found, ask for name
s.load_people()

if s.people.current==noone:
    inputwhile("Привет! Я тебя не знаю, как тебя зовут? ->", search_person_cb)
print("Привет!")
diffs=s.get_month(-1).pprint_diff()

print("Введи команду")
inputwhile_ctrlc("->", command)
print("Выход")