# a new, more efficient parser for the schedule. upd. even more efficient, because we use dataclasses and jsons now.
# terms:
# big mess: the big json object that is returned by the server
# prepared data: the data that is returned by the server, but is already parsed

from datetime import datetime, timedelta, date, time
from pytz import timezone
from copy import deepcopy
import json
from dataclasses import dataclass, field

STUDIES = ["08:20", "10:10", "12:00", "14:30", "16:15", "18:00", "19:40"]
moscow=timezone("Europe/Moscow")

#region big mess helper functions
def _get_name(event_id, data):
    """
    Retrieves the name of an event based on its ID from the given data.

    Parameters:
    - event_id (int): The ID of the event to retrieve the name for.
    - data (dict): The data containing the course unit realizations.

    Returns:
    - str or None: The name of the event if found, None otherwise.
    """
    course_unit_realizations = data['course-unit-realizations']
    name = None
    for cur in course_unit_realizations:
        if cur['id'] == event_id:
            name = cur['name']
            break
    return name

def _get_teacher(event_id, data):
    """
    Retrieves the name of the teacher for an event based on its ID from the given data.

    Parameters:
    - event_id (int): The ID of the event to retrieve the teacher for.
    - data (dict): The data from the server.

    Returns:
    - str or None: The name of the teacher if found, None otherwise.
    """
    # works with the big mess
    event_attendees = data['event-attendees']
    event_organizers = data['event-organizers']
    persons = data['persons']
    event_attendeer_id = None
    for organizer in event_organizers:
        if organizer['eventId'] == event_id:
            try:
                event_attendeer_id = organizer['_links']['event-attendees']['href'][1:]
            except TypeError:
                return "Неизвестный"
            break
    assert event_attendeer_id
    person_id = None
    for event_attendeer in event_attendees:
        if event_attendeer['id'] == event_attendeer_id:
            person_id = event_attendeer['_links']['person']['href'][1:]
            break
    for person in persons:
        if person['id'] == person_id:
            full_name = person['fullName']
            return full_name

def _get_room(event_id, data):
    # internal. works with the big mess
    event_locations = data['event-locations']
    event_rooms = data['event-rooms']	
    rooms = data['rooms']
    for event_location in event_locations:
        if event_location['eventId'] == event_id:
            if 'event-rooms' not in event_location['_links']:
                #print("no room")
                return (None, None)

            event_room_id = event_location['_links']['event-rooms']['href'][1:]
            for event_room in event_rooms:
                if event_room['id'] == event_room_id:
                    room_href = event_room['_links']['room']['href']
                    for room in rooms:
                        if room['id'] == room_href[1:]:
                            room_name = room['name']
                            address = room['building']['address'].replace("обл. Архангельская, г. Архангельск, ", "")  # we all know that safu is in arkhangel'sk xD
                            return (room_name, address)

def get_person_info(person_id, data):
    """
    Retrieves the information of a person based on their ID from the given data.

    Parameters:
    - person_id (int): The ID of the person to retrieve the information for.
    - data (dict): The data containing the people information (returned by the server).

    Returns:
    - tuple: The type of the person and their information.
    """
    # big mess to person's info
    if "students" in data:
        person=[per for per in data["students"] if person_id==per["personId"]]  # get the person by id from the students
        if len(person)==0 and "employees" not in data:
            raise ValueError("Json is strange! If you put in the person id right from this json, than json is terribly wrong or corrupted.")  # either students or employees must be in the json
        if len(person)>0:
            return "student", person[0]
        # if len(person)==0, then we need to check the employees
    if "employees" in data:  # further a student can't pass here
        person=[per for per in data["employees"] if person_id==per["personId"]]
        if len(person)==0 and "students" not in data:
            raise ValueError("Json is strange! If you put in the person id right from this json, than json is terribly wrong or corrupted.")
        if len(person)>0:
            return "employee", person[0]  # both can't pass further
    return None, None  # incorrect id


#endregion

def combine_moscow(date, time):  # i am from russia, we are lazy to write this every time xD!
    return moscow.localize(datetime.combine(date, time))

@dataclass
class Event:
    event_id: int
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

    @property
    def start_datetime(self):
        return combine_moscow(self.event_date, self.event_start)

    @property
    def end_datetime(self):
        return combine_moscow(self.event_date, self.event_end)

    def __dict__(self):
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

    def json(self):
        return json.dumps(self.__dict__())

    @classmethod
    def from_prepared(cls, data):
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
    def diffstr(self):
        # +, - or changed fields
        if self.diff==1:
            return "+"
        elif self.diff==-1:
            return "-"
        elif self.diff==2:
            return " ".join(self.changed)
        else:
            return ""

    def get_diff(self, other) -> "Event":
        if self.event_id!=other.event_id:
            return None  # different events
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

    def human_diff(self):
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
    
    def humanize(self):  # alias for __str__
        return str(self)

    def __contains__(self, item):
        return item.lower in str(self).lower()

    def mark_new(self):
        self.diff=1
        return self  # for setting the diff in one line
    
    def mark_removed(self):
        self.diff=-1
        return self
    
    def mark_changed(self, changed_fields):
        self.diff=2
        self.changed=changed_fields
        return self

class Events:  # if this were rust, it would be a trait for Vec<Event>
    def __init__(self, events):
        self.events=events

    #begin magic methods
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
    #end magic methods

    def json(self):
        return json.dumps(self.__list)

    @classmethod
    def from_big_mess(cls, data):
        if "_embedded" in data:
            data=data["_embedded"]
        if "events" not in data:
            return cls([])
        events = data['events']
        parsed_events = []
        for event in Events:
            event_id = event['id']
            event_name = _get_name(event['_links']['course-unit-realization']['href'][1:], data)
            event_start = datetime.fromisoformat(event['start']).time()
            event_end = datetime.fromisoformat(event['end']).time()
            event_date = datetime.fromisoformat(event['start']).replace(hour=0, minute=0).isoformat()
            event_num = STUDIES.index(event_start) + 1
            event_status = event['holdingStatus']['name']
            room_name, address = _get_room(event_id, data)
            teacher = _get_teacher(event_id, data)
            parsed_events.append(Event(event_id, event_num, event_date, event_start, event_end, event_name, teacher, room_name, address, event_status))  # diff is 0 by default




    @classmethod
    def from_prepared_json(cls, data):
        return cls([Event.from_json(event) for event in data])

    @classmethod
    def from_cache(cls, month, person_id):
        #cache/monthnumber.personid.json
        with open(f"cache/{month}.{person_id}.json", "r") as f:
            data=json.load(f)
        return cls.from_prepared_json(data)

    def to_cache(self, month, person_id):
        with open(f"cache/{month}.{person_id}.json", "w") as f:
            json.dump(self.__list__(), f)

    def get_event_by_id(self, event_id):
        event=[event for event in self.events if event.event_id==event_id]
        return event[0] if len(event)>0 else None

    def get_events_by_date(self, date):
        return Events([event for event in self.events if event.event_date==date])

    def get_events_by_num(self, num):
        return Events([event for event in self.events if event.event_num==num]) # usually 1 event, but if different days, then more

    def get_events_between_times(self, start_time=..., end_time=...):
        if start_time==... and end_time==...:
            return deepcopy(self) # return a copy of the object
        if start_time==...:
            return Events([event for event in self.events if event.event_time<=end_time])
        if end_time==...:
            return Events([event for event in self.events if start_time<=event.event_time])
        return Events([event for event in self.events if start_time<=event.event_time<=end_time])

    def get_events_between_dates(self, start_date=..., end_date=...):
        if start_date==... and end_date==...:
            return deepcopy(self)
        if start_date==...:
            return Events([event for event in self.events if event.event_date<=end_date])
        if end_date==...:
            return Events([event for event in self.events if start_date<=event.event_date])
        return Events([event for event in self.events if start_date<=event.event_date<=end_date])


    def get_events_by_name(self, name):
        return Events([event for event in self.events if name.lower() in event.event_name.lower()])

    def get_events_by_teacher(self, teacher):
        return Events([event for event in self.events if teacher.lower() in event.teacher.lower()])

    def get_events_by_room(self, room):
        return Events([event for event in self.events if room.lower() in event.room_name.lower()])

    def get_events_by_status(self, status):
        return Events([event for event in self.events if status.lower() in event.status.lower()])

    # we dont need filter events function, because we can use the methods above

    def diff(self, other):  # self is new, other is old
        # return the difference between two events objects
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
    
    def human_diff(self):  # only for events with diff marks
        return "\n".join([event.human_diff() for event in self.events])
    
    def humanize(self):
        return self.__str__()
    
    def humanize_event(self, event_id):
        event=self.get_event_by_id(event_id)
        return event.humanize()    



# person class will have subclasses Student and Employee. We define Person and then inherit from it
@dataclass
class Person:
    person_id: int
    name: str
    start_date: date|None  # can be omitted in Json for some strange reason.
    end_date: date|None

    def __eq__(self, other):
        return self.person_id==other.person_id

    def __ne__(self, other):
        return self.person_id!=other.person_id

    def __hash__(self):
        return hash(self.person_id)

    @classmethod
    def from_prepared(cls, data):
        # check if data is student or employee
        if data["type"]=="student":
            return Student.from_prepared(data)
        return Employee.from_prepared(data)


        




@dataclass
class Student(Person):
    specialty: str
    profile: str

    def __str__(self):
        msg=f"{self.name}: {self.specialty}, {self.profile}."
        if self.start_date is not None:
            msg+=f" Учится с {self.start_date}"
        if self.end_date is not None:
            msg+=f" по {self.end_date}"
        return msg

    def __repr__(self):
        return self.json()

    def __dict__(self):
        return {
            "id": self.person_id,
            "type": "student",  # to distinguish from employee
            "name": self.name,
            "specialty": self.specialty,
            "profile": self.profile,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }

    def json(self):
        return json.dumps(self.__dict__())

    @classmethod
    def from_prepared(cls, data):  # dont use this method directly, use from_prepared in Person
        return cls(data["id"], data["name"], data["specialty"], data["profile"], date.fromisoformat(data["start_date"]), date.fromisoformat(data["end_date"]))


@dataclass
class Employee(Person):
    group: str

    def __str__(self):
        #return f"{self.name}: {self.group}. Работает с {self.start_date} по {self.end_date}"
        msg=f"{self.name}: {self.group}."
        if self.start_date is not None:
            msg+=f" Работает с {self.start_date}"
        if self.end_date is not None:
            msg+=f" по {self.end_date}"
        return msg

    def __repr__(self):
        return self.json()

    def __dict__(self):
        return {
            "id": self.person_id,
            "name": self.name,
            "type": "employee",
            "group": self.group,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }

    def json(self):
        return json.dumps(self.__dict__())

    @classmethod
    def from_prepared(cls, data):  # dont use this method directly, use from_prepared in Person
        return cls(data["id"], data["name"], data["group"], date.fromisoformat(data["start_date"]), date.fromisoformat(data["end_date"]))

class People:
    def __init__(self, people):
        self.people=people

    #begin magic methods
    def __iter__(self):
        return iter(self.people)

    def __len__(self):
        return len(self.people)

    def __getitem__(self, index):
        return self.people[index]

    def __setitem__(self, index, value):
        self.people[index]=value

    def __delitem__(self, index):
        del self.people[index]

    def __str__(self):  # human readable
        return "\n".join([str(person) for person in self.people])

    def __repr__(self):  # for debugging
        return f"People {self.people}"

    def __contains__(self, item):
        # filter by query. If string, then return bool whether it is in all event strings
        if isinstance(item, str):  # if "Воронцов" in people, it will return True if it is in any person
            return any([item.lower() in person.name.lower() for person in self.people])
        return item in self.people

    def __eq__(self, other):
        return self.people==other.people

    def __ne__(self, other):
        return self.people!=other.people

    def __add__(self, other):
        # add but remove duplicates
        ppl_set=set(self.people+other.people)
        return People(list(ppl_set))

    def __sub__(self, other):
        return People([person for person in self.people if person not in other.people])

    def __list__(self):  # use it to get the list of dictified events
        return [person.__dict__() for person in self.people]
    #end magic methods

    def json(self):
        return json.dumps(self.__list)

    @classmethod
    def from_big_mess(cls, data):
        if "_embedded" in data:  # allow to take full data or just everything inside _embedded
            data=data["_embedded"]
        persons=data['persons'] if 'persons' in data else []
        if len(persons)==0:
            return cls([]) # empty, not NoOne
        parsed_persons=[]
        for person in persons:
            person_id=person['id']
            person_type, person_info=get_person_info(person_id, data)
            if person_type=="student":
                start_date=date.fromisoformat(person_info['learningStartDate'])
                end_date=date.fromisoformat(person_info['learningEndDate'])
                parsed_persons.append(Student(person_id, person['fullName'], start_date, end_date, person_info['specialtyName'], person_info['specialtyProfile']))
            elif person_type=="employee":
                start_date=date.fromisoformat(person_info['dateIn'])
                end_date=date.fromisoformat(person_info['dateOut'])
                parsed_persons.append(Employee(person_id, person['fullName'], start_date, end_date, person_info['groupName']))
        return cls(parsed_persons)



    @classmethod
    def from_prepared_json(cls, data):
        return cls([Person.from_prepared(person) for person in data])

    @classmethod
    def from_cache(cls):
        with open("people.json", "r") as f:
            data=json.load(f)
        return cls.from_prepared_json(data)

    def to_cache(self):
        with open("people.json", "w") as f:
            json.dump(self.__list__(), f)

    def get_person_by_id(self, person_id):
        person=[person for person in self.people if person.person_id==person_id]
        return person[0] if len(person)>0 else None

    def get_person_by_name(self, name):
        return People([person for person in self.people if name.lower() in person.name.lower()])

    def get_students(self):
        return People([person for person in self.people if isinstance(person, Student)])
    
    def get_employees(self):
        return People([person for person in self.people if isinstance(person, Employee)])
    
    def get_students_by_specialty(self, specialty):
        return People([person for person in self.get_students() if specialty.lower() in person.specialty.lower()])
    
    def get_students_by_profile(self, profile):
        return People([person for person in self.get_students() if profile.lower() in person.profile.lower()])
    
    def get_employees_by_group(self, group):
        return People([person for person in self.get_employees() if group.lower() in person.group.lower()])

    def get_people_by_date(self, date):
        return People([person for person in self.people if person.start_date<=date<=person.end_date])  # basically, get all people who are active on this date
    
    # that's all for now. We can add more methods later if needed. What the hell, 1130 lines! Now we remove old functions.


class NoOne(Person):
    # a class that prints warnings in all methods
    def __init__(self):
        self.person_id=0
        self.name="NoOne"
        self.start_date=date.today()
        self.end_date=date.today()

    def __getattr__(self, attr):
        print(f"Warning: NoOne has no attribute {attr}")
        return lambda *args, **kwargs: print(f"Warning: NoOne has no method {attr}")
# yep, our ghost is ready.