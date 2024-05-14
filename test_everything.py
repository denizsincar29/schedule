import pytest
import modeus
import schedparser
import dotenv
import os
from datetime import datetime, timedelta
from pytz import timezone
moscow=timezone('Europe/Moscow')

dotenv.load_dotenv()
email=os.getenv("MODEUS_EMAIL")
password=os.getenv("MODEUS_PASSWORD")

def test_auth():
    # this test will fail if your environment variables are not set
    assert not modeus.modeus_auth("incorrect@email.com", "qwertyuiopasdfghjklzxcvbnm123456789")  # wow, The password is so strong!
    assert modeus.modeus_auth(email, password) # I hope you have set your environment variables

def test_token():
    # this test will fail if your environment variables are not set
    assert modeus.modeus_parse_token(email, password)  # I hope you have set your environment variables
    with pytest.raises(RuntimeError):
        modeus.modeus_parse_token("incorrect@e.mail", "qwertyuiopasdfghjklzxcvbnm123456789")
    with pytest.raises(RuntimeError):
        modeus.modeus_parse_token(email, "qwertyuio")  # correct email, but incorrect password

testevents=[
        {
      "id": "f8ade90c-0a83-49d2-9920-920ef8720b84",
      "event": 1,
      "date": "2024-05-02T00:00:00+03:00",
      "start_time": "08:20",
      "end_time": "09:55",
      "name": "Алгоритмизация и программирование",
      "teacher": "Латухина Екатерина Александровна",
      "room_name": "42 (АУК-11)",
      "address": "наб. Северной Двины, д.2",
      "status": "Проведено",
      "diff": "+"
    },
    {
      "id": "943ce483-8faf-4682-becd-ae6c42c435ff",
      "event": 2,
      "date": "2024-05-02T00:00:00+03:00",
      "start_time": "10:10",
      "end_time": "11:45",
      "name": "Алгоритмизация и программирование",
      "teacher": "Латухина Екатерина Александровна",
      "room_name": "42 (АУК-11)",
      "address": "наб. Северной Двины, д.2",
      "status": "Проведено",
      "diff": "+"
    },
    {
      "id": "8a4a3c33-0f9d-413c-9d93-f2a5dbba6f6b",
      "event": 3,
      "date": "2024-05-02T00:00:00+03:00",
      "start_time": "12:00",
      "end_time": "13:35",
      "name": "Физика (базовый уровень) 09.03.00",
      "teacher": "Харламова Анастасия Александровна",
      "room_name": "2301 (АУК-2)",
      "address": "наб. Северной Двины, д.22",
      "status": "Проведено",
      "diff": "+"
    }
]

def test_events():
    start_time=moscow.localize(datetime(2024, 5, 2, 0, 0, 0))
    delta=timedelta(days=1)
    filtered=schedparser.filter_events(testevents, start_time, delta)
    assert len(filtered)==3
    assert filtered[0]["name"]=="Алгоритмизация и программирование"
    filtered=schedparser.filter_events(testevents, start_time)  # everything for today
    assert len(filtered)==3
    filtered=schedparser.filter_events(testevents, teacher_query="Латухина")  # Большой привет Латухиной Екатерине Александровне!
    assert len(filtered)==2
    filtered=schedparser.filter_events(testevents, room_query="2301")
    assert len(filtered)==1
    filtered=schedparser.filter_events(testevents, start_time="10:11", end_time="13:40")  #the event that starts at 10:10 is not included
    assert len(filtered)==2
    filtered=schedparser.filter_events(testevents, evt_num=2)
    assert len(filtered)==1
    assert filtered[0]["name"]=="Алгоритмизация и программирование"
    filtered=schedparser.filter_events(testevents, evt_num=4)
    assert len(filtered)==0  # there is no event with number 4
    filtered=schedparser.filter_events(testevents, evt_num=3, teacher_query="Латухина")
    assert len(filtered)==0  # there is no event with number 3 and teacher "Латухина". the programming teacher does not teach physics xD
    filtered=schedparser.filter_events(testevents, evt_num=3, teacher_query="анастасия")  # большой привет Харламовой Анастасии Александровне!
    assert len(filtered)==1  # case-insensitive search
    assert schedparser.filter_events(testevents) == testevents  # no filters
    # ooh that's a lot of tests
    

