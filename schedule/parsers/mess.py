def get_name(event_id, data):
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

def get_teacher(event_id, data):
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

def get_room(event_id, data):
    # internal. works with the big mess
    event_locations = data['event-locations']
    event_rooms = data['event-rooms']	
    rooms = data['rooms']
    for event_location in event_locations:
        if event_location['eventId'] == event_id:
            # event locations thing has custom location if it's not a room but online event
            if "customLocation" in event_location and event_location["customLocation"]:  # we check because this strange api can return "customLocation"less event
                return (event_location["customLocation"], "online")
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


def get_format_id(event_id, data):
    """
    Retrieves the format of an event based on its ID from the given data.

    Parameters:
    - event_id (int): The ID of the event to retrieve the format for.
    - data (dict): The data containing the event formats.

    Returns:
    - str or None: The format of the event if found, None otherwise.
    """
    # data["events"][indx][]
    events = data['events']
    for event in events:
        if event['id'] == event_id:
            return event['formatId']
    return None

types_formats={
    "LECT": "Лекция",
    "SEMI": "Практическое занятие",
    "SEMINAR": "Семинар",
    "SEMI_OTHER": "Практический курс",
    "LAB": "Лабораторная работа",
    "LAB_RESEARCH": "Лабораторный опыт",
    "MID_CHECK": "Контрольная работа",
    "EXAMINATION": "Экзамен",
    "PRETEST": "Предэкзаменационная аттестация",
    "DIFF_PRETEST": "Дифференцированный зачёт",
    "CONS": "Консультация",
    "INFORMATION": "вводная информация",
    None: ""  # some events don't have a type or format
}

def get_type_id(event_id, data):
    """
    Retrieves the type of an event based on its ID from the given data.

    Parameters:
    - event_id (int): The ID of the event to retrieve the type for.
    - data (dict): The data containing the event types.

    Returns:
    - str or None: The type of the event if found, None otherwise.
    """
    # data["events"][indx][]
    events = data['events']
    for event in events:
        if event['id'] == event_id:
            return event['typeId']
    return None

def get_type_and_format_name(event_id, data):
    """
    Retrieves the type and format of an event based on its ID from the given data.

    Parameters:
    - event_id (int): The ID of the event to retrieve the type and format for.
    - data (dict): The data containing the events.

    Returns:
    - str: The type and format of the event.
    """
    type_id = get_type_id(event_id, data)
    format_id = get_format_id(event_id, data)
    type_name=""
    format_name=""
    if type_id in types_formats:
        type_name=types_formats[type_id]
    else:
        type_name=f"Неизвестный тип {type_id}"
    if format_id in types_formats:
        format_name=types_formats[format_id]
    else:
        format_name=f"Неизвестный формат {format_id}"
    # sometimes the strings are empty, so i have came up with this clever solution
    return ", ".join([type_name, format_name])  # empty string, one of them or both separated by comma+space
