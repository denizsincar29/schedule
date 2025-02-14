# NARFU schedule app.
# Became so complex!

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

# Create a schedule object
schedule = Schedule(email, password, me)


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

def choose_friends(people):
    if len(people) <= 1:
        print("У вас нет друзей")
        return
    if len(people)>2:  # if there is only me, no need to ask
        print("Выберите друга:")
    person = ask_choice_from_list(people[1:], "Выберите человека")  # no space needed in prompt, it'll make a newline
    person.pprint()
    return person

if schedule.current_person is noone:
    ask_name("Как вас зовут? Введите фио: ", people, str(people_path), break_on_fail=False)
    schedule.current_person = people[0]  # there was no, now there is

# Main loop

while True:
    try:
        cmd = input("@:> ").strip().lower()
        match cmd:
            case "today" | "сегодня":
                s = schedule(start_time=date.today(), end_time=date.today())
                print(s)  # it has __str__ method
            case "tomorrow" | "завтра":
                s=schedule(start_time=date.today() + timedelta(days=1), end_time=date.today() + timedelta(days=1))
                print(s)
            case "week" | "неделя":
                # this thingy will print till the end of the week
                # get days till the end of the week
                days = 6 - date.today().weekday()
                s = schedule(start_time=date.today(), end_time=date.today() + timedelta(days=days))
                print(s)
            case "next week" | "следующая неделя":
                # get monday of the next week
                days = 7 - date.today().weekday()
                s = schedule(start_time=date.today() + timedelta(days=days), end_time=date.today() + timedelta(days=days + 6))
                print(s)
            case "now" | "сейчас" | "!":  # bang is easier to type
                evt = schedule.now  # it's a property function
                # if it's None, check if we are on a break or in the non-working hours
                if evt is None:
                    if schedule.on_break:
                        print("Сейчас перерыв! Скоро начнётся следующая пара:\n", schedule.next)
                    elif schedule.on_non_working_time:
                        print("Сейчас не рабочее время или пары закончились")
                else:
                    print(evt)
            case "next" | "следующий" | "следующая" | "следующее" | "дальше" | "далее":  # this has record amount of synonyms!
                evt = schedule.next
                print(evt if evt is not None else "Следующей пары нет")
            case "new friend" | "новый друг":
                try:
                    ask_name("Введите фио: ", people, str(people_path))
                    schedule.overlap = people[-1]
                    schedule.get_only_friends = True
                    print("Сейчас вы просматриваете расписание этого человека. Чтобы вернуться к своему, введите 'me'")
                    # debug prints:
                    print(f"overlap: {schedule.overlap}\nme: {schedule.current_person}")
                except RuntimeError as e:
                    print(e)
            case "me" | "я":
                schedule.get_only_friends = False
                schedule.overlap = noone
                print("Теперь вы просматриваете своё расписание")
            case "get friends schedule" | "расписание друзей" | "friendsched":
                person = choose_friends(people)
                schedule.overlap = person
                schedule.get_only_friends = True
            case "overlap" | "overlaps" | "пересечение":
                person = choose_friends(people)
                schedule.overlap = person
                schedule.get_only_friends = False # me also, we get events that overlap with this person
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
                    print(schedule(start_time=start_time, end_time=end_time))
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