# schedule 2.0
by Deniz Sincar <deniz@r1oaz.ru>  
This program is designed to view the schedule of students, teachers and other people at Northern Arctic Federal University (Arkhangelsk, Russia).
It supports searching for people, viewing the schedule for today, for a specific day, and the intersection of the schedule with another person.
It uses an unofficial API of the site modeus.org. It does not store user data, except for the cache to speed up the work. The cache can be safely opened, read and deleted, as they are jsons.
# installation
Recently, a new UV package manager has been released by ruff developers. It's recommended to use it, but you can use pip as well.

```bash
git clone https://github.com/denizsincar29/narfu_schedule
cd narfu_schedule
pip install -r requirements.txt  # but if you use UV, you can skip this step.
python main.py
# or
uv run main.py
```

# first run
At the first run, the program will ask for your email and password from modeus.org. The credentials will be dotenved automatically.
Modeus is designed so that even with your login, you can find out the schedule of anyone in the university, so the program will ask and save your full name. More in local readmes.
# usage
webview client is planned to be added in the future. For now, the program is made in the form of a console where you can enter [commands in english](#commands).
# commands
Go to [command_help.md](command_help.md) for more information.
Exiting with Ctrl+c for console lovers also works. If the program hangs, press Ctrl+break, but it's like a blow to the head, don't forget to save the data!
# license
Use this program as you like, but do not forget to mention the author. I'm not responsible if you are banned from modeus if you flood their servers with requests. Use the program wisely.
# contacts
If you have any questions, suggestions or found a bug, write to @denizsincar29 on telegram or deniz@r1oaz.ru.
