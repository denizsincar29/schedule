# a new, more efficient parser for the schedule
# terms:
# big mess: the big json object that is returned by the server
# prepared data: the data that is returned by the server, but is already parsed

from datetime import datetime
from copy import deepcopy

STUDIES = ["08:20", "10:10", "12:00", "14:30", "16:15", "18:00", "19:40"]

def get_name(event_id, data):
    course_unit_realizations=data['course-unit-realizations']
    name=None
    for cur in course_unit_realizations:
        if cur['id']==event_id:
            name=cur['name']
            break
    return name



def get_teacher(event_id, data):
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

def get_room(event_id, data):
    # works with the big mess
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


def parse_bigjson(data):
    # transforms the big mess into prepared data
    # normally data is value of _embedded key, but if not, then set data=data["_embedded"]
    if "_embedded" in data:
        data = data["_embedded"]
    events = data['events']
    parsed_events = []
    
    for event in events:
        event_id = event['id']
        event_name = get_name(event['_links']['course-unit-realization']['href'][1:], data)
        event_start = datetime.fromisoformat(event['start']).strftime("%H:%M")
        event_end = datetime.fromisoformat(event['end']).strftime("%H:%M")
        event_date = datetime.fromisoformat(event['start']).replace(hour=0, minute=0).isoformat()
        event_time = STUDIES.index(event_start) + 1
        event_status = event['holdingStatus']['name']
        room_name, address = get_room(event_id, data)
        teacher = get_teacher(event_id, data)
        # datetime object is not JSON serializable
        event_data = {
            "id": event_id,  # unique identifier
            "event": event_time,
            "date": event_date,  # sometimes needed for quick filtering
            "start_time": event_start,
            "end_time": event_end,
            "name": event_name,
            "teacher": teacher,
            "room_name": room_name,
            "address": address,
            "status": event_status,
            "diff": "+"  # used for diffing. "+"- new, "-"- removed, ""- no diff, other string: space separated list of fields that are different
        }
        
        parsed_events.append(event_data)
    # sort the events by date and time
    parsed_events = sorted(parsed_events, key=lambda x: (datetime.fromisoformat(x['date']), x['event']))
    return parsed_events


def filter_events(data, date=None, delta=None, start_time=None, end_time=None, evt_num=None, evt_name_query=None, teacher_query=None, room_query=None, status=None):  # all kwargs are optional
    # filters the prepared data
    if isinstance(data, dict):
        raise ValueError("Hey, you passed the full schedule json, not events list!")
    filtered_data = []
    for event in data:
        # get all dates into datetime objects, start and end time into datetime date+start_time, date+end_time
        event_date = datetime.fromisoformat(event['date'])
        evt_st=start_time.split(":") if start_time is not None else [0, 0]
        evt_et=end_time.split(":") if end_time is not None else [23, 59]
        event_start_time = event_date.replace(hour=int(evt_st[0]), minute=int(evt_st[1]))  # if raises, it's other function's fault
        event_end_time = event_date.replace(hour=int(evt_et[0]), minute=int(evt_et[1]))
        # if event between date and date+delta
        if date is not None and delta is not None:
            if event_date < date or event_date > date + delta:
                continue
        if date is not None and delta is None and event_date != date:  # now if no delta, then only date
            continue
        if start_time is not None and event_start_time < start_time:
            continue
        if end_time is not None and event_end_time > end_time:
            continue
        if evt_num is not None and event['event'] != evt_num:
            continue
        if evt_name_query is not None and evt_name_query.lower() not in event['name'].lower():
            continue
        if teacher_query is not None and teacher_query.lower() not in event['teacher'].lower():
            continue
        if room_query is not None and room_query.lower() not in event['room_name'].lower():
            continue
        if status is not None and status.lower() not in event['status'].lower():
            continue
        filtered_data.append(event)  # passed all filters
    return filtered_data

# lets remake the old human readable parser (from parse.py)
MSGS={
    "no_events": {
        False: "На этот промежуток времени пар нет!",
        True: "Пар нет!"  # laconic
    },
    "no_diff": {
        False: "Изменений нет!",
        True: "Изменений нет!"  # laconic
    },
    "no_events_multiday": {
        False: "В эти дни пар нет!",
        True: "В эти дни пар нет!"  # laconic
    },
    "online": {
        False: "Проходит онлайн на сайте сафу",
        True: "онлайн"
    },
    "in_room": {
        False: "Проходит в аудитории: {room_name}. По адресу: {address}",
        True: "в аудитории: {room_name}"
    }
}

def get_event_by_id(event_id, data):
    # returns the event by its id
    for event in data:
        if event['id'] == event_id:  # it's modeus's resp that the id is unique xD
            return event
    return None


def humanize_event_id(event_id, data, laconic=False):
    # parsing from the prepared data
    event = get_event_by_id(event_id, data)
    if event is None:
        return "Не найдено. Обратитесь к криворукому программисту."  # xDDDDDDDDDD
    if laconic:
        msg=f"Пара {event['event']}: {event['name']}. Преподаватель {event['teacher']}. {MSGS['in_room'][laconic].format(room_name=event['room_name']) if event['room_name'] is not None else MSGS['online'][laconic]}"
    else:
        # пара 1: с 08:20 до 10:00. Математический анализ. Преподаватель Иванов И.И. Проходит в аудитории: 101. По адресу: ул. Ленина, 1
        msg=f"Пара {event['event']}: с {event['start_time']} до {event['end_time']}. {event['name']}. Преподаватель {event['teacher']}. {MSGS['in_room'][laconic].format(room_name=event['room_name'], address=event['address']) if event['room_name'] is not None else MSGS['online'][laconic]}"
    return msg

def multiday(events):
    # return all dates of the events by set comprehension
    dates={event['date'] for event in events}
    return dates

def humanize_events(events, laconic=False):
    # parsing from the prepared data
    if len(events) == 0:
        return MSGS['no_events'][laconic]
    msg=""
    multi=len(multiday(events))>1
    # if day changes or first event in multiday, msg+=date, but separated by \n\n
    prevdate=None
    for event in events:
        if multi:
            if prevdate is None:
                prevdate=event['date']
            elif prevdate!=event['date']:
                msg+='\n\n'
                prevdate=event['date']
            msg+=f"{datetime.fromisoformat(event['date']).strftime('%d/%m')}: "
        msg+=humanize_event_id(event['id'], events, laconic)+'\n'
    return msg

def parse_people(data):
    # big mess to prepared data
    #students=data['students'] if 'students' in data else []  # there can be no students or employees
    #employees=data['employees'] if 'employees' in data else []
    persons=data['persons'] if 'persons' in data else []
    if len(persons)==0:
        return []
    parsed_persons=[]
    for person in persons:
        person_id=person['id']
        person_type, person_info=get_person_info(person_id, data)
        # if person_type is None, then the developer messed up with everything xD
        if person_type is None:
            raise ValueError("Json is strange! If you put in the person id right from this json, than json is terribly wrong or corrupted.")
        if person_type=="student":
            specialty=person_info['specialtyName']
            profile=person_info['specialtyProfile']
            start_date=person_info['learningStartDate']
            end_date=person_info['learningEndDate']
            parsed_persons.append({
                "id": person_id,
                "type": "student",
                "name": person['fullName'],
                "specialty": specialty,
                "profile": profile,
                "start_date": start_date,
                "end_date": end_date
            })
        elif person_type=="employee":
            group=person_info['groupName']
            date_in=person_info['dateIn']
            date_out=person_info['dateOut']
            parsed_persons.append({
                "id": person_id,
                "type": "employee",
                "name": person['fullName'],
                "group": group,
                "date_in": date_in,
                "date_out": date_out
            })
    return parsed_persons  # oh my god, i forgot to return the parsed persons and got many NoneType errors


def get_person_info(person_id, data):
    # big mess to person's info
    if "students" in data:
        person=[per for per in data["students"] if person_id==per["personId"]]  # get the person by id from the students
        if len(person)==0 and "employees" not in data: raise ValueError("Json is strange! If you put in the person id right from this json, than json is terribly wrong or corrupted.")  # either students or employees must be in the json
        if len(person)>0: return "student", person[0]
        # if len(person)==0, then we need to check the employees
    if "employees" in data:  # further a student can't pass here
        person=[per for per in data["employees"] if person_id==per["personId"]]
        if len(person)==0 and "students" not in data: raise ValueError("Json is strange! If you put in the person id right from this json, than json is terribly wrong or corrupted.")
        if len(person)>0: return "employee", person[0]  # both can't pass further
    return None, None  # incorrect id


def get_person_by_id(person_id, data):
    # returns the person by its id
    for person in data:
        if person['id'] == person_id:
            return person
    return None


def humanize_person(person_id, data):
    # works with the prepared data
    person = get_person_by_id(person_id, data)
    if person is None:
        return ""
    if person['type'] == "student":
        msg=f"{person['name']}: {person['specialty']}, {person['profile']}."
        if person['start_date'] is not None:
            msg+=f" Учится с {datetime.fromisoformat(person['start_date']).strftime('%d/%m/%Y')}"
        if person['end_date'] is not None:
            msg+=f" по {datetime.fromisoformat(person['end_date']).strftime('%d/%m/%Y')}."
        else:
            msg+="."
    elif person['type'] == "employee":
        msg=f"{person['name']}: {person['group']}."
        if person['date_in'] is not None:
            msg+=f" Работает с {datetime.fromisoformat(person['date_in']).strftime('%d/%m/%Y')}"
        if person['date_out'] is not None:
            msg+=f" по {datetime.fromisoformat(person['date_out']).strftime('%d/%m/%Y')}."
        else:
            msg+="."
    return msg


def events_equality(event1, event2):
    # if ids are not equal, []. If ids are equal but some fields are not, then return the fields that are not equal. If all fields are equal, then return ...
    if event1==event2:
        return ...  # dotdotdot!
    if event1['id']!=event2['id']:
        return []
    diff=[]
    if event1['event']!=event2['event']:
        diff.append("event")
    if event1['date']!=event2['date']:
        diff.append("date")
    if event1['start_time']!=event2['start_time']:
        diff.append("start_time")
    if event1['end_time']!=event2['end_time']:
        diff.append("end_time")
    if event1['name']!=event2['name']:
        diff.append("name")
    if event1['teacher']!=event2['teacher']:
        diff.append("teacher")
    if event1['room_name']!=event2['room_name']:
        diff.append("room_name")
    if event1['address']!=event2['address']:
        diff.append("address")
    if event1['status']!=event2['status']:
        diff.append("status")
    return diff


def diff(old, new):
    # returns the difference between two lists of events in the prepared data format with the diff key. Return only added, removed and changed events
    old=deepcopy(old)
    new=deepcopy(new)
    events=[]
    # get all ids
    ids_old={event['id'] for event in old}
    ids_new={event['id'] for event in new}
    # get added and removed
    added_ids=ids_new-ids_old
    removed_ids=ids_old-ids_new
    # append the events with the diff key
    for event in added_ids:
        event=get_event_by_id(event, new)
        event['diff']="+"
        events.append(event)
    for event in removed_ids:
        event=get_event_by_id(event, old)
        event['diff']="-"
        events.append(event)
    # get changed events
    for event in ids_old.intersection(ids_new):
        event1=get_event_by_id(event, old)
        event2=get_event_by_id(event, new)
        diff=events_equality(event1, event2)
        if diff!=... and diff!=[]:  # empty list is no diff, dotdotdot is all fields are equal
            event2['diff']=" ".join(diff)
            events.append(event2)
    return events

def human_diff(diff, date=None, delta=None, ifnodiff=False):
    # returns a human readable diff
    if len(diff)==0:
        if ifnodiff: return MSGS['no_diff'][True]
        else: return ""  # normally we ssend notification only if there is a diff
    msg=""
    multi=len(multiday(diff))>1
    # if day changes or first event in multiday, msg+=date, but separated by \n\n
    prevdate=None
    for event in diff:
        if multi:
            if prevdate is None:
                prevdate=event['date']
            elif prevdate!=event['date']:
                msg+='\n\n'
                prevdate=event['date']
            msg+=f"{datetime.fromisoformat(event['date']).strftime('%d/%m')}: "
        if event['diff']=="+":
            msg+=f"Новая пара {event['event']}: с {event['start_time']} до {event['end_time']}. {event['name']}. Преподаватель {event['teacher']}. {MSGS['in_room'][False].format(room_name=event['room_name'], address=event['address']) if event['room_name'] is not None else MSGS['online'][False]}\n"
        elif event['diff']=="-":
            msg+=f"Снята пара {event['event']}: {event['name']} с Преподавателем {event['teacher']}. {MSGS['in_room'][True].format(room_name=event['room_name'], address=event['address']) if event['room_name'] is not None else MSGS['online'][True]}\n"  # if event removed, then no need to show full info.
        else:
            # if only status changed, then no need to show it
            if event['diff']=="status":
                continue # we're done here
            msg+=f"Изменена пара {event['event']}: с {event['start_time']} до {event['end_time']}. {event['name']}. Преподаватель {event['teacher']}. {MSGS['in_room'][False].format(room_name=event['room_name'], address=event['address']) if event['room_name'] is not None else MSGS['online'][False]}\n"
            # изменился e.g. преподаватель, аудитория
            for field in event['diff'].split():
                if field=="event":
                    msg+=f"Изменено время пары с {event['start_time']} до {event['end_time']}\n"
                elif field=="date":
                    msg+=f"Изменена дата пары на {datetime.fromisoformat(event['date']).strftime('%d/%m')}\n"
                elif field=="start_time":
                    msg+=f"Изменено время начала пары на {event['start_time']}\n"
                elif field=="end_time":
                    msg+=f"Изменено время окончания пары на {event['end_time']}\n"
                elif field=="name":
                    msg+=f"Изменено название пары на {event['name']}\n"
                elif field=="teacher":
                    msg+=f"Изменен преподаватель на {event['teacher']}\n"
                elif field=="room_name":
                    msg+=f"Изменена аудитория на {event['room_name']}\n"
                elif field=="address":
                    msg+=f"Изменен адрес аудитории на {event['address']}\n"
    return msg

