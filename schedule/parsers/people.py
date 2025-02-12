from dataclasses import dataclass
from datetime import date, datetime
import json
try:
    from typing import Self
except ImportError:
    Self=type("Self", (), {})

from .mess import get_person_info


@dataclass
class Person:
    """
    Represents a person.

    Attributes:
    - person_id (str): The unique identifier of the person.
    - name (str): The name of the person.
    - start_date (date): The start date of the person.
    - end_date (date): The end date of the person.

    Optional Attributes:
    - type (type): The type of the person.
    """
    person_id: str
    name: str
    start_date: date|None  # can be omitted in Json for some strange reason.
    end_date: date|None

    def mutate(self, other):
        """
        Mutates the person with the other person.

        Parameters:
        - other (Person): The other person to mutate with.
        """
        # student to student... etc
        self.person_id=other.person_id
        self.name=other.name
        self.start_date=other.start_date
        self.end_date=other.end_date
        if isinstance(other, Student):
            self.specialty=other.specialty
            self.profile=other.profile
        elif isinstance(other, Employee):
            self.group=other.group

        # 

    #region magic methods
    def __eq__(self, other):
        return self.person_id==other.person_id

    def __ne__(self, other):
        return self.person_id!=other.person_id

    def __hash__(self):
        return hash(self.person_id)
    #endregion

    @classmethod
    def _from_prepared(cls, data: dict) -> Self:
        """
        Creates a person from the prepared data.

        Parameters:
        - data (dict): The prepared data for the person.

        Returns:
        - Person: The person created from the data.
        """
        if data["type"]=="student":
            return Student._from_prepared(data)
        return Employee._from_prepared(data)

@dataclass
class Student(Person):
    """
    Represents a student.


    Attributes:
    - specialty (str): The specialty of the student.
    - profile (str): The profile of the student.
    """
    specialty: str
    profile: str

    def __post_init__(self):  # specialty and profile are empty if they are none
        if self.specialty is None:
            self.specialty=""
        if self.profile is None:
            self.profile=""
        # no need to check dates, they can be None

    # grade of the student by year:
    @property
    def grade(self) -> int:
        """Returns the grade of the student by year."""
        # if his start year is None, grade is 0
        if self.start_date is None:
            return 0
        # grade is the difference between current year and start year, but grade changes in September
        # if current month is less than September, then we are in the same grade
        if datetime.now().month<9:
            return datetime.now().year-self.start_date.year
        # if we are in September or later, then we are in the next grade
        return datetime.now().year-self.start_date.year+1


    @property
    def type(self) -> type:
        """Returns the type of the person."""
        return Student  # we can simply write if some_person.type==Student

    def pprint(self):
        """Prints the student in a human-readable format."""
        print(self.__str__())


    def __str__(self):
        msg=self.name
        if self.specialty!="":
            msg+=f", {self.specialty}"
        if self.profile!="":
            msg+=f" - {self.profile}"
        # don't care start end date, use grade if not 0.
        if self.grade!=0:
            msg+=f". {self.grade} курс"
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
            "start_date": self.start_date.isoformat() if self.start_date is not None else None,
            "end_date": self.end_date.isoformat() if self.end_date is not None else None
        }

    def json(self) -> str:
        """Returns the student as a JSON string."""
        return json.dumps(self.__dict__())

    @classmethod
    def _from_prepared(cls, data):  # dont use this method directly, use from_prepared in Person
        # for some reason, start_date and end_date can be None in Json
        stdate=datetime.fromisoformat(data["start_date"]).date() if data["start_date"] is not None else None
        endate=datetime.fromisoformat(data["end_date"]).date() if data["end_date"] is not None else None
        return cls(data["id"], data["name"], stdate, endate, data["specialty"], data["profile"])

@dataclass
class Employee(Person):
    """
    Represents an employee.
    """

    group: str

    def __post_init__(self):
        if self.group is None:
            self.group=""


    @property
    def type(self) -> type:
        """Returns the type of the person."""
        return Employee

    def pprint(self):
        """Prints the employee in a human-readable format."""
        print(self.__str__())


    def __str__(self):
        #return f"{self.name}: {self.group}. Работает с {self.start_date} по {self.end_date}"
        msg=self.name
        if self.group!="":
            msg+=f" - {self.group}"
        if self.start_date is not None:
            msg+=f". Работает с {self.start_date}"
        if self.end_date is not None:
            msg+=f" по {self.end_date}."
        return msg

    def __repr__(self):
        return self.json()

    def __dict__(self):
        return {
            "id": self.person_id,
            "name": self.name,
            "type": "employee",
            "group": self.group,
            "start_date": self.start_date.isoformat() if self.start_date is not None else None,
            "end_date": self.end_date.isoformat() if self.end_date is not None else None
        }

    def json(self) -> str:
        """Returns the employee as a JSON string."""
        return json.dumps(self.__dict__())

    @classmethod
    def _from_prepared(cls, data: dict):  # dont use this method directly, use from_prepared in Person
        stdate=datetime.fromisoformat(data["start_date"]).date() if data["start_date"] is not None else None
        endate=datetime.fromisoformat(data["end_date"]).date() if data["end_date"] is not None else None
        return cls(data["id"], data["name"], stdate, endate, data["group"])

class People:
    """
    Represents a collection of people.

    Attributes:
    - people (list): The list of people.
    """
    def __init__(self, people: list[Person]=[]):
        """
        Initializes the people.

        Parameters:
        - people (list): The list of people.
        - current (str): The current person's ID.
        friend (str): The friend's ID (to specify another person to get his/her data).
        """
        self.people=people

    #region magic methods
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
        return "\n".join(f"{i+1}. {person}" for i, person in enumerate(self.people))

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

    def __list__(self):
        return self.people
    #endregion

    def pprint(self):
        """Prints the people in a human-readable format."""
        print(self.__str__())


    def append(self, person: Person):
        """Appends a person to the list."""
        return self.people.append(person) if person not in self.people else None


    def json(self) -> str:
        """Returns the people as a JSON string."""
        # return json.dumps(self.__list__()) # nope, we need to call json method of each person
        return json.dumps([person.__dict__() for person in self.people])

    @classmethod
    def from_who_goes(cls, data):
        """
        parses who goes to the event. Data came from the server

        Parameters:
        - data (list): The data from the server.
        """
        # roleId can be STUDENT or TEACHER
        evts=[]
        for dat in data:
            if dat["roleId"]=="STUDENT":
                evts.append(Student(dat["personId"], dat["fullName"], None, None, dat["specialtyName"], dat["specialtyProfile"]))
            else:
                # this strange api doesn't return group name. Instead, the student fields are None. So employee fields are empty strings
                evts.insert(0, Employee(dat["personId"], dat["fullName"], None, None, ""))  # prepend teacher to start of the list
        return cls(evts)

    @classmethod
    def from_big_mess(cls, data: dict) -> Self:
        """
        Parses the server response with people.

        Parameters:
        - data (dict): The server response with people.

        Returns:
        - People: The people parsed from the data.
        """
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
                start_date=datetime.fromisoformat(person_info['learningStartDate']).date() if person_info['learningStartDate'] is not None else None
                end_date=datetime.fromisoformat(person_info['learningEndDate']).date() if person_info['learningEndDate'] is not None else None
                parsed_persons.append(Student(person_id, person['fullName'], start_date, end_date, person_info['specialtyName'], person_info['specialtyProfile']))
            elif person_type=="employee":
                start_date=date.fromisoformat(person_info['dateIn']) if person_info['dateIn'] is not None else None
                end_date=date.fromisoformat(person_info['dateOut']) if person_info['dateOut'] is not None else None
                parsed_persons.append(Employee(person_id, person['fullName'], start_date, end_date, person_info['groupName']))
        return cls(parsed_persons)

    @classmethod
    def from_prepared_json(cls, data: list) -> Self:
        """
        Parses the prepared JSON data with people. It is used for caching.

        Parameters:
        - data (list): The prepared JSON data with people.

        Returns:
        - People: The people parsed from the data.
        """
        return cls([Person._from_prepared(person) for person in data])

    @classmethod
    def from_cache(cls, cache_filename) -> Self:
        """loads people from cache"""
        try:
            with open(cache_filename, "r", encoding="UTF-8") as f:
                data=json.load(f)
        except FileNotFoundError:
            return cls([])
        return cls.from_prepared_json(data)

    def to_cache(self, cache_filename):
        """saves people to cache"""
        with open(cache_filename, "w", encoding="UTF-8") as f:
            f.write(self.json())

    def get_person_by_id(self, person_id: str) -> Person:
        """
        Returns the person by the ID.

        Parameters:
        - person_id (str): The ID of the person.

        Returns:
        - Person: The person with the ID or NoOne if not found.
        """
        person=[person for person in self.people if person.person_id==person_id]
        return person[0] if len(person)>0 else NoOne()

    def get_people_by_name(self, name: str) -> Self:
        """
        Returns the people by the name.

        Parameters:
        - name (str): The name of the person.

        Returns:
        - People: The people with the name.
        """
        return People([person for person in self.people if name.lower() in person.name.lower() or name.lower().replace("ё", "е") in person.name.lower() or name.lower().replace("е", "ё") in person.name.lower()])  # russian letter yo can be written as e and vice versa

    def get_students(self) -> Self:
        """Returns the students."""
        return People([person for person in self.people if isinstance(person, Student)])

    def get_employees(self) -> Self:
        """Returns the employees."""
        return People([person for person in self.people if isinstance(person, Employee)])

    def get_students_by_specialty(self, specialty: str) -> Self:
        """
        Returns the students by the specialty.

        Parameters:
        - specialty (str): The approximate specialty of the student. It is case-insensitive.

        Returns:
        - People: The students with the specialty.
        """
        return People([person for person in self.get_students() if specialty.lower() in person.specialty.lower()])

    def get_students_by_profile(self, profile: str) -> Self:
        """
        Returns the students by the profile.

        Parameters:
        - profile (str): The approximate profile of the student. It is case-insensitive.

        Returns:
        - People: The students with the profile.
        """
        return People([person for person in self.get_students() if profile.lower() in person.profile.lower()])

    def get_employees_by_group(self, group: str) -> Self:
        """
        Returns the employees by the group.

        Parameters:
        - group (str): The approximate group of the employee. It is case-insensitive.

        Returns:
        - People: The employees with the group.
        """
        return People([person for person in self.get_employees() if group.lower() in person.group.lower()])

    def get_people_by_date(self, date: date) -> Self:
        """
        Returns the people that are active on the date. E.g. who are studying or working.

        Parameters:
        - date (date): The date to check.

        Returns:
        - People: The people who are active on the date.
        """
        return People([person for person in self.people if person.start_date<=date<=person.end_date])  # basically, get all people who are active on this date


class NoOne(Person):
    """Represents a ghost person. It is used when there is no person."""
    def __init__(self):
        super().__init__("", "NoOne", None, None)

    @property
    def type(self):
        """Returns the type of the person."""
        return NoOne

    def __str__(self):
        return "Warning: NoOne is not a person."

    def __getattr__(self, attr):
        print(f"Warning: NoOne has no attribute {attr}")
        return lambda *args, **kwargs: print(f"Warning: NoOne has no method {attr}")  # if you try to call the attribute, it will print a warning
# yep, our ghost is ready.

noone=NoOne()  # we will use it to return when we need to return nothing