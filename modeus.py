import json
import httpx
import re
from datetime import datetime, timedelta
from pytz import UTC

def modeus_parse_token(email: str, password: str) -> str:
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
        #with open("raw.txt", "w", encoding="UTF-8") as f: f.write(str(before_form1_response))
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


def get_schedule(person_id: str, modeus_token: str, start_time: datetime, end_time: datetime) -> dict:
    if end_time<=start_time:
        raise ValueError("Time is bad!")
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

def search_person(term: str, by_id: bool, modeus_token: str) -> dict:
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
        else: raise RuntimeError("No key embedded")

def who_goes(event_id: str, modeus_token: str) -> dict:
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

