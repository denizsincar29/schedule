from datetime import date, time
from dateutil.relativedelta import relativedelta
from schedule.parsers.russian_date import russian_date
from schedule.parsers.events import Events, Event, study_to_number

import pytest

JDATA=[{"id": "bcfa9c47-d828-4e2d-a821-e50d070dfbf2", "event": 4, "date": "2024-07-02", "start_time": "14:30:00", "end_time": "16:05:00", "name": "Философия (все, кроме 44.03.05)", "teacher": "Шубина Татьяна Федоровна", "room_name": "207 (АУК-9)", "address": "пр-кт Ломоносова, д.2", "status": "Неизвестно", "format": "Консультация, ", "diff": ""}, {"id": "5f3a59c9-eeea-4b94-8ed7-2156cd8dc689", "event": 4, "date": "2024-07-03", "start_time": "14:30:00", "end_time": "17:50:00", "name": "Философия (все, кроме 44.03.05)", "teacher": "Шубина Татьяна Федоровна", "room_name": "107 (АУК-9)", "address": "пр-кт Ломоносова, д.2", "status": "Неизвестно", "format": "Контрольная работа, Экзамен", "diff": ""}]




class TestRussianDate():
    def test_today(self):
        assert "сегодня" in russian_date(date.today())

    def test_yesterday(self):
        assert "вчера" in russian_date(date.today() - relativedelta(days=1))

    def test_tomorrow(self):
        assert "завтра" in russian_date(date.today() + relativedelta(days=1))

    def test_day_of_week(self):
        assert russian_date(date(2023, 3, 13)).startswith("понедельник, 13 марта")

    def test_day_of_month(self):
        assert "24 марта" in russian_date(date(2023, 3, 24))

    def test_month(self):
        assert russian_date(date(2023, 3, 8), include_year=True).endswith("8 марта 2023 года")

    def test_year(self):
        assert russian_date(date(2024, 4, 29), include_year=True).endswith("29 апреля 2024 года")


class TestEvents:
    @pytest.fixture
    def events(self):
        return Events.from_prepared_json(JDATA)

    def test_studynum(self):
        assert study_to_number(time(8, 20)) == 1
        assert study_to_number(time(9, 40)) == -1

    def test_tokenize(self, events):
        assert events.get_event_by_strindex(3) == events[0]
        assert events.get_event_by_strindex(3000000000) == None

    def test_filters(self, events: Events):
        assert events.get_event_by_date(date(2024, 7, 3))[0] == events[1]  # the second event is 3rd june
        assert len(events.get_events_by_num(4))==2
        assert len(events.get_events_by_num(1))==0
        assert len(events.get_events_by_teacher("шубина")) ==2

