import httpx
import re
from datetime import datetime
from pytz import UTC
from functools import lru_cache, partial
import asyncio
import time
import logging

def modeus_parse_token(email: str, password: str) -> str:
    """
    Parse id_token from modeus server.

    Parameters:
    email (str): email.
    password (str): password.

    Returns:
    str: id_token.

    Raises:
    RuntimeError: if can't parse 1st form, 2nd form or id_token.
    """
    with httpx.Client(timeout=10) as client:
        params = {
            "client_id":"YDNCeCPsf1zL2etGQflijyfzo88a",
            "redirect_uri":"https://narfu.modeus.org/",
            "response_type":"id_token",
            "scope":"openid",
            "state":"abab35fcb9164912aa46d287a594a338",
            "nonce":"08cd3a21e9724040acb48cf3a35b0c4b"
        }
        url = "https://narfu-auth.modeus.org/oauth2/authorize"
        before_form1_response = client.get(url, params=params)
        cookies = httpx.Cookies()
        cookies.set(
            'tc01', before_form1_response.cookies['tc01']
        )
        form1_response = client.get(
            before_form1_response.next_request.url,
            cookies=cookies
        )
        form1 = form1_response.text
        form1_url_match = re.search(r'<form.*action="(https:.+)".*>', form1)
        if not form1_url_match:
            raise RuntimeError("modeus_parse_token: can't parse 1st form")
        form1_url = form1_url_match.group(1)
        data = {
            "UserName":email,
            "Password":password,
            "AuthMethod":"FormsAuthentication"
        }
        form2_response = client.post(
            form1_url, data=data, cookies=httpx.Cookies(), follow_redirects=True,
            headers=dict(Referer=str(form1_response.url))
        )
        form2 = form2_response.text
        form2_matches = re.findall(r'<input type="hidden" name="(.+?)" value="(.+?)" \/>', form2)
        if len(form2_matches) < 2:
            raise RuntimeError("modeus_parse_token: can't parse 2nd form")
        data = dict(form2_matches)
        url="https://narfu-auth.modeus.org:443/commonauth"
        last_response = client.post(url, data=data, follow_redirects=True)
        last_url = str(last_response.url)
        id_token_match = re.search(r'#id_token=(.+?)&', last_url)
        if not id_token_match:
            raise RuntimeError("modeus_parse_token: can't parse id_token")
        id_token = id_token_match.group(1)
        return id_token

def modeus_auth(email: str, password: str) -> bool:
    """
    Check if user's credentials are correct.

    Parameters:
    email (str): email.
    password (str): password.

    Returns:
    bool: True if credentials are correct, False otherwise.

    Raises:
    RuntimeError: if can't parse 1st form, 2nd form.
    """
        # copy-paste from modeus_parse_token until can't parse 2nd form. If parsed, return True
    with httpx.Client(timeout=10) as client:
        params = {
            "client_id":"YDNCeCPsf1zL2etGQflijyfzo88a",
            "redirect_uri":"https://narfu.modeus.org/",
            "response_type":"id_token",
            "scope":"openid",
            "state":"abab35fcb9164912aa46d287a594a338",
            "nonce":"08cd3a21e9724040acb48cf3a35b0c4b"
        }
        url = "https://narfu-auth.modeus.org/oauth2/authorize"
        before_form1_response = client.get(url, params=params)
        cookies = httpx.Cookies()
        cookies.set(
            'tc01', before_form1_response.cookies['tc01']
        )
        form1_response = client.get(
            before_form1_response.next_request.url,
            cookies=cookies
        )
        form1 = form1_response.text
        form1_url_match = re.search(r'<form.*action="(https:.+)".*>', form1)
        if not form1_url_match:
            raise RuntimeError("modeus_auth: can't parse 1st form")
        form1_url = form1_url_match.group(1)
        data = {
            "UserName":email,
            "Password":password,
            "AuthMethod":"FormsAuthentication"
        }
        form2_response = client.post(
            form1_url, data=data, cookies=httpx.Cookies(), follow_redirects=True,
            headers=dict(Referer=str(form1_response.url))
        )
        form2 = form2_response.text
        form2_matches = re.findall(r'<input type="hidden" name="(.+?)" value="(.+?)" \/>', form2)
        if len(form2_matches) < 2:
            return False
        return True


def get_schedule(person_id: str, modeus_token: str, start_time: datetime, end_time: datetime) -> dict:
    """
    Get schedule of a person.

    Parameters:
    person_id (str): person id.
    modeus_token (str): modeus token.
    start_time (datetime): start time.
    end_time (datetime): end time.

    Returns:
    dict: huge json with schedule.

    Raises:
    ValueError: if start_time >= end_time.
    RuntimeError: if can't find key embedded.
    """
    if end_time<=start_time:
        raise ValueError("End time must be greater than start time!")
    url = "https://narfu.modeus.org/schedule-calendar-v2/api/calendar/events/search?tz=Europe/Moscow"
    # "/" must not be encoded
    request_json = {
        "size": 500,
        "timeMin": start_time.astimezone(UTC).isoformat(timespec='seconds'),
        "timeMax": end_time.astimezone(UTC).isoformat(timespec='seconds'),
        "attendeePersonId": [person_id,]
    }

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {modeus_token}"
    }

    with httpx.Client(timeout=10) as client:
        response = client.post(
            url,
            json=request_json,
            headers=headers
        )
        j=response.json()
        #with open("tt.json", "w", encoding="UTF-8") as f: json.dump(j["_embedded"], f, ensure_ascii=False, indent=2)
        if "_embedded" in j: return j
        else: raise RuntimeError("No key embedded")

def get_schedule_async(person_id: str, modeus_token: str, start_time: datetime, end_time: datetime, on_finish, stop_event: asyncio.Event) -> None:
    """
    Get schedule of a person asynchronously.

    Parameters:
    person_id (str): person id.
    modeus_token (str): modeus token.
    start_time (datetime): start time.
    end_time (datetime): end time.
    on_finish (function): callback function.
    stop_event (asyncio.Event): stop event.

    Returns:
    None.

    Raises:
    ValueError: if start_time >= end_time.
    """
    if end_time<=start_time:
        raise ValueError("End time must be greater than start time!")
    url = "https://narfu.modeus.org/schedule-calendar-v2/api/calendar/events/search?tz=Europe/Moscow"
    # "/" must not be encoded
    request_json = {
        "size": 500,
        "timeMin": start_time.astimezone(UTC).isoformat(timespec='seconds'),
        "timeMax": end_time.astimezone(UTC).isoformat(timespec='seconds'),
        "attendeePersonId": [person_id,]
    }

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {modeus_token}"
    }

    async def get_schedule_async_inner():
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                while not stop_event.is_set():
                    response_task = asyncio.create_task(client.post(
                        url,
                        json=request_json,
                        headers=headers
                    ))
                    done, pending = await asyncio.wait(
                        [response_task],
                        timeout=1,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    if stop_event.is_set():
                        for task in pending:
                            task.cancel()
                        break

                    if response_task in done:
                        response = response_task.result()
                        response.raise_for_status()
                        j = response.json()
                        on_finish(j)
                        break  # Exit the loop after the first successful request
            except httpx.RequestError as exc:
                print(f"An error occurred while requesting {exc.request.url!r}.")
            except httpx.HTTPStatusError as exc:
                print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            except asyncio.CancelledError:
                print("The task was cancelled.")
    #asyncio.create_task(get_schedule_async_inner())  # this gives no event loop error
    async def run():
        task = asyncio.create_task(get_schedule_async_inner())
    asyncio.run(run())

def search_person(term: str, by_id: bool, modeus_token: str) -> dict:
    """
    Search person in the university database.

    Parameters:
    term (str): search term.
    by_id (bool): search by id or by full name.
    modeus_token (str): modeus token.

    Returns:
    dict: huge json with search results.

    Raises:
    RuntimeError: if can't find key embedded.
    """
    if by_id:
        logging.warning("Search by id is not implemented yet. Returning empty result.")
        return {"_embedded": {"persons": []}}
    mode="id" if by_id else "fullName"
    request_json = {
        "size": 10,
        mode: term,
        "sort": "+fullName"
    }

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {modeus_token}"
    }

    url="https://narfu.modeus.org/schedule-calendar-v2/api/people/persons/search"
    with httpx.Client(timeout=10) as client:
        response = client.post(
            url,
            json=request_json,
            headers=headers
        )
    
        j=response.json()
        if "_embedded" in j: return j
        else: raise RuntimeError(f"No key embedded! {j}")

def who_goes(event_id: str, modeus_token: str) -> dict:
    """
    Get attendees of an event.

    Parameters:
    event_id (str): event id.
    modeus_token (str): modeus token.

    Returns:
    dict: huge json with attendees.

    Raises:
    RuntimeError: if can't find key embedded.
    """
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {modeus_token}"
    }

    url=f"https://narfu.modeus.org/schedule-calendar-v2/api/calendar/events/{event_id}/attendees"
    with httpx.Client(timeout=10) as client:
        response = client.get(
            url,
            headers=headers
        )
    
        j=response.json()
        return j
class TimeCache:
    def __init__(self, seconds=5):
        self.ttl = 0
        self.seconds = seconds
        self.cache = {}

    @property
    def expired(self):
        """Return the same value withing `seconds` time period"""
        ttl=round(time.time() / self.seconds)
        if ttl != self.ttl:
            self.ttl = ttl
            self.cache = {}
            return True
        return False  # not expired

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            if not self.expired and key in self.cache:
                return self.cache[key][1]
            result = func(*args, **kwargs)
            self.cache[key] = (self.ttl, result)
            return result
        return wrapper

# a function that returns if there is internet connection. It caches for 5 seconds
@TimeCache(5)
def is_connected():
    try:
        httpx.get("https://google.com", timeout=5)
        return True
    except:
        return False

