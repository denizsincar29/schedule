from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import os
from copy import deepcopy  # prevent a huge expensive error that I would spend hours to debug!
from modeus import modeus_parse_token, get_schedule, search_person, who_goes, modeus_auth
import schedparser

from pytz import timezone

from pydotdict import DotDict
moscow=timezone("europe/moscow")  # we overwrite to use localize method

CONF_PATH="config.json"

class Config(DotDict):
    """Config class for reading and writing config file. It's a dotdict, so you can access keys like config.api.token"""
    def __init__(self) -> None:
        """
        Read config file and create a dotdict object. If config file does not exist, create a new one with default values.
        """
        super().__init__()
        self.read_config()

    def read_config(self):
        """
        reads config file and creates a dotdict object.
        """
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
        """
        Saves the dotdict object to config file.
        """
        with open(CONF_PATH, "w", encoding="UTF-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)



class Schedule:
    """The main class for abstracting the modeus api"""
    def __init__(self, email: str, password: str) -> None:
        """
        Initialize the Schedule object with email and password. It will check the token and load it if it's not expired.

        Parameters:
        email (str): Email for modeus
        password (str): Password for modeus
        """
        self.email=email
        self.password=password
        self.token=...
        self.expire=datetime.now()-timedelta(seconds=10)
        self.results=schedparser.People()
        self.people=schedparser.People()
        self.current_person=schedparser.NoOne()
        self.friend=schedparser.NoOne()
        self.last_events=[]
        self.last_msg=""
        self.config=Config()
        if not os.path.exists("cache"):
            os.mkdir("cache")
        self.check_token()


    def save_token(self):
        """Save token and expire time to config file"""
        if self.token is None or self.token==...:
            return
        self.config.api.token=self.token
        self.config.api.expires=self.expire.timestamp()
        self.config.save_config()

    def load_token(self):
        """Load token and expire time from config file"""
        self.expire=datetime.fromtimestamp(self.config.api.expires)
        if datetime.now()>self.expire:
            self.token=None
        else:
            self.token=self.config.api.token


    def check_token(self):
        """Check if token is expired or not loaded. If it's expired or not loaded, get a new token. This function is automatically called, but it is a good practice to call it every 12 hours if you're developing a long running server script."""
        if self.token==...:  # first run
            self.load_token()
        if datetime.now()>self.expire or self.token is None:  # token expired or not loaded
            print("Получение токена. Пожалуйста, подождите...")
            self.token=modeus_parse_token(self.email, self.password)            
            self.expire=datetime.now()+timedelta(hours=12)  # modeus token lives for 12 hours and dies!
            self.save_token()

    def cache_people(self, people=schedparser.People():
        """
        caches people info to people.json.

        Parameters:
        people (list): List of people to cache. If not given, it will cache self.people. If given, it will append to self.people and cache it. If it's empty, it will cache self.people. If it's None, it will cache self.people but won't change it.
        """
        people.to_cache()
    def save_current_person(self, id: str=...):
        """
        saves person info to people.json.

        Parameters:
        id (str): id of the person to save. If not given, it will save self.current_person.

        """
        if id==...:
            id=self.current_person
        # open json. Save to me key, but append to people if not exists
        self.load_people()
        if self.current_person is None:
            self.current_person=id
        if self.current_person not in [p["id"] for p in self.people]:
            person=schedparser.get_person_by_id(self.current_person, self.results)
            if person is not None:
                self.people.append(person)
            else:
                raise ValueError("Person not found in results!")
        self.cache_people()


    def load_people(self):
        """Loads people from people.json. If file does not exist, it will create an empty list."""
        try:
            with open("people.json", "r", encoding="UTF-8") as f:
                perjson=json.load(f)
            self.current_person=perjson["me"]
            self.people=perjson["people"]
        except FileNotFoundError:
            self.people=[]

    def get_schedule(self, person_id: str=..., start_time=None, end_time=None, overlap_id: str="") -> list:
        """
        Gets schedule for a person.

        Parameters:
        person_id (str): id of the person to get schedule. If not given, it will get schedule for self.current_person.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap_id (str): id of the person to get overlapping events. If not given, it will get schedule for person_id.

        Returns:
        list: Schedule of the person in json format.
        """
        if person_id==...:
            person_id=self.current_person
        self.check_token()
        if start_time is None:
            start_time=moscow.localize(datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time is None:
            end_time=start_time+timedelta(days=1, seconds=-1)  # end of the day
        g=schedparser.parse_bigjson(get_schedule(person_id, self.token, start_time, end_time))
        if overlap_id!="":
            h=schedparser.parse_bigjson(get_schedule(overlap_id, self.token, start_time, end_time))
            # parsed to prepared data, lets get overlapping events
            return list(set(g).intersection(h))
        return g


    def get_month(self, month: int, person_id: str=...) -> list:
        """
        Gets and caches schedule for a person for a month.

        Parameters:
        month (int): month to get schedule. If -1, it will get schedule for current month.
        person_id (str): id of the person to get schedule. If not given, it will get schedule for self.current_person.

        Returns:
        list: List of diffs for the month.
        """
        if person_id==...:
            person_id=self.current_person
        # if month is not -1, start time replaces with that month
        start_time=moscow.localize(datetime.now()).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month!=-1:
            start_time=start_time.replace(month=month)
        end_time = start_time + relativedelta(months=1) - timedelta(days=1)
        schedjson=self.get_schedule(person_id, start_time, end_time)
        schedjson={"person": person_id, "start_time": start_time.isoformat(), "schedule": schedjson}
        # if file for this month exists, return get_diffs_for_month(old, new)  # not implemented yet
        diff=[]
        if os.path.exists(f"cache/{start_time.month}.{person_id}.json"):
            with open(f"cache/{start_time.month}.{person_id}.json", "r", encoding="UTF-8") as f:
                oldjson=json.load(f)
            diff=self.get_diffs_for_month(oldjson["schedule"], schedjson["schedule"])
        # save with filename mon.personid.json like {person: id, start_time: time, schedule: json}
        with open(f"cache/{start_time.month}.{person_id}.json", "w", encoding="UTF-8") as f:
            json.dump(schedjson, f, ensure_ascii=False, indent=2)
        # delete previous month file if it exists. (also december file if january counts as previous month)
        if start_time.month==1:
            try:
                os.remove(f"cache/12.{person_id}.json")
            except FileNotFoundError:
                pass
        else:
            try:
                os.remove(f"cache/{start_time.month-1}.{person_id}.json")
            except FileNotFoundError:
                pass
        # filter out diffs that are outdated
        return diff  # if there is no diff, it will return empty list


    def search_in_cache(self, person_id, **kwargs) -> list:
        """
        Searches in cache for a person's schedule.

        Parameters:
        person_id (str): id of the person to search.
        - date (datetime): The date to filter by.
        - delta (timedelta): The time delta to filter by.
        - start_time (str): The start time to filter by.
        - end_time (str): The end time to filter by.
        - evt_num (int): The event number to filter by.
        - evt_name_query (str): The event name query to filter by.
        - teacher_query (str): The teacher query to filter by.
        - room_query (str): The room query to filter by.
        - status (str): The status to filter by.

        Returns:
        list: List of events that match the filters.
        """

        files = [f for f in os.listdir("cache") if f.endswith(person_id+".json")]
        months=[int(f.split(".")[0]) for f in files]
        # if kwargs has date and delta, filter out the files that are not in that range
        if "date" in kwargs and "delta" in kwargs:
            files = [f for f, m in zip(files, months) if kwargs["date"].month<=m<=(kwargs["date"]+kwargs["delta"]).month]
        if "date" in kwargs and "delta" not in kwargs:
            files = [f for f, m in zip(files, months) if kwargs["date"].month==m]
        # if there is no cache, return empty dict
        if len(files)==0:
            return {}
        events=[]
        for file in files:
            with open(f"cache/{file}", "r", encoding="UTF-8") as f:
                monthjson=json.load(f)
            events+=schedparser.filter_events(monthjson["schedule"], **kwargs)
        return events



    def get_diffs_for_month(self, old_month: list, new_month: list) -> list:
        """
        Gets the diffs between two months.

        Parameters:
        old_month (list): The old month schedule.
        new_month (list): The new month schedule.

        Returns:
        list: list of events with diff marks from schedparser.py
        """
        return schedparser.diff(old_month, new_month)

    def humanize_diff(self, diffs: list) -> str:
        """
        transforms diffs to human readable format.

        Parameters:
        diffs (list): list of diffs.

        Returns:
        str: Human readable diffs.
        """
        return schedparser.human_diff(diffs)


    def humanize_person_info(self, person_id: str) -> str:
        """
        transforms person info to human readable format.

        Parameters:
        person_id (str): id of the person to get info.

        Returns:
        str: Human readable person info.
        """
        persons=self.results + self.people  # get from everywhere
        searched=False
        if persons==[]:  # if no results, search for person
            self.search_person(person_id, True)
            searched=True
            persons=self.results
        p=schedparser.humanize_person(person_id, persons)
        # if searched and not found, return not found
        if searched and p=="":
            return "Не нашел человека!"
        if not searched and p=="": # there is cache but not found
            self.search_person(person_id, True)
            p=schedparser.humanize_person(person_id, self.results)
        return p

    def search_person_from_cache(self, term: str, by_id: bool) -> list:
        """
        Searches person in cache. If not found, returns empty list.

        Parameters:
        term (str): The term to search (Full name or id).
        by_id (bool): If True, search by id, else search by name.

        Returns:
        list: List of people that match the term.
        """
        self.load_people()
        if len(self.people)==0:
            return []
        if by_id:
            byid=schedparser.get_person_by_id(term, self.people)
            if byid is not None:
                return [byid]
            return []
        return [p for p in self.people if term.lower() in p["name"].lower()]

    def search_person(self, term: str, by_id: bool) -> list:
        """
        Searches person in modeus. If not found, returns empty list.

        Parameters:
        term (str): The term to search (Full name or id).
        by_id (bool): If True, search by id, else search by name.

        Returns:
        list: List of people that match the term.
        """
        self.check_token()
        # load people from cache
        self.load_people()
        # search in cache first
        self.results=self.search_person_from_cache(term, by_id)
        if len(self.results)==0:
            self.results=schedparser.parse_people(search_person(term, by_id, self.token)["_embedded"])
        return self.results


    def save_result(self, idx: int, itsme=True):
        """
        Saves the result to people cache.

        Parameters:
        idx (int): The index of the result to save (from self.results)
        itsme (bool): If True, save to self.current_person, else save to self.friend.

        Returns:
        bool: True if saved, False if not found.
        """
        if idx<0 or idx>=len(self.results):
            return False
        if itsme:
            self.current_person=self.results[idx]["id"]
            self.save_current_person()
        else:
            self.friend=self.results[idx]["id"]
        return True


    def who_goes(self, event_id: str) -> dict:
        """
        Gets who goes to an event. A list of people bound to the event.

        Parameters:
        event_id (str): The id of the event to get who goes.

        Returns:
        dict: The who goes data.
        """
        self.check_token()
        return who_goes(event_id, self.token)

    def get_person_by_id(self, person_id: str) -> dict:
        """
        Gets person by id. If not found, returns empty dict.

        Parameters:
        person_id (str): The id of the person to get.

        Returns:
        dict: The person data.
        """

        self.load_people()
        return schedparser.get_person_by_id(person_id, self.people)

    def humanize_person(self, person_id: str, data: list) -> str:
        """
        transforms person info to human readable format.

        Parameters:
        person_id (str): id of the person to get info.
        data (dict): List of people to search.

        Returns:
        str: Human readable person info.
        """
        self.check_token()
        return  schedparser.humanize_person(person_id, data)

    def schedule(self, person_id: str, start_time=None, end_time=None, overlap_id: str="") -> dict:
        """
        Gets schedule for a person. It caches the schedule for the day. This function is recommended to use.

        Parameters:
        person_id (str): id of the person to get schedule.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap_id (str): id of the person to get overlapping events.

        Returns:
        dict: Schedule of the person in json format.
        """
        # this function must be used for getting schedule because it caches it, only use get_schedule for getting from server or you need to get overlapping events

        if start_time is None:
            start_time=moscow.localize(datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_time is None:
            end_time=start_time+timedelta(days=1, seconds=-1)  # end of the day
        # search in cache first, if not found, get from server
        if overlap_id!="":  # if overlap_id is given, get overlapping events
            sch=self.get_schedule(person_id, start_time, end_time, overlap_id)
            return sch  # if we overlap, we don't cache it
        sch=self.search_in_cache(person_id=person_id, date=start_time, delta=end_time-start_time)  # timedelta object for delta
        if sch=={}:  # prevent empty cache, schedule a task to get from server every hour
            sch=self.get_schedule(person_id, start_time, end_time)
        return sch



    def get_schedule_str(self, person_id: str, start_time=None, end_time=None, overlap_id: str="") -> str:
        """
        Gets schedule for a person and transforms it to human readable format.

        Parameters:
        person_id (str): id of the person to get schedule.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap_id (str): id of the person to get overlapping events.

        Returns:
        str: Human readable schedule.
        """
        if overlap_id is None:
            overlap_id=""
        if overlap_id !="":
            self.last_msg = f"Общее расписания пользователя {self.get_person_by_id(person_id)['name']} и {self.get_person_by_id(overlap_id)['name']}:\n"
        else:
            self.last_msg=f"Расписание пользователя {self.get_person_by_id(person_id)['name']}:\n"
        self.last_msg+=schedparser.humanize_events(self.schedule(person_id, start_time, end_time, overlap_id))
        return self.last_msg



auth=modeus_auth # alias for modeus_auth