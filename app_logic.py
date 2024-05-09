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
        dotenv.load_dotenv(".env")  # dont eat from the parent directory.
        email=os.environ.get("MODEUS_EMAIL", "")
        password=os.environ.get("MODEUS_PASSWORD", "")
        self.backward.put(("creds", self.check_credentials(email, password, True)))
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
                    if command[2] is None:
                        command[2]=False  # we need to pass a boolean to the function
                    self.schedule.save_result(command[1], command[2])
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
            if not direct_pass:
                os.environ["MODEUS_EMAIL"]=email
                os.environ["MODEUS_PASSWORD"]=password
                with open(".env", "w") as f:
                    f.write(f"MODEUS_EMAIL={email}\nMODEUS_PASSWORD={password}\n")

            self.schedule=Schedule(email, password)
            self.schedule.load_people()
            self.person=self.schedule.current_person
        return authed

    def send_command(self, command):  # main thread uses.
        self.forward.put(command)

    def has_reply(self):  # main thread uses.
        return not self.backward.empty()

    def get_reply(self):  # main thread uses.
        return self.backward.get()