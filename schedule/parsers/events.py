from datetime import date, time, datetime, timedelta
from pytz import timezone
from .russian_date import russian_date
from dataclasses import dataclass, field
from copy import deepcopy
try:
    from typing import Self
except ImportError:
    Self=type("Self", (), {})
from . import mess, people
import json
import icalendar

STUDIES = [time(8, 20), time(10, 10), time(12, 0), time(14, 30), time(16, 15), time(18, 0), time(19, 40)]

def study_to_number(study_time: time) -> int:
    """Converts the study time to the number of the event. Returns -1 if the time is not a study time, which happened only once in the developer's life."""
    return STUDIES.index(study_time)+1 if study_time in STUDIES else -1

moscow=timezone("Europe/Moscow")

def combine_moscow(date, time):  # i am from russia, we are lazy to write this every time xD!
    return moscow.localize(datetime.combine(date, time))

@dataclass
class Event:
    """
    Represents a single event in the schedule.

    Attributes:
    - event_id (str): The unique identifier of the event.
    - event_num (int): The number of the event (e.g. first, second, etc.).
    - event_date (date): The date of the event.
    - event_start (time): The start time of the event.
    - event_end (time): The end time of the event.
    - event_name (str): The name of the event.
    - teacher (str): The name of the teacher for the event.
    - room_name (str): The name of the room where the event takes place.
    - address (str): The address of the room where the event takes place.
    - status (str): The status of the event.
    - format (str): The format of the event.

    Optional Attributes:
    - diff (int): The difference between this event and another event.
    """
    event_id: str
    event_num: int  # first, second, etc.
    event_date: date
    event_start: time
    event_end: time
    event_name: str
    teacher: str
    room_name: str
    address: str
    status: str
    format: str=""
    diff: int=0  # 0- no diff, 1- new, -1- removed, 2- changed
    changed: list=field(default_factory=list)  # list of changed fields

    #region magic methods
    def __eq__(self, other):
        return self.event_id==other.event_id

    def __ne__(self, other):
        return self.event_id!=other.event_id

    def prop_eq(self, other):
        """Compares the properties of this event with another event."""
        return self.event_num==other.event_num and self.event_date==other.event_date and self.event_start==other.event_start and self.event_end==other.event_end and self.event_name==other.event_name and self.teacher==other.teacher and self.room_name==other.room_name and self.address==other.address and self.status==other.status

    def __str__(self):  # human readable in russian
        return self.humanize()  # i will rewrite humanize method to return the string
    def __repr__(self):  # for debugging
        return f"Event {self.event_num}: {self.event_name}. Teacher: {self.teacher}. Room: {self.room_name}. Address: {self.address}. Status: {self.status}, Diff: {self.diff}, Changed: {self.changed}"

    def __hash__(self):
        return hash(self.event_id)

    def __lt__(self, other):
        # end times will be shifted exactly same as start times, so we can compare only start times
        return self.start_datetime<other.start_datetime

    def __gt__(self, other):
        return self.start_datetime>other.start_datetime
    #endregion

    def pprint(self) -> str:
        """Prints the event in a human-readable format."""
        print(self.__str__())
        return self.__str__()


    @property
    def start_datetime(self) -> datetime:
        """
        Returns the start datetime of the event.

        Returns:
        - datetime: The start datetime of the event.
        """
        return combine_moscow(self.event_date, self.event_start)

    @property
    def end_datetime(self) -> datetime:
        """
        Returns the end datetime of the event.

        Returns:
        - datetime: The end datetime of the event.
        """
        return combine_moscow(self.event_date, self.event_end)

    def __dict__(self) -> dict:
        """
        Returns the event as a dictionary.
        
        Returns:
        - dict: The event as a dictionary.
        """
        return {
            "id": self.event_id,
            "event": self.event_num,
            "date": self.event_date.isoformat(),
            "start_time": self.event_start.isoformat(),
            "end_time": self.event_end.isoformat(),
            "name": self.event_name,
            "teacher": self.teacher,
            "room_name": self.room_name,
            "address": self.address,
            "status": self.status,
            "format": self.format,
            "diff": self.diffstr
        }

    def json(self) -> str:
        """Returns the event as a JSON string."""
        return json.dumps(self.__dict__(), ensure_ascii=False)  # it makes huge unicode escape sequences if not set to False

    @classmethod
    def from_prepared(cls, data: dict) -> Self:
        """
        Creates an event from the prepared data.

        Parameters:
        - data (dict): The prepared data for the event.

        Returns:
        - Event: The event created from the data.
        """
        diff=0
        changed=[]
        if data["diff"]=="-":
            diff=-1
        elif data["diff"]=="+":
            diff=1
        else:
            diff=2
            changed=data["diff"].split()
        edate=date.fromisoformat(data["date"])
        estime=time.fromisoformat(data["start_time"])
        eetime=time.fromisoformat(data["end_time"])
        # if there is no format, then old cache is used. But soon the app will get new cache with format
        format=data["format"] if "format" in data else ""
        return cls(data["id"], data["event"], edate, estime, eetime, data["name"], data["teacher"], data["room_name"], data["address"], data["status"], format, diff, changed)

    @property
    def diffstr(self) -> str:
        """Returns the diff as a string."""
        if self.diff==1:
            return "+"
        elif self.diff==-1:
            return "-"
        elif self.diff==2:
            return " ".join(self.changed)
        else:
            return ""

    def get_diff(self, other) -> Self:
        """
        Returns the difference between this event and another event.

        Parameters:
        - other (Event): The old event to compare with.

        Returns:
        - Event|None: The difference between the two events. e.g. events list with diff marks.
        """
        if self.event_id!=other.event_id:
            return None
        # if ids are equal, then check all fields
        diff=2
        if self.event_start != other.event_start:  # we can omit checking the event num, because it dependends on the start time
            self.changed.append("start_time")  # append like json key.
        if self.event_end != other.event_end:
            self.changed.append("end_time")
        if self.event_date!=other.event_date:
            self.changed.append("date")
        if self.event_name!=other.event_name:
            self.changed.append("name")
        if self.teacher!=other.teacher:
            self.changed.append("teacher")
        if self.room_name!=other.room_name:
            self.changed.append("room_name")
        if self.address!=other.address:
            self.changed.append("address")
        if self.status!=other.status:
            self.changed.append("status")
        if self.format!=other.format:
            self.changed.append("format")
        if len(self.changed)==0:
            diff=0
        return Event(self.event_id, self.event_num, self.event_date, self.event_start, self.event_end, self.event_name, self.teacher, self.room_name, self.address, self.status, diff, self.changed)

    def human_diff(self) -> str:
        """Returns the diff as a human-readable string."""
        if self.diff==0:
            return ""  # to avoid printing "Изменений нет" million times for each event
        msg=""
        if self.diff==1:
            msg+=f"Новая пара {self.event_num}: с {self.event_start} до {self.event_end}. {self.event_name}. Преподаватель {self.teacher}. В аудитории: {self.room_name}. По адресу: {self.address}. Статус: {self.status}"
        elif self.diff==-1:
            msg+=f"Снята пара {self.event_num}: {self.event_name}. Преподаватель {self.teacher}. В аудитории: {self.room_name}. По адресу: {self.address}. Статус: {self.status}"
        else:
            msg+=f"Изменена пара {self.event_num}: с {self.event_start} до {self.event_end}. {self.event_name}. Преподаватель {self.teacher}. В аудитории: {self.room_name}. По адресу: {self.address}. Статус: {self.status}"
            for field in self.changed:
                if field=="start_time":
                    msg+=f"Изменено время начала пары на {self.event_start}"
                elif field=="end_time":
                    msg+=f"Изменено время окончания пары на {self.event_end}"
                elif field=="date":
                    msg+=f"Изменена дата пары на {self.event_date}"
                elif field=="name":
                    msg+=f"Изменено название пары на {self.event_name}"
                elif field=="teacher":
                    msg+=f"Изменен преподаватель на {self.teacher}"
                elif field=="room_name":
                    msg+=f"Изменена аудитория на {self.room_name}"
                elif field=="address":
                    msg+=f"Изменен адрес аудитории на {self.address}"
                elif field=="status":
                    msg+=f"Изменен статус на {self.status}"
                elif field=="format":
                    msg+=f"Изменен формат проведения на {self.format}"
        return msg

    def humanize(self, event_times=True) -> str:
        """
        Returns the event as a human-readable string.

        Parameters:
        - event_times (bool): Whether to include the event times in the string.
        """
        event_num_str=f"Пара {self.event_num}" if self.event_num>0 else "Событие"
        if "online" in self.address:
            addrmsg=f"Проходит онлайн:\n{self.room_name}"
        elif "online" in self.room_name:
            addrmsg=f"Проходит онлайн:\n{self.address}"
        else:
            addrmsg=f"В аудитории: {self.room_name}. По адресу: {self.address}."  # if both are not online, then print both
        evtmsg=f"с {self.event_start:%H:%M} до {self.event_end:%H:%M}. " if event_times or self.event_num<=0 else ""  # if it is not a study event, then even if event_times is False, we will show the times because it's not obvious
        return f"{event_num_str}: {evtmsg}{self.format}, {self.event_name}. Преподаватель {self.teacher}. {addrmsg}."


    def __contains__(self, item) -> bool:
        return item.lower() in str(self).lower()

    def mark_new(self) -> Self:
        """Marks the event as new. Places a new diff mark and returns the event for chaining"""
        self.diff=1
        return self  # for setting the diff in one line

    def mark_removed(self) -> Self:
        """Marks the event as removed. Places a removed diff mark and returns the event for chaining"""
        self.diff=-1
        return self

    def mark_changed(self, changed_fields) -> Self:
        """
        Marks the event as changed. Places a changed diff mark and returns the event for chaining.

        Parameters:
        - changed_fields (list): The list of fields that have been changed.

        Returns:
        - Event: The event with the changed diff mark.
        """
        self.diff=2
        self.changed=changed_fields
        return self


class Events:  # if this were rust, it would be a trait for Vec<Event>
    """A collection of events. Supports all list methods and some additional methods for filtering and diffing."""
    def __init__(self, events: list[Event]=[]):
        self.events=events
        self.tokens=[]  # for tokenizing the events

    #region magic methods
    def __iter__(self):
        return iter(self.events)

    def __len__(self):
        return len(self.events)

    def __getitem__(self, index):
        return self.events[index]

    def __setitem__(self, index, value):
        self.events[index]=value

    def __delitem__(self, index):
        del self.events[index]

    def __str__(self):  # human readable
        return self.humanize()
    def __repr__(self):  # for debugging
        return f"Events {self.events}"

    def __contains__(self, item):
        # filter by query. If string, then return bool whether it is in all event strings
        if isinstance(item, str):  # if "Воронцов" in events, it will return True if it is in any event
            return any([item in event for event in self.events])
        return item in self.events

    def __eq__(self, other):
        return self.events==other.events

    def __ne__(self, other):
        return self.events!=other.events


    def __add__(self, other):
        # add but remove duplicates
        # use prop eq to check duplicates
        evt_list = self.events.copy()  # deepcopy is not working here
        for event in other.events:
            for el in evt_list:
                if event.prop_eq(el):
                    break
            else:
                evt_list.append(event)
        return Events(evt_list)


    def __sub__(self, other):
        # return self.events-other.events # we cannot sub lists
        return Events([event for event in self.events if event not in other.events])

    def __list__(self):  # use it to get the list of dictified events
        return [event.__dict__() for event in self.events]
    #endregion

    def ics(self) -> str:
        """Returns the events as an iCalendar string."""
        cal=icalendar.Calendar()
        cal.add('prodid', '-//NARFUSchedule//deniz.r1oaz.ru//')
        cal.add('version', '2.0')
        prev_date=date(2020, 1, 1)  # for making alarm yesterday with the whole day
        for event in self.events:
            if event.event_date!=prev_date:
                prev_date=event.event_date
                day_event=icalendar.Event()
                day_event.add('uid', f"{event.event_date}-day")
                whole_day_schedule = self.get_events_by_date(event.event_date).humanize()  # get the whole day schedule
                day_event.add('summary', f"Расписание на {russian_date(event.event_date)}")
                day_event.add('description', whole_day_schedule)
                day_event.add('dtstart', combine_moscow(event.event_date, time(8, 20)))
                day_event.add('dtend', combine_moscow(event.event_date, time(21, 0)))
                day_event.add('dtstamp', moscow.localize(datetime.now()))
                day_alarm=icalendar.Alarm()
                day_alarm.add('action', 'display')
                day_alarm.add('description', f'Расписание на завтра:\n{whole_day_schedule}')
                day_alarm.add('trigger', timedelta(hours=-14, minutes=-20))  # yesterday at 18:00
                day_event.add_component(day_alarm)
                cal.add_component(day_event)
            ical_event=icalendar.Event()
            ical_event.add('uid', event.event_id)
            ical_event.add('summary', f"{event.format}, {event.event_name}")
            ical_event.add('dtstart', event.start_datetime)
            ical_event.add('dtend', event.end_datetime)
            ical_event.add('location', f"{event.room_name}, {event.address}")
            ical_event.add('description', f"Преподаватель: {event.teacher}.")
            ical_event.add('dtstamp', moscow.localize(datetime.now()))
            alarm=icalendar.Alarm()
            alarm.add('action', 'display')
            alarm.add('description', 'Скоро начнется пара! Подготовьтесь!')
            alarm.add('trigger', timedelta(minutes=-15))
            ical_event.add_component(alarm)
            cal.add_component(ical_event)
        return cal.to_ical().decode("utf-8")

    def tokenize(self) -> list[tuple[Event, int]]:
        """Tokenizes the events for highlighting in the text field."""
        if len(self.tokens)==0:
            str(self)  # dummy call to fill the tokens
        return self.tokens

    def get_event_by_strindex(self, index: int) -> Event:  # making this for getting event by highliting the event in the text field
        """returns the event by the index of the human-readable string."""
        evt= [event for event, start in self.tokenize() if start<=index<(start+len(str(event)))]
        return evt[0] if len(evt)>0 else None


    def pprint(self, person: people.Person=people.noone) -> str:
        """
        Prints the events in a human-readable format.

        Parameters:
        - person (Person): The person to print the events for.

        Returns:
        - str: The events in a human-readable format.
        """
        print(f"Расписание {person.name}:" if person!=people.noone else "Расписание:")  # great if we would have genitive case for names.
        print(self.__str__())
        return self.__str__()


    def json(self) -> str:
        """Returns the events as a JSON string."""
        # we need to convert the events to dict first
        return json.dumps([event.__dict__() for event in self.events], ensure_ascii=False)  # yep, else you got json encode error

    @classmethod
    def from_big_mess(cls, data: dict) -> Self:
        """
        Creates a collection of events from the json that is returned by the server.

        Parameters:
        - data (dict): The data from the server.

        Returns:
        - Events: The collection of events created from the data.
        """
        if "_embedded" in data:
            data=data["_embedded"]
        if "events" not in data:
            return cls([])
        parsed_events = []
        events = data['events']
        for event in events:
            #print(event)
            event_id = event['id']
            event_name = mess.get_name(event['_links']['course-unit-realization']['href'][1:], data) if 'course-unit-realization' in event['_links'] else event["name"]+", "+event["nameShort"]
            event_format = mess.get_type_and_format_name(event_id, data)
            event_start = datetime.fromisoformat(event['start']).time()
            event_end = datetime.fromisoformat(event['end']).time()
            event_date = datetime.fromisoformat(event['start']).date()
            event_num = study_to_number(event_start)
            event_status = event['holdingStatus']['name']
            room_name, address = mess.get_room(event_id, data)
            teacher = mess.get_teacher(event_id, data)
            parsed_events.append(Event(event_id, event_num, event_date, event_start, event_end, event_name, teacher, room_name, address, event_status, event_format))
        return cls(sorted(parsed_events))

    @classmethod
    def from_prepared_json(cls, data: dict) -> Self:
        """
        get the events from the prepared json. Used for cache.

        Parameters:
        - data (dict): The prepared data.

        Returns:
        - Events: The collection of events created from the data.
        """
        return cls(sorted(Event.from_prepared(event) for event in data))

    @classmethod
    def from_cache(cls, month: int, person_id: str) -> Self:
        """
        get the events from the cache.

        Parameters:
        - month (int): The month number.
        - person_id (str): The person's id.

        Returns:
        - Events: The collection of events created from the cache.
        """
        try:
            with open(f"cache/{month}.{person_id}.json", "r", encoding="UTF-8") as f:
                data=json.load(f)
        except FileNotFoundError:
            return cls([], True)  # we have empty cache
        return cls.from_prepared_json(data)

    def to_cache(self, month: int, person_id: str) -> Self:
        """
        put the events to the cache.

        Parameters:
        - month (int): The month number.
        - person_id (str): The person's id.

        Returns:
        - Events: The collection of events representing difference between the old and new events.
        """
        if month==-1:
            month=date.today().month  # we can save to the current month
        # read from cache to differentiate the events
        old_events=Events.from_cache(month, person_id)  # attention! recursive call
        with open(f"cache/{month}.{person_id}.json", "w", encoding="UTF-8") as f:
            json.dump(self.__list__(), f, ensure_ascii=False)
        return self.diff(old_events)


    def get_event_by_id(self, event_id: str) -> Event:
        """
        Returns the event with the given ID.

        Parameters:
        - event_id (str): The ID of the event to retrieve.

        Returns:
        - Event: The event with the given ID.
        """
        event=[event for event in self.events if event.event_id==event_id]
        return event[0] if len(event)>0 else None

    def get_events_by_date(self, date: date) -> Self:
        """
        Returns the events for the given date.

        Parameters:
        - date (date): The date to retrieve the events for.

        Returns:
        - Events: The events for the given date.
        """
        return Events([event for event in self.events if event.event_date==date])

    def get_events_by_num(self, num):
        """
        Returns the events for the given number.

        Parameters:
        - num (int): The number of the event to retrieve. e.g. the one starting at 8:20 is first, etc.

        Returns:
        - Events: The events for the given number.
        """
        return Events([event for event in self.events if event.event_num==num])

    def get_events_between_times(self, start_time: time=..., end_time: time=...) -> Self:
        """
        Returns the events between the given start and end times.

        Parameters:
        - start_time (time): The start time to filter the events by.
        - end_time (time): The end time to filter the events by.

        Returns:
        - Events: The events between the given start and end times.
        """
        if start_time==... and end_time==...:
            return deepcopy(self) # return a copy of the object
        if start_time==...:
            return Events([event for event in self.events if event.event_time<=end_time])
        if end_time==...:
            return Events([event for event in self.events if start_time<=event.event_time])
        return Events([event for event in self.events if start_time<=event.event_time<=end_time])

    def get_events_between_dates(self, start_date: date=..., end_date: date=...) -> Self:
        """
        Returns the events between the given start and end dates.

        Parameters:
        - start_date (date): The start date to filter the events by.
        - end_date (date): The end date to filter the events by.

        Returns:
        - Events: The events between the given start and end dates.
        """
        if start_date==... and end_date==...:
            return deepcopy(self)
        if start_date==...:
            return Events([event for event in self.events if event.event_date<=end_date])
        if end_date==...:
            return Events([event for event in self.events if start_date<=event.event_date])
        return Events([event for event in self.events if start_date<=event.event_date<=end_date])


    def get_events_by_name(self, name: str) -> Self:
        """
        Returns the events with the given name.

        Parameters:
        - name (str): The name to filter the events by.

        Returns:
        - Events: The events with the given name.
        """
        return Events([event for event in self.events if name.lower() in event.event_name.lower()])

    def get_events_by_teacher(self, teacher: str) -> Self:
        """
        Returns the events with the given teacher.

        Parameters:
        - teacher (str): The teacher to filter the events by.

        Returns:
        - Events: The events with the given teacher.
        """
        return Events([event for event in self.events if teacher.lower() in event.teacher.lower()])

    def get_events_by_room(self, room: str) -> Self:
        """
        Returns the events with the given room.

        Parameters:
        - room (str): The room to filter the events by.

        Returns:
        - Events: The events with the given room.
        """
        return Events([event for event in self.events if room.lower() in event.room_name.lower()])

    def get_events_by_status(self, status: str) -> Self:
        """
        Returns the events with the given status.

        Parameters:
        - status (str): The status to filter the events by.

        Returns:
        - Events: The events with the given status.
        """
        return Events([event for event in self.events if status.lower() in event.status.lower()])

    def get_events_by_query(self, query: str) -> Self:
        """
        Returns the events that match the given query.

        Parameters:
        - query (str): The query to filter the events by.

        Returns:
        - Events: The events that match the given query.
        """
        return Events([event for event in self.events if query.lower() in str(event).lower()])  # what? was it that easy? I thaught we'd check each field!

    def overlap(self, other: Self) -> Self:
        """
        Returns the overlap between this collection of events and another collection of events.

        Parameters:
        - other (Events): The other collection of events to compare with.

        Returns:
        - Events: The overlap between the two collections of events.
        """
        return Events([event for event in self.events if event in other.events])


    def diff(self, other: Self) -> Self:
        """
        Returns the difference between this collection of events and another collection of events.

        Parameters:
        - other (Events): The other collection of events to compare with.

        Returns:
        - Events: The difference between the two collections of events with diff marks.
        """
        if len(other)==0:
            return Events([])  # well, if there was empty cache, then all events seemed new but they are not
        added=[event.mark_new() for event in self.events if event not in other.events]
        removed=[event.mark_removed() for event in other.events if event not in self.events]
        changed=[]
        for event in self.events:
            old_event=other.get_event_by_id(event.event_id)
            if old_event is not None:
                diff=event.get_diff(old_event)  # automatically marks the diff
                if diff is not None and diff.diff==2:
                    changed.append(diff)
        return Events(sorted(added+removed+changed))  # the < operator overloaded by start time

    def human_diff(self) -> str:
        """Returns the diff as a human-readable string."""
        return "\n".join([hdiff for event in self.events if (hdiff:=event.human_diff())!=""])

    def pprint_diff(self) -> str:
        """Prints the diff in a human-readable format if there are."""
        if len(self)>0:
            print("Изменения в расписании:")
            print(self.human_diff())
            return self.human_diff()
        return "" # to avoid printing "Изменений нет" million times for each event

    def humanize(self, event_times: bool=True) -> Self:
        """
        Returns the events as a human-readable string.

        Parameters:
        - event_times (bool): Whether to include the event times in the string.
        """
        if len(self.events)==0:
            self.tokens=[]
            return "Пар нет!"
        msg=""
        prev_date=date(2020, 1, 1)# to instantly print the first date
        double_evt=False
        for i, event in enumerate(self.events):
            if double_evt:
                double_evt=False
                continue
            if event.event_date!=prev_date:
                msg+=f"\n{russian_date(event.event_date)}:"
                prev_date=event.event_date
            self.tokens.append((event, len(msg)))
            # if next event is in the same day but the same room, name and teacher, we can write "2 пары" or even "3 пары"
            if i+1<len(self.events) and self.events[i+1].event_date==event.event_date and self.events[i+1].room_name==event.room_name and self.events[i+1].event_name==event.event_name and self.events[i+1].teacher==event.teacher:
                #msg+=f"\nДвойная пара: пары {event.event_num} и {self.events[i+1].event_num}. {event.format}, {event.event_name}. Преподаватель {event.teacher}. В аудитории: {event.room_name}. По адресу: {event.address}." still check the onlinity
                addrmsg=f"Проходит онлайн:\n{event.room_name}" if "online" in event.address else f"В аудитории: {event.room_name}. По адресу: {event.address}."  # if both are not online, then print both
                msg+=f"\nДвойная пара: пары {event.event_num} и {self.events[i+1].event_num}. {event.format}, {event.event_name}. Преподаватель {event.teacher}. {addrmsg}"

                double_evt=True  # skip the next event because we have already written it
                continue
            msg+=f"\n{event.humanize(event_times)}"
        return msg.strip()


    def humanize_event(self, event_id: str) -> str:
        """
        Returns the event as a human-readable string.

        Parameters:
        - event_id (str): The ID of the event to retrieve.

        Returns:
        - str: The event as a human-readable string.
        """
        event=self.get_event_by_id(event_id)
        return event.humanize()    
