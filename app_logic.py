from schedule import Schedule, auth
import schedparser
from datetime import datetime
from pytz import timezone
from threading import Thread
from queue import Queue
import os
import dotenv # move dotenv check here
from sys import exit  # pyinstaller can't find it in some cases
dotdotdot=... # for the match statement
VERSION="1.0.0-beta2"

class App(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.forward = Queue()
        self.backward = Queue()
        self.schedule = None  # don't use this if not authed. Else you'll get angry customers chasing you with pitchforks.
        self.person=None
        self.daemon = True  # we don't want to keep the program running after the main thread exits
        self.start()

    def run(self):
        dotenv.load_dotenv()
        email=os.environ.get("MODEUS_EMAIL", "")
        password=os.environ.get("MODEUS_PASSWORD", "")
        match self.check_credentials(email, password, True):
            case False:  # can't return False when direct passing.
                self.backward.put(("auth", "invalid",))  # touplify every reply to avoid confusion
            case True:
                self.backward.put(("auth", "welcome"))
            case dotdotdot:
                self.backward.put(("auth", "credentials"))
        while True:
            command = self.forward.get()  # blocks until we get something
            command.extend([None]*(4-len(command)))
            # command is a list.
            match command[0]:
                case "schedule":
                    self.backward.put(("schedule", self.schedule.get_schedule_str(self.schedule.current_person, command[1], command[2], command[3])))
                case "fullname":
                    self.backward.put(("search", self.schedule.search_person(command[1], False)))
                case "saveperson":
                    self.schedule.save_person(command[1]["id"])
                case "check_credentials":
                    self.backward.put(("creds", self.check_credentials(command[1], command[2], command[3])))
                case "exit":
                    return  # exit the thread
                case _:
                    self.backward.put(("Unknown", "command"))
            self.forward.task_done()

    def check_credentials(self, email, password, direct_pass=False):
        if not email or not password:
            return ...  # return something that will make the main thread ask for credentials
        authed=direct_pass  # if we loaded the credentials from the environment, we don't need to check them
        if not direct_pass:
            authed=auth(email, password)
        if authed:
            self.schedule=Schedule(email, password)
            self.person=self.schedule.current_person
        return authed

    def send_command(self, command):  # main thread uses.
        self.forward.put(command)

    def has_reply(self):  # main thread uses.
        return not self.backward.empty()

    def get_reply(self):  # main thread uses.
        return self.backward.get()