from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from modeus import modeus_parse_token, get_schedule, search_person, who_goes

from pytz import timezone, UTC
import schedparser

from pydotdict import DotDict
CONF_PATH="config.json"

class Config(DotDict):
    # config file reader and writer (inherits from DotDict for easy access to keys)
    def __init__(self) -> None:
        super().__init__()
        self.read_config()

    def read_config(self):
        try:
            with open(CONF_PATH, "r", encoding="UTF-8") as f:
                self._dict=json.load(f)
                # dotdictify all keys
                for key in self._dict:
                    self[key]=DotDict(self._dict[key])
        except FileNotFoundError:
            self._dict={"api": DotDict({"token": "", "expires": 1})}
            self.save_config()


    def save_config(self):
        with open(CONF_PATH, "w", encoding="UTF-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

class Schedule:
    def __init__(self, email: str, password: str) -> None:
        self.email=email
        self.password=password
        self.token=...
        self.expire=datetime.now()-timedelta(seconds=10)
        self.results=[]  # for searching people
        self.people=[]  # for caching people. Dont touch results, it's for searching
        self.current_person=None
        self.friend=None
        self.last_events=[]
        self.config=Config()
        self.check_token()


    def save_token(self):
        if self.token is None or self.token==...:
            print("no token, ignoring!")
            return
        self.config.api.token=self.token
        self.config.api.expires=self.expire.timestamp()
        self.config.save_config()
        print("saved new token")

    def load_token(self):
        self.expire=datetime.fromtimestamp(self.config.api.expires)
        if datetime.now()>self.expire:
            self.token=None
        else:
            self.token=self.config.api.token


    def check_token(self):
        if self.token==...:  # first run
            self.load_token()
        if datetime.now()>self.expire or self.token==None:  # token expired or not loaded
            print("getting_token")
            self.token=modeus_parse_token(self.email, self.password)            
            self.expire=datetime.now()+timedelta(hours=12)  # modeus token lives for 12 hours and dies!
            self.save_token()

    def cache_people(self, people=[]):
        # save self.people to cache, but append and remove duplicates
        if people==[] or people==None: people=self.people.copy()  # when self.people changes, dont change people.
        else: people=people.copy()  # or it will change the original list
        current_person=self.current_person
        self.load_people()
        if self.current_person is None: self.current_person=current_person  # retrieve back
        ids=[p["id"] for p in people]
        for person in self.people:
            if person["id"] not in ids:
                people.append(person)
        with open("people.json", "w", encoding="UTF-8") as f: json.dump({"me": self.current_person, "people": people}, f, ensure_ascii=False, indent=2)

    def save_current_person(self, id: str=...):
        if id==...: id=self.current_person
        # open json. Save to me key, but append to people if not exists
        self.load_people()
        if self.current_person is None:
            self.current_person=id
        if self.current_person not in [p["id"] for p in self.people]:
            person=schedparser.get_person_by_id(self.current_person, self.results)
            if person is not None: self.people.append(person)
            else: raise ValueError("Person not found in results!")
        self.cache_people()


    def load_people(self):
        try:
            with open("people.json", "r", encoding="UTF-8") as f: perjson=json.load(f)
            self.current_person=perjson["me"]
            self.people=perjson["people"]
        except FileNotFoundError:
            self.people=[]

    def get_schedule(self, person_id: str=..., start_time=None, end_time=None, overlap_id: str="") -> dict:
        if person_id==...: person_id=self.current_person
        self.check_token()
        if start_time is None: start_time=datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time is None: end_time=start_time+timedelta(days=1)
        g=schedparser.parse_bigjson(get_schedule(person_id, self.token, start_time, end_time))
        if overlap_id!="" and "events" in g["_embedded"]:
            h=schedparser.parse_bigjson(get_schedule(overlap_id, self.token, start_time, end_time))
            # parsed to prepared data, lets get overlapping events
            return list(set(g).intersection(h))
        return g


    def get_month(self, month: int, person_id: str=...) -> list:
        if person_id==...: person_id=self.current_person
        # if month is not -1, start time replaces with that month
        start_time=datetime.now(timezone("europe/moscow")).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month!=-1: start_time=start_time.replace(month=month)
        end_time = start_time + relativedelta(months=1) - timedelta(days=1)
        schedjson=self.get_schedule(person_id, start_time, end_time)
        schedjson={"person": person_id, "start_time": start_time.isoformat(), "schedule": schedjson}
        # if file for this month exists, return get_diffs_for_month(old, new)  # not implemented yet
        diff=[]
        if os.path.exists(f"cache/{start_time.month}.{person_id}.json"):
            with open(f"cache/{start_time.month}.{person_id}.json", "r", encoding="UTF-8") as f: oldjson=json.load(f)
            diff=self.get_diffs_for_month(oldjson["schedule"], schedjson["schedule"])
        # save with filename mon.personid.json like {person: id, start_time: time, schedule: json}
        with open(f"cache/{start_time.month}.{person_id}.json", "w", encoding="UTF-8") as f: json.dump(schedjson, f, ensure_ascii=False, indent=2)
        # delete previous month file if it exists. (also december file if january counts as previous month)
        if start_time.month==1:
            try: os.remove(f"cache/12.{person_id}.json")
            except FileNotFoundError: pass
        else:
            try: os.remove(f"cache/{start_time.month-1}.{person_id}.json")
            except FileNotFoundError: pass
        # filter out diffs that are outdated
        diff=schedparser.filter_events(diff, datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0))
        return diff  # if there is no diff, it will return empty list


    def search_in_cache(self, person_id, **kwargs) -> dict:
        files = [f for f in os.listdir("cache") if f.endswith(person_id+".json")]
        months=[int(f.split(".")[0]) for f in files]
        # if kwargs has date and delta, filter out the files that are not in that range
        if "date" in kwargs and "delta" in kwargs:
            files = [f for f, m in zip(files, months) if kwargs["date"].month<=m<=(kwargs["date"]+kwargs["delta"]).month]
        if "date" in kwargs and "delta" not in kwargs:
            files = [f for f, m in zip(files, months) if kwargs["date"].month==m]
        # if there is no cache, return empty dict
        if len(files)==0: return {}
        events=[]
        for file in files:
            with open(f"cache/{file}", "r", encoding="UTF-8") as f: monthjson=json.load(f)
            events+=schedparser.filter_events(monthjson["schedule"], **kwargs)
        return events



    def get_diffs_for_month(self, old_month: list, new_month: list) -> list:
        return schedparser.diff(old_month, new_month)

    def humanize_diff(self, diffs: dict) -> str:
        return schedparser.human_diff(diffs)


    def humanize_person_info(self, person_id: str) -> dict:
        persons=self.results + self.people  # get from everywhere
        searched=False
        if persons==[]:  # if no results, search for person
            self.search_person(person_id, True)
            searched=True
            persons=self.results
        p=schedparser.humanize_person(person_id, persons)
        # if searched and not found, return not found
        if searched and p=="": return "Не нашел человека!"
        if not searched and p=="": # there is cache but not found
            self.search_person(person_id, True)
            p=schedparser.humanize_person(person_id, self.results)
        return p

    def search_person_from_cache(self, term: str, by_id: bool) -> dict:
        self.load_people()
        if len(self.people)==0: return []
        if by_id:
            byid=schedparser.get_person_by_id(term, self.people)
            if byid is not None: return [byid]
            return []
        return [p for p in self.people if term.lower() in p["name"].lower()]

    def search_person(self, term: str, by_id: bool) -> dict:
        self.check_token()
        # load people from cache
        self.load_people()
        # search in cache first
        self.results=self.search_person_from_cache(term, by_id)
        if len(self.results)==0:
            self.results=schedparser.parse_people(search_person(term, by_id, self.token)["_embedded"])


    def save_result(self, idx: int, itsme=True):
        if idx<0 or idx>=len(self.results): return False
        if itsme:
            self.current_person=self.results[idx]["id"]
            self.save_current_person()
        else:
            self.friend=self.results[idx]["id"]
        return True


    def who_goes(self, event_id: str) -> dict:
        self.check_token()
        return who_goes(event_id, self.token)

    def humanize_person(self, person_id: str, data: str) -> dict:
        self.check_token()
        return  schedparser.humanize_person(person_id, data)

    def schedule(self, person_id: str, start_time=None, end_time=None, overlap_id: str="") -> dict:
        # this function must be used for getting schedule because it caches it, only use get_schedule for getting from server or you need to get overlapping events

        if start_time is None: start_time=datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time is None: end_time=start_time+timedelta(days=1)
        # search in cache first, if not found, get from server
        if overlap_id!="":  # if overlap_id is given, get overlapping events
            sch=self.get_schedule(person_id, start_time, end_time, overlap_id)
            return sch  # if we overlap, we don't cache it
        sch=self.search_in_cache(person_id=person_id, date=start_time, delta=end_time-start_time)  # timedelta object for delta
        if sch=={}:  # prevent empty cache, schedule a task to get from server every hour
            sch=self.get_schedule(person_id, start_time, end_time)
        return sch



    def get_schedule_str(self, person_id: str, start_time=None, end_time=None, overlap_id: str="") -> str:
        # overlap_id is the id of another person to check for overlapping events
        return schedparser.humanize_events(self.schedule(person_id, start_time, end_time, overlap_id))



# main function
if __name__ == "__main__":
    from inputval import inputwhile, input_int, inputwhile_ctrlc, ContinueLoop
    import re

    # compile regex for date with possible omitting of month or year
    regex=re.compile(r"^((?:\d{1,2}))(?:/((?:\d{1,2}))(?:/((?:\d{4}|\d{2})))?)?(?: +((?:together)))?$")
    def search_person_cb(fio, itsme=True):
        s.search_person(fio, False)
        results=s.results
        if len(results)==0:
            raise ContinueLoop("Не нашёл тебя в базе данных, попробуй еще раз!")  # raise exception to continue loop
        elif len(results)>1:
            print("Нашёл несколько человек с таким именем, уточни пожалуйста!")
            for i, r in enumerate(results):
                print(f"{i+1}: {schedparser.humanize_person(r['id'], [r])}")  # not passing all people, just the result: a smart move but is it faster?
            choice=input_int("Выбери номер ->", 1, len(results))
            if not s.save_result(choice-1, itsme):
                raise ContinueLoop("Ошибка сохранения! Попробуй еще раз!")  # raise exception to continue loop
        else:
            if not s.save_result(0, itsme):
                raise ContinueLoop("Ошибка сохранения! Попробуй еще раз!")
        print("Нашёл тебя! Вот твои данные:" if itsme else "Нашёл человека! Вот его данные:")
        whos=s.current_person if itsme else s.friend
        if whos is None: # debug
            raise ValueError("Person not saved! whos is None! Debug info: ", s.current_person, s.friend)
        print(s.humanize_person_info(whos))

    def command(cmd):  # inputwhile callback
        if cmd=="exit" or cmd=="" or cmd=="quit":  # or just press enter
            print("Выход")
            exit()
        if cmd=="resave":
            fio=inputwhile("Как тебя зовут? ->", search_person_cb)  # resave
            return
        if cmd=="search" or cmd=="friend":
            fio=inputwhile("Как зовут? ->", search_person_cb, False)
            return
        if cmd.startswith("today"):
            if "together" in cmd:
                if s.friend is None:
                    print("Сначала выбери человека, с которым хочешь посмотреть расписание! Используй friend или search.")
                    return
                print(s.get_schedule_str(s.current_person, datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0), overlap_id=s.friend))
                return
            whos=s.current_person if s.friend is None else s.friend  # if not together, then not overlap but just friend.
            if s.friend is not None:
                print("Смотрим чужое расписание!")
            print(s.get_schedule_str(whos, datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0)))
            return
        if regex.match(cmd):
            c=regex.match(cmd).groups()
            start_time=datetime.now(timezone("europe/moscow")).replace(hour=0, minute=0, second=0, microsecond=0)
            # do as deprecated lines but with this groups. Length of c is always 4, so we don't need to check
            if c[0] is not None: start_time=start_time.replace(day=int(c[0]))
            if c[1] is not None: start_time=start_time.replace(month=int(c[1]))
            if c[2] is not None: start_time=start_time.replace(year=int(c[2]))
            if c[3] is not None:  # if together is given, get overlapping events
                if s.friend is None:
                    print("Сначала выбери человека, с которым хочешь посмотреть расписание! Используй friend или search.")
                    return
                print(s.get_schedule_str(s.current_person, start_time, overlap_id=s.friend))
                return
            whos=s.current_person if s.friend is None else s.friend  # if not together, then not overlap but just friend.
            if s.friend is not None:
                print("Смотрим чужое расписание!")
            print(s.get_schedule_str(whos, start_time))
            return
        elif cmd.startswith("reset"):
            s.friend=None
            print("Всё, ты прекратил следить за другим человеком. Теперь ты снова один!")
        elif cmd.startswith("help"):
            print("Schedule 2.0 by Дениз Синджар")
            print("Программа для просмотра расписания студентов, преподавателей и прочих людей в САФУ.")
            print("Поддерживает поиск людей, просмотр расписания на сегодня, на определённый день и пересечение расписания с другим человеком.")
            print("Использует неофициальный API сайта modeus.org. Не хранит данные о пользователях, кроме кэша для ускорения работы. Кеш можно спокойно открыть, прочитать и удалить.")
            print("При первом запуске программа спросит email и пароль от modeus.org. Программа автоматически сохранит их в файл .env, чтобы не спрашивать каждый раз.")
            print("Модеус устроен так, что даже с вашим логином, можно узнавать расписание кого угодно, поэтому потом программа у вас спросит ваше фио. (Если программа вас не находит и у вас есть буква ё, экспериментируйте и пробуйте с Е.")
            print("Затем вы попадаете в главную консоль программы.")
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


    import os
    import dotenv
    dotenv.load_dotenv()
    print("Программа для просмотра расписания студентов, преподавателей и прочих людей в САФУ.")
    print("Автор: Дениз Синджар <deniz@r1oaz.ru> 2024, версия 2.0")
    print("Введите help для справки, когда вы попадёте в консоль программы.")
    email=os.environ.get("MODEUS_EMAIL", "")
    password=os.environ.get("MODEUS_PASSWORD", "")
    if email=="" or password=="":
        email = input("Введите email ->")
        password = input("Введите пароль ->")
        os.environ["MODEUS_EMAIL"]=email
        os.environ["MODEUS_PASSWORD"]=password
        # we can't save directly to .env file, so we need to save it to a file and then append it to .env file
        with open(".env", "w", encoding="UTF-8") as f: f.write(f"MODEUS_EMAIL={email}\nMODEUS_PASSWORD={password}\n")
    s=Schedule(email, password)
    # load me from cache. If not found, ask for name
    s.load_people()
    
    if s.current_person is None:  # if not found, ask for name
        inputwhile("Привет! Я тебя не знаю, как тебя зовут? ->", search_person_cb)
    print("Привет!")
    diffs=s.get_month(-1)  # get month and notify about diffs
    if diffs!=[]:
        print("Ваше расписание изменилось!")
        print(s.humanize_diff(diffs))

    print("Введи команду")
    inputwhile_ctrlc("->", command)
    print("Выход")