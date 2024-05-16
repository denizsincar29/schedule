from dataclasses import dataclass
from datetime import date
import json
from typing import Self
from mess import get_person_info


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

    def __eq__(self, other):
        return self.person_id==other.person_id

    def __ne__(self, other):
        return self.person_id!=other.person_id

    def __hash__(self):
        return hash(self.person_id)

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

    @property
    def type(self) -> type:
        """Returns the type of the person."""
        return Student  # we can simply write if some_person.type==Student

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

    def json(self) -> str:
        """Returns the student as a JSON string."""
        return json.dumps(self.__dict__())

    @classmethod
    def _from_prepared(cls, data):  # dont use this method directly, use from_prepared in Person

        return cls(data["id"], data["name"], data["specialty"], data["profile"], date.fromisoformat(data["start_date"]), date.fromisoformat(data["end_date"]))

@dataclass
class Employee(Person):
    """
    Represents an employee.
    """

    group: str


    @property
    def type(self) -> type:
        """Returns the type of the person."""
        return Employee

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

    def json(self) -> str:
        """Returns the employee as a JSON string."""
        return json.dumps(self.__dict__())

    @classmethod
    def _from_prepared(cls, data: dict):  # dont use this method directly, use from_prepared in Person
        return cls(data["id"], data["name"], data["group"], date.fromisoformat(data["start_date"]), date.fromisoformat(data["end_date"]))

class People:
    """
    Represents a collection of people.

    Attributes:
    - people (list): The list of people.
    - current (str): The current person's ID.
    """
    def __init__(self, people: list, current: str="", friend: str=""):
        """
        Initializes the people.

        Parameters:
        - people (list): The list of people.
        - current (str): The current person's ID.
        friend (str): The friend's ID (to specify another person to get his/her data).
        """
        self.people=people
        self._current=current  # current person index
        self._friend=friend

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

    def __dict__(self):
        return {"current": self._current, "people": [person.__dict__() for person in self.people]}
    #endregion

    @property
    def current(self):
        return self.get_person_by_id(self._current)

    @current.setter
    def current(self, pid):
        if self.get_person_by_id(pid)==noone:

            raise ValueError("No person with this id")
        self._current=pid

    @property
    def friend(self):
        return self.get_person_by_id(self._friend)
    
    @friend.setter
    def friend(self, pid):
        self._friend=pid  # we can have no friend, so no need to check

    def json(self) -> str:
        """Returns the people as a JSON string."""
        return json.dumps(self.__list)

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
                start_date=date.fromisoformat(person_info['learningStartDate'])
                end_date=date.fromisoformat(person_info['learningEndDate'])
                parsed_persons.append(Student(person_id, person['fullName'], start_date, end_date, person_info['specialtyName'], person_info['specialtyProfile']))
            elif person_type=="employee":
                start_date=date.fromisoformat(person_info['dateIn'])
                end_date=date.fromisoformat(person_info['dateOut'])
                parsed_persons.append(Employee(person_id, person['fullName'], start_date, end_date, person_info['groupName']))
        return cls(parsed_persons)

    @classmethod
    def from_prepared_json(cls, data: dict) -> Self:
        """
        Parses the prepared JSON data with people. It is used for caching.

        Parameters:
        - data (dict): The prepared JSON data with people.

        Returns:
        - People: The people parsed from the data.
        """
        current=data["current"]  # we save only current person id, not friend
        people=data["people"]
        return cls([Person._from_prepared(person) for person in people], current)

    @classmethod
    def from_cache(cls) -> Self:
        """loads people from cache"""
        try:
            with open("people.json", "r") as f:
                data=json.load(f)
        except FileNotFoundError:
            return cls([])
        return cls.from_prepared_json(data)

    def to_cache(self):
        """saves people to cache"""
        with open("people.json", "w") as f:
            json.dump(self.__dict__(), f)

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
        return People([person for person in self.people if name.lower() in person.name.lower()])

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
        return lambda *args, **kwargs: print(f"Warning: NoOne has no method {attr}")
# yep, our ghost is ready.

noone=NoOne()  # we will use it to return when we need to return nothing