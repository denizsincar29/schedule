from datetime import datetime, timedelta, date #, time
from dateutil.relativedelta import relativedelta
import json
import os
from modeus import modeus_parse_token, get_schedule, search_person, who_goes, modeus_auth
# getting rid of old schedparser and using new one
from parsers.events import Event, Events
from parsers.people import Person, People, noone  # noone is a singleton

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
        self.results=People()
        self.people=People()  # self.current_person is now self.people.current and friend is self.people.friend
        self.last_events=Events()
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

    def save_current_person(self, person: Person=noone, itsme: bool=True):
        """
        saves person info to people.json.

        Parameters:
        person (Person): person to save. If not given, it will save self.people.current.
        itsme (bool): If True, save to self.people.current, else save to self.people.friend.

        """
        if person!=noone:
            self.people.append(person)
            if itsme:
                self.people.current=person.person_id
            else:
                self.people.friend=person.person_id
        self.people.to_cache()

    def load_people(self):
        """Loads people from people.json. If file does not exist, it will create an empty list."""
        self.people=People.from_cache()

    def get_schedule(self, person: Person=noone, start_time: date=None, end_time: date=None, overlap: Person=noone) -> Events:
        """
        Gets schedule for a person.

        Parameters:
        person (Person): person to get schedule. If not given, it will get schedule for self.people.current.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap (Person): person to get overlapping events. If not given, it will get schedule for person_id.

        Returns:
        list: Schedule of the person in json format.
        """
        if person==noone:
            person=self.people.current
        if person==noone:  # check again if it's still noone
            return Events([])
        self.check_token()
        if start_time is None:
            start_time=moscow.localize(datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_time=moscow.localize(datetime.combine(start_time, datetime.min.time()))
        if end_time is None:
            end_time=start_time+timedelta(days=1, seconds=-1)  # end of the day
        else:
            end_time=moscow.localize(datetime.combine(end_time, datetime.min.time()))+timedelta(days=1, seconds=-1)
        g=Events.from_big_mess(get_schedule(person.person_id, self.token, start_time, end_time))
        if overlap!=noone:
            h=Events.from_big_mess(get_schedule(overlap.person_id, self.token, start_time, end_time))
            return g.overlap(h)
        return g


    def get_month(self, month: int, person: Person=noone) -> Events:
        """
        Gets and caches schedule for a person for a month.

        Parameters:
        month (int): month to get schedule. If -1, it will get schedule for current month.
        person (Person): the person to get schedule. If not given, it will get schedule for self.people.current.

        Returns:
        Events: Events list of diffs for the month.
        """
        if person==noone:
            person=self.people.current
        # if month is not -1, start time replaces with that month
        start_time=moscow.localize(datetime.now()).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month!=-1:
            start_time=start_time.replace(month=month)
        end_time = start_time + relativedelta(months=1) - timedelta(seconds=1)  # i hope we don't have university events in 23:59 lol
        sched=self.get_schedule(person, start_time, end_time)
        diff=sched.to_cache(month, person.person_id)
        # delete previous month file if it exists. (also december file if january counts as previous month)
        month=12 if start_time.month==1 else start_time.month-1
        try:
            os.remove(f"cache/{month}.{person.person_id}.json")
        except FileNotFoundError:
            pass
        # filter out diffs that are outdated
        return diff  # if there is no diff, it will return empty Events object


    def search_in_cache(self, person: Person, start_date: date, end_date: date) -> Events:
        """
        Searches in cache for a person's schedule.

        Parameters:
        person_id (str): id of the person to search.
        start_date (date): start date of the schedule.
        end_date (date): end date of the schedule.

        Returns:
        Events: List of events that match the filters.
        """
        # flatten the list of all events of the range of months, then filter out the events that are not in the range of dates.
        return sum([Events.from_cache(month, person.person_id) for month in range(start_date.month, end_date.month+1)], Events()).get_events_between_dates(start_date, end_date)  # what a clever one-liner!

    def search_person_from_cache(self, term: str, by_id: bool) -> People:
        """
        Searches person in cache. If not found, returns empty People object.

        Parameters:
        term (str): The term to search (Full name or id).
        by_id (bool): If True, search by id, else search by name.

        Returns:
        People: List of people that match the term.
        """
        self.load_people()
        if len(self.people)==0:
            return []
        if by_id:
            byid=self.people.get_person_by_id(term)
            if byid!=noone:
                return [byid]
            return People([])
        return self.people.get_people_by_name(term)

    def search_person(self, term: str, by_id: bool) -> People:
        """
        Searches person in modeus. If not found, returns empty list.

        Parameters:
        term (str): The term to search (Full name or id).
        by_id (bool): If True, search by id, else search by name.

        Returns:
        People: List of people that match the term.
        """
        self.check_token()
        self.results=self.search_person_from_cache(term, by_id)
        if len(self.results)==0:
            self.results=People.from_big_mess(search_person(term, by_id, self.token)["_embedded"])
        return self.results


    def save_result(self, idx: int, itsme: bool=True):
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
        self.save_current_person(self.results[idx], itsme)
        return True


    def who_goes(self, event: Event) -> dict:
        """
        Gets who goes to an event. A list of people bound to the event.

        Parameters:
        event (Event): The event to get who goes.

        Returns:
        dict: The who goes data.
        """
        self.check_token()
        return who_goes(event.event_id, self.token)

    def schedule(self, person: Person=noone, start_time: date=None, end_time: date=None, overlap: Person=noone) -> Events:
        """
        Gets schedule for a person. It caches the schedule for the day. This function is recommended to use.

        Parameters:
        person (Person): the person to get schedule.
        start_time (date): start time of the schedule. If not given, it will get schedule for today.
        end_time (date): end time of the schedule. If not given, it will get schedule for today.
        overlap (person): person to get overlapping events.

        Returns:
        Events: Schedule of the person.
        """
        if start_time is None:
            start_time=date.today()
        if end_time is None:
            end_time=start_time
        if overlap!=noone or person!=self.people.current:  # if we overlap or we don't get our own schedule
            sch=self.get_schedule(person, start_time, end_time, overlap)
            return sch  # if we overlap, we don't cache it
        sch=self.search_in_cache(person, start_time, end_time)
        if sch.nocache: # if not nocache then just no events
            print("warning: cache miss. This is not recommended. Load cache manually for this function to work faster!")  # don't trigger this warning in production!
            sch=self.get_schedule(person, start_time, end_time)
        return sch

auth=modeus_auth # alias for modeus_auth