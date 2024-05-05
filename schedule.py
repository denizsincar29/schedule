from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from modeus import modeus_parse_token, get_schedule, search_person, who_goes

from pytz import timezone
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



# main function inside the main.py