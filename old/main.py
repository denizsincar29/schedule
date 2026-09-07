# NARFU schedule app.
# Became so complex!

# nuitka-if: {OS} in ("Windows", "Linux", "Darwin", "FreeBSD"):
#    nuitka-project: --onefile
# nuitka-project-else:
#    nuitka-project: --mode=standalonealone


import os
import dotenv
from pathlib import Path
from datetime import date, timedelta
from schedule import Schedule, People, noone
from datecommand import parse_date
from cutils import ask_choice_from_list, ask_while, longprint, CallFailed

# Load environment variables
dotenv.load_dotenv()
email = os.getenv("MODEUS_EMAIL")
password = os.getenv("MODEUS_PASSWORD")

if not email:
    email = input("Enter your email: ")
    dotenv.set_key(".env", "MODEUS_EMAIL", email)
if not password:
    password = input("Enter your password: ")
    dotenv.set_key(".env", "MODEUS_PASSWORD", password)

# check if there is people.json and load it
people_path = Path("people.json")
if people_path.exists():
    with open(people_path, "r") as f:
        people = People.from_cache(str(people_path))
else:
    people = People()
    people.to_cache(str(people_path))

me = people[0] if people else noone
me_id = me.person_id if me != noone else None

# Create a schedule object
schedule = Schedule(email, password)
if me_id:
    schedule.set_me_id(me_id)


def ask_name(prompt, people, people_path, break_on_fail=True):
    """
    Asks the user for their name, searches for them in the schedule,
    and sets the current person.

    Args:
    prompt: str: The prompt to display to the user.
    people: People: The list of people to search for the user.
    people_path: str: The path to the people cache file.
    break_on_fail: bool: Whether to break if the user is not found.
    """
    while True:
        results = ask_while(search_cb, prompt)
        r = ask_choice_from_list(results, "Выберите человека: ")  # none if no results, automatically first if only one result without asking
        if r is None:
            print("Не удалось найти человека")
            if break_on_fail:  # asking for me is crucial, for others it's optional
                break
            continue
        # appending autoremoves duplicates
        people.append(r)
        people.to_cache(people_path)
        r.pprint()
        break

def search_cb(prompt):
    try:
        results = schedule.search_person(prompt, by_id=False)
        if not results:
            raise CallFailed("Не удалось найти человека в базе данных")
        return results
    except Exception as e:
        raise CallFailed(str(e))

if not me_id:
    ask_name("Как вас зовут? Введите фио: ", people, str(people_path), break_on_fail=False)
    me = people[0]
    me_id = me.person_id
    schedule.set_me_id(me_id)

# Main loop

while True:
    try:
        cmd = input("@:> ").strip().lower()
        match cmd:
            case "today" | "сегодня":
                s = schedule(me_id, start_time=date.today(), end_time=date.today())
                print(s)  # it has __str__ method
            case "tomorrow" | "завтра":
                s=schedule(me_id, start_time=date.today() + timedelta(days=1), end_time=date.today() + timedelta(days=1))
                print(s)
            case "week" | "неделя":
                # this thingy will print till the end of the week
                # get days till the end of the week
                days = 6 - date.today().weekday()
                s = schedule(me_id, start_time=date.today(), end_time=date.today() + timedelta(days=days))
                print(s)
            case "next week" | "следующая неделя":
                # get monday of the next week
                days = 7 - date.today().weekday()
                s = schedule(me_id, start_time=date.today() + timedelta(days=days), end_time=date.today() + timedelta(days=days + 6))
                print(s)
            case "now" | "сейчас" | "!":  # bang is easier to type
                evt = schedule.now(me_id)  # it's a property function
                # if it's None, check if we are on a break or in the non-working hours
                if evt is None:
                    if schedule.on_break(me_id):
                        print("Сейчас перерыв! Скоро начнётся следующая пара:\n", schedule.next(me_id))
                    elif schedule.on_non_working_time(me_id):
                        print("Сейчас не рабочее время или пары закончились")
                else:
                    print(evt)
            case "next" | "следующий" | "следующая" | "следующее" | "дальше" | "далее":  # this has record amount of synonyms!
                evt = schedule.next(me_id)
                print(evt if evt is not None else "Следующей пары нет")
            case "who goes" | "кто идёт":
                # get events that are last fetched and ask for the event
                s = schedule.last_events
                if not s:
                    print("Сегодня пар нет")
                    continue
                print("Выберите пару:")
                evt = ask_choice_from_list(s, "Выберите пару: ")
                if evt is None:
                    continue
                hg = schedule.who_goes(evt)
                if hg:
                    print("На эту пару идут:")
                    longprint(hg)  # beautiful print with page pauses and early exit
                else:
                    print("На эту пару никто не идёт")  # impossible to reach. At least I and teacher go!
            case "file" | "файл":
                with Path("schedule.txt").open("w", encoding="UTF-8") as f:
                    f.write(str(schedule.last_events))  # get what was last printed
                print("Расписание сохранено в файле schedule.txt")
            case "help" | "помощь":
                with Path("command_help.md").open("r", encoding="UTF-8") as f:
                    print(f.read())
            case "exit" | "выход":
                break
            case _:
                try:
                    start_time, end_time = parse_date(cmd)
                    print(schedule(me_id, start_time=start_time, end_time=end_time))
                except ValueError:
                    print("Не удалось распознать команду")  # all cases are handled, now date parsing is the only thing left and failed
        # check if person is None or NoOne
    except Exception as e:
        #print(f"Произошла ошибка: {e}")
        raise e  # will it raise the same error as handled above?
        continue
    except KeyboardInterrupt:
        print("\nВыход")
        break