# This file is a part of the schedule fetcher for Northern Arctic Federal University.
# I'm rewriting the 90% of the code because it was a huge mess!

import json
from pathlib import Path
from datetime import datetime, timedelta, date #, time
from .modeus import modeus_parse_token, get_schedule, search_person, who_goes, modeus_auth
from .parsers.events import Event, Events
from .parsers.people import Person, People, noone, Employee, NoOne

from pytz import timezone

moscow=timezone("europe/moscow")  # we overwrite to use localize method

class NoCacheError(Exception):
    """Raised when there is no cache for the person or the schedule for the specific date/time is not cached."""
    pass

class Schedule:
    """The main class for abstracting the modeus api"""
    def __init__(self, email: str, password: str, default_person: Person=noone, cache_folder: str=".cache"):
        """
        Initialize the Schedule object with email and password. It will check the token and load it if it's not expired.

        Parameters:
        email (str): Email for modeus
        password (str): Password for modeus
        default_person (Person): Default person to get schedule. If not given, it will get schedule for self.people.current
        cache_folder (str): Folder to save the cache. If not given, it will save in .cache folder.
        """
        self.email=email if "@edu.narfu.ru" in email else email+"@edu.narfu.ru"
        self.password=password
        self.token=...
        self.expire=datetime.now()-timedelta(seconds=10)
        self.last_events=Events()
        self.last_msg=""
        self.cache_folder=Path(cache_folder)
        self.cache_folder.mkdir(exist_ok=True)
        
        self.check_token()
        self.current_person: Person=default_person
        self.overlap: Person=noone
        self.get_only_friends=False  # only overlapped friend's schedule, not mine.
        # update cache for today to next 3 weeks
        self.cache_schedule(datetime.now(), datetime.now()+timedelta(days=21), True)

    def check_token(self):
        """
        Checks if token is expired or not loaded. If it's expired or not loaded, get a new token. This function is automatically called, but it is a good practice to call it every 12 hours if you're developing a long running server script.
        The token fetched from modeus very slowly, in a few requests and regex parsing, so it's better to load only on start up.

        Raises:
        Exception: If the token is not loaded successfully or internet connection is not available.
        """
        if datetime.now()>self.expire or self.token is None:  # token expired or not loaded
            try:
                self.token=modeus_parse_token(self.email, self.password)
            except Exception as e:
                self.token=None
                raise e
            self.expire=datetime.now()+timedelta(hours=12)  # modeus token lives for 12 hours and dies!

    def set_person(self, person: Person):
        """Set the current person to get schedule."""
        self.current_person=person

    def fetch_schedule(self, start_time: date=None, end_time: date=None) -> Events:
        """
        Gets schedule for a person.

        Parameters:
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.

        Returns:
        list: Schedule of the person in json format. If async, it will return None quickly and pass the result to on_finish function.
        """
        person=self.current_person if not self.get_only_friends else self.overlap
        if person==noone:
            raise ValueError("No person to get schedule.")
        overlap=self.overlap if not self.get_only_friends else noone
        self.check_token()
        if start_time is None:
            start_time=moscow.localize(datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_time=moscow.localize(datetime.combine(start_time, datetime.min.time()))
        if end_time is None:
            end_time=start_time+timedelta(days=1, seconds=-1)  # end of the day
        else:
            end_time=moscow.localize(datetime.combine(end_time, datetime.max.time()))
        g=Events.from_big_mess(get_schedule(person.person_id, self.token, start_time, end_time))
        if overlap!=noone:
            h=Events.from_big_mess(get_schedule(overlap.person_id, self.token, start_time, end_time))
            return g.overlap(h)
        return g

    def cache_schedule(self, start_time: date=None, end_time: date=None, override: bool=False) -> None:
        """
        Caches the schedule for a person.

        Parameters:
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        override (bool): If True, it will override the cache, else it will append to the cache.
        """
        events = self.fetch_schedule(start_time, end_time)
        folder=self.cache_folder  # lazy to rewrite the code
        person=self.current_person  # It's &mut self.current_person but in python.
        # we need to read the cache and append to it. If there is no cache, then create a new one.
        if not override:
            try:
                with (folder/f"{person.person_id}.json").open("r", encoding="utf-8") as f:
                    old_events=Events.from_prepared_json(json.load(f))
                    events += old_events  # this object automatically removes duplicates when adding.
            except FileNotFoundError:
                pass  # i got ya!
        with (folder/f"{person.person_id}.json").open("w", encoding="utf-8") as f:
            f.write(events.json())

    def load_schedule(self) -> Events:
        """
        Loads the schedule from cache.

        Returns:
        Events: Schedule of the person in json format.
        """
        folder=self.cache_folder
        person=self.current_person
        with (folder/f"{person.person_id}.json").open("r", encoding="utf-8") as f:
            return Events.from_prepared_json(json.load(f))

    def load_timed_schedule(self, start_time: date=None, end_time: date=None) -> Events:
        """
        Loads the schedule from cache.

        Parameters:
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.

        Returns:
        Events: Schedule of the person in json format.
        """
        if start_time is None:
            start_time=moscow.localize(datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_time=moscow.localize(datetime.combine(start_time, datetime.min.time()))
        if end_time is None:
            end_time=start_time+timedelta(days=1, seconds=-1)
        else:
            end_time=moscow.localize(datetime.combine(end_time, datetime.max.time()))
        # now load the whole schedule
        events = self.load_schedule()
        # now filter the schedule
        return events.get_events_between_dates(start_time.date(), end_time.date())  # empty list if no events

    def schedule(self, start_time: date=None, end_time: date=None) -> Events:
        """
        Gets schedule for a person. If the schedule is not cached, it will fetch the schedule and cache it.

        Parameters:
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap (Person): person to get overlapping events. If not given, it will get schedule for person_id.

        Returns:
        list: Schedule of the person in json format.
        """
        # if there is an overlap, ignore the cache and fetch the schedule.
        overlap=self.overlap
        if self.get_only_friends:
            overlap=self.current_person
        if overlap.type is not NoOne:
            return self.fetch_schedule(start_time, end_time)
        try:
            evts = self.load_timed_schedule(start_time, end_time)
            if len(evts)==0:
                # fetch the schedule and cache it.
                self.cache_schedule(start_time, end_time)
                evts = self.load_timed_schedule(start_time, end_time)
        except FileNotFoundError:
            self.cache_schedule(start_time, end_time)
            evts = self.load_timed_schedule(start_time, end_time)
        return evts

    # make a call alias for schedule, because it's a main function.
    def __call__(self, start_time: date=None, end_time: date=None) -> Events:
        """
        Alias for schedule function.

        Parameters:
        person (Person): person to get schedule. If not given, it will get schedule for self.current_person.
        start_time (datetime): start time of the schedule. If not given, it will get schedule for today.
        end_time (datetime): end time of the schedule. If not given, it will get schedule for today.
        overlap (Person): person to get overlapping events. If not given, it will get schedule for person_id.
        folder (str): folder to save the cache. If not given, it will save in .cache folder.

        Returns:
        list: Schedule of the person in json format.
        """
        return self.schedule(start_time, end_time)

    @property
    def now(self) -> Event:
        """
        Gets the current event for a person.

        Returns:
        Event: Current event of the person.
        """
        now=moscow.localize(datetime.now())
        evts = self.schedule()  # automatically gets the schedule for today.
        for evt in evts:
            if evt.start_time<=now<=evt.end_time:
                return evt
            

    @property
    def next(self) -> Event:
        # this function will return the next event after the current time, no matter if now is in the event or break.
        now=moscow.localize(datetime.now())
        evts = self.schedule()
        for evt in evts:
            if evt.start_time>now:
                return evt

    @property
    def on_an_event(self) -> bool:
        # get today's schedule
        evts = self.schedule()
        now=moscow.localize(datetime.now())
        for evt in evts:
            if evt.start_time<=now<=evt.end_time:
                return True

    @property
    def on_break(self) -> bool:
        # careful, it must find out if it's a real break and not night or before the first event!
        evts = self.schedule()
        now=moscow.localize(datetime.now())
        for i, evt in enumerate(evts):
            if evt.start_time<=now<=evt.end_time:
                return False
            # from now on, we are on an eventless time. Either break or rest of the day.
            if i==0 and now<evt.start_time:  # before the first event
                return False
            if i==len(evts)-1 and now>evt.end_time:  # after the last event
                return False
        return True  # yess, loop is over and none of the conditions are met.

    @property
    def on_non_working_time(self) -> bool:
        #return not self.on_an_event and not self.on_break  # is it efficient? Probably not.
        # get today's schedule
        evts = self.schedule()
        now=moscow.localize(datetime.now())
        # return true if length is 0
        return len(evts)==0 or now<evts[0].start_time or now>evts[-1].end_time  # one-liner to check if it's a non-working time.

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
        self.results=People.from_big_mess(search_person(term, by_id, self.token)["_embedded"])
        # if we searched with russian letter yo, and no results, then search with e instead.
        if len(self.results)==0 and "ё" in term:
            self.results=People.from_big_mess(search_person(term.replace("ё", "е"), by_id, self.token)["_embedded"])
        return self.results

    def who_goes(self, event: Event) -> People:
        """
        Gets who goes to an event. A list of people bound to the event.

        Parameters:
        event (Event): The event to get who goes.

        Returns:
        People: List of people who goes to the event.
        """
        self.check_token()
        ppl=People.from_who_goes(who_goes(event.event_id, self.token))  # this data doesn't have "_embedded" key
        # we need to get the full data of every teacher, because who_goes doesn't return full data.
        for person in ppl:
            if person.type==Employee:
                person=person.mutate(People.from_big_mess(search_person(person.name, False, self.token)["_embedded"])[0])  # don't search by id, the api returns 500 error if we do that.
        return ppl



#auth=modeus_auth # alias for modeus_auth

def auth(email, password):
    if "@edu.narfu.ru" not in email:  # allow to use the first part of the email
        email+="@edu.narfu.ru"
    try:
        return (modeus_auth(email, password), "")  # empty string means no error and either success or unsuccess confirmed by server.
    except Exception as e:
        return (True, str(e))  # if not empty, then it's an error message.


