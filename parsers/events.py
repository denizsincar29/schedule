from datetime import date, time, datetime
from pytz import timezone
from dataclasses import dataclass, field
from copy import deepcopy
from typing import Self
import mess
import json

STUDIES = ["08:20", "10:10", "12:00", "14:30", "16:15", "18:00", "19:40"]
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
    diff: int=0  # 0- no diff, 1- new, -1- removed, 2- changed
    changed: list=field(default_factory=list)  # list of changed fields

    #region magic methods
    def __eq__(self, other):
        return self.event_id==other.event_id

    def __ne__(self, other):
        return self.event_id!=other.event_id

    def __str__(self):  # human readable in russian
        return f"Пара {self.event_num}: с {self.event_start} до {self.event_end}. {self.event_name}. Преподаватель {self.teacher}. В аудитории: {self.room_name}. По адресу: {self.address}. Статус: {self.status}"

    def __repr__(self):  # for debugging
        return f"Event {self.event_num}: {self.event_name}. Teacher: {self.teacher}. Room: {self.room_name}. Address: {self.address}. Status: {self.status}"

    def __hash__(self):
        return hash(self.event_id)

    def __lt__(self, other):
        # end times will be shifted exactly same as start times, so we can compare only start times
        return self.start_datetime<other.start_datetime

    def __gt__(self, other):
        return self.start_datetime>other.start_datetime
    #endregion

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
            "diff": self.diffstr
        }

    def json(self) -> str:
        """Returns the event as a JSON string."""
        return json.dumps(self.__dict__())

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
        return cls(data["id"], data["event"], edate, estime, eetime, data["name"], data["teacher"], data["room_name"], data["address"], data["status"], diff, changed)

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
        if len(self.changed)==0:
            diff=0
        return Event(self.event_id, self.event_num, self.event_date, self.event_start, self.event_end, self.event_name, self.teacher, self.room_name, self.address, self.status, diff, self.changed)

    def human_diff(self) -> str:
        """Returns the diff as a human-readable string."""
        if self.diff==0:
            return "Изменений нет!"
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
        return msg

    def humanize(self) -> str:
        """Returns the event as a human-readable string."""
        return str(self)

    def __contains__(self, item) -> bool:
        return item.lower in str(self).lower()

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
    def __init__(self, events: list[Event]):
        self.events=events

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
        if len(self.events)==0:
            return "Пар нет!"
        return "\n".join([str(event) for event in self.events])

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
        evt_set=set(self.events+other.events)
        return Events(list(evt_set))

    def __sub__(self, other):
        # return self.events-other.events # we cannot sub lists
        return Events([event for event in self.events if event not in other.events])

    def __list__(self):  # use it to get the list of dictified events
        return [event.__dict__() for event in self.events]
    #endregion

    def json(self) -> str:
        """Returns the events as a JSON string."""
        return json.dumps(self.__list)

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
            event_id = event['id']
            event_name = mess.get_name(event['_links']['course-unit-realization']['href'][1:], data)
            event_start = datetime.fromisoformat(event['start']).time()
            event_end = datetime.fromisoformat(event['end']).time()
            event_date = datetime.fromisoformat(event['start']).replace(hour=0, minute=0).isoformat()
            event_num = STUDIES.index(event_start) + 1
            event_status = event['holdingStatus']['name']
            room_name, address = mess.get_room(event_id, data)
            teacher = mess.get_teacher(event_id, data)
            parsed_events.append(Event(event_id, event_num, event_date, event_start, event_end, event_name, teacher, room_name, address, event_status))  # diff is 0 by default
        return cls(parsed_events)

    @classmethod
    def from_prepared_json(cls, data: dict) -> Self:
        """
        get the events from the prepared json. Used for cache.

        Parameters:
        - data (dict): The prepared data.

        Returns:
        - Events: The collection of events created from the data.
        """
        return cls([Event.from_json(event) for event in data])

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
        #cache/monthnumber.personid.json
        try:
            with open(f"cache/{month}.{person_id}.json", "r") as f:
                data=json.load(f)
        except FileNotFoundError:
            return cls([])
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
        # read from cache to differentiate the events
        old_events=Events.from_cache(month, person_id)  # attention! recursive call
        with open(f"cache/{month}.{person_id}.json", "w") as f:
            json.dump(self.__list__(), f)
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
        return Events([event for event in self.events if event.event_num==num]) # usually 1 event, but if different days, then more

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
        added=[event.mark_new() for event in self.events if event not in other.events]
        removed=[event.mark_removed() for event in other.events if event not in self.events]
        changed=[]
        for event in self.events:
            old_event=other.get_event_by_id(event.event_id)
            if old_event is not None:
                diff=event.get_diff(old_event)  # automatically marks the diff
                if diff is not None:
                    changed.append(diff)
        #events_sorted=
        return Events(added+removed+changed)
    
    def human_diff(self) -> Self:  # only for events with diff marks
        """Returns the diff as a human-readable string."""
        return "\n".join([event.human_diff() for event in self.events])
    
    def humanize(self) -> Self:
        """Returns the events as a human-readable string."""
        return self.__str__()
    
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
