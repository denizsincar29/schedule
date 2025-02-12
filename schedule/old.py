from datetime import datetime, timedelta, date #, time
from dateutil.relativedelta import relativedelta
from asyncio import Event as AEvent  # we already have an Event class
import json
import os
from .modeus import modeus_parse_token, get_schedule, get_schedule_async, search_person, who_goes, modeus_auth
# getting rid of old schedparser and using new one
from .parsers.events import Event, Events
from .parsers.people import Person, People, noone, Employee

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
    def __init__(self, email: str, password: str, on_error=lambda: None) -> None:
        """
        Initialize the Schedule object with email and password. It will check the token and load it if it's not expired.

        Parameters:
        email (str): Email for modeus
        password (str): Password for modeus
        on_error (function): Function to call if token is not valid. Default is a nothing-doing function.
        """
        self.email=email if "@edu.narfu.ru" in email else email+"@edu.narfu.ru"
        self.password=password
        self.token=...
        self.expire=datetime.now()-timedelta(seconds=10)
        self.no_internet=False  # to notify the user that this app is working offline. Search results will be empty, non-cached schedule will be empty, etc.
        self.results=People()
        self.people=People()  # self.current_person is now self.people.current and friend is self.people.friend
        self.last_events=Events()
        self.last_msg=""
        self.schedstop=AEvent()  # event to stop the schedule thread
        self.config=Config()
        if not os.path.exists("cache"):
            os.mkdir("cache")
        self.check_token(on_error)


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


    def check_token(self, on_error=lambda: None):
        """Check if token is expired or not loaded. If it's expired or not loaded, get a new token. This function is automatically called, but it is a good practice to call it every 12 hours if you're developing a long running server script."""
        if self.token==...:  # first run
            self.load_token()
        if datetime.now()>self.expire or self.token is None:  # token expired or not loaded
            try:
                self.token=modeus_parse_token(self.email, self.password)
            except Exception as e:
                self.token=None
                self.no_internet=True  # not really no internet, but the server is down or something.
                on_error(str(e))
                return
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

    def get_schedule(self, person: Person=noone, start_time: date=None, end_time: date=None, overlap: Person=noone, on_finish=None) -> Events:
        """
        Gets schedule for a person.

        Parameters:
        person (Person): person to get schedule. If not given, it will get schedule for self.people.current.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap (Person): person to get overlapping events. If not given, it will get schedule for person_id.
        on_finish (function): function to run after the schedule is fetched if run asynchronously.

        Returns:
        list: Schedule of the person in json format. If async, it will return None quickly and pass the result to on_finish function.
        """
        if person==noone:
            person=self.people.current
        if person==noone or self.no_internet: # if we don't have internet, we can't get schedule.
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
        if on_finish is not None:
            cb=lambda x: on_finish(Events.from_big_mess(x))
            self.schedstop.clear()
            get_schedule_async(person.person_id, self.token, start_time, end_time, cb, self.schedstop)
            return Events([])
        try:
            g=Events.from_big_mess(get_schedule(person.person_id, self.token, start_time, end_time))
            if overlap!=noone:
                h=Events.from_big_mess(get_schedule(overlap.person_id, self.token, start_time, end_time))
                return g.overlap(h)
            return g
        except:
            self.no_internet=True
            return Events([])


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
        if self.no_internet:  # we dont cache if we don't have internet
            return Events([])
        diff=sched.to_cache(month, person.person_id)
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
        #return sum([(cache if (cache:=Events.from_cache(month, person.person_id)).nocache else self.get_month(month, person)) for month in range(start_date.month, end_date.month+1)], Events()).get_events_between_dates(start_date, end_date)  # wow, it became huger than before!
        events=Events()
        for month in range(start_date.month, end_date.month+1):
            cache=Events.from_cache(month, person.person_id)
            if cache.nocache:
                cache=self.get_month(month, person) # yep, go grab that months.
            events+=cache
        return events.get_events_between_dates(start_date, end_date)

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
            if self.no_internet:  # if we don't have internet, we can't search.
                self.results=People()
                return self.results
            try:
                self.results=People.from_big_mess(search_person(term, by_id, self.token)["_embedded"])
                # if we searched with russian letter yo, we should search with ye if we don't find anything.
                if len(self.results)==0 and "ё" in term:
                    self.results=People.from_big_mess(search_person(term.replace("ё", "е"), by_id, self.token)["_embedded"])
            except:
                self.no_internet=True
                self.results=People()
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


    def who_goes(self, event: Event) -> People:
        """
        Gets who goes to an event. A list of people bound to the event.

        Parameters:
        event (Event): The event to get who goes.

        Returns:
        People: List of people who goes to the event.
        """
        self.check_token()
        if self.no_internet:
            return People()
        try:
            ppl=People.from_who_goes(who_goes(event.event_id, self.token))  # this data doesn't have "_embedded" key
        except:
            self.no_internet=True
            return People()
        # we need to get the full data of every teacher, because who_goes doesn't return full data.
        for person in ppl:
            if person.type==Employee:
                person=person.mutate(People.from_big_mess(search_person(person.name, False, self.token)["_embedded"])[0])  # don't search by id, the api returns 500 error if we do that.
        return ppl

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
        if overlap is None:
            overlap=noone
        # print involved people
        self.last_events=self.search_in_cache(person, start_time, end_time)
        if self.last_events.nocache: # if not nocache then just no events
            print("warning: cache miss. This is not recommended. Load cache manually for this function to work faster!")  # don't trigger this warning in production!
            self.last_events=self.get_schedule(person, start_time, end_time)
        return self.last_events

    def schedule_async(self, person: Person=noone, start_time: date=None, end_time: date=None, overlap: Person=noone, on_finish=None):
        """
        Gets schedule for a person asynchronously. It caches the schedule for the day. This function is recommended to use.

        Parameters:
        person (Person): the person to get schedule.
        start_time (date): start time of the schedule. If not given, it will get schedule for today.
        end_time (date): end time of the schedule. If not given, it will get schedule for today.
        overlap (person): person to get overlapping events.
        on_finish (function): function to run after the schedule is fetched.

        Returns:
        None: Returns None quickly and pass the result to on_finish function.
        """
        if start_time is None:
            start_time=date.today()
        if end_time is None:
            end_time=start_time
        if overlap is None:
            overlap=noone
        def cb(x):
            self.last_events=x
            on_finish(x)
        self.get_schedule(person, start_time, end_time, overlap, cb)

#auth=modeus_auth # alias for modeus_auth

def auth(email, password):
    if "@edu.narfu.ru" not in email:  # allow to use the first part of the email
        email+="@edu.narfu.ru"
    try:
        return (modeus_auth(email, password), "")  # empty string means no error and either success or unsuccess confirmed by server.
    except Exception as e:
        return (True, str(e))  # if not empty, then it's an error message.