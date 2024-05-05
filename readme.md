# schedule 2.0
by Deniz Sincar <deniz@r1oaz.ru>  
This program is designed to view the schedule of students, teachers and other people at Northern Arctic Federal University (Arkhangelsk, Russia).
It supports searching for people, viewing the schedule for today, for a specific day, and the intersection of the schedule with another person.
It uses an unofficial API of the site modeus.org. It does not store user data, except for the cache to speed up the work. The cache can be safely opened, read and deleted, as they are jsons.
# installation
'''
git clone https://github.com/denizsincar29/narfu_schedule
cd narfu_schedule
pip install -r requirements.txt
python schedule.py
'''
# first run
At the first run, the program will ask for your email and password from modeus.org. The credentials will be dotenved automatically.
Modeus is designed so that even with your login, you can find out the schedule of anyone in the university, so the program will ask and save your full name. More in local readmes.
# usage
webview client is planned to be added in the future. For now, the program is made in the form of a console where you can enter [commands in english](#commands).
# commands
- `today` - schedule for today
- `dd/mm/yyyy` - schedule for a specific day.  
you can omit the year or month/year, then they will be taken from the current date. You can enter only the day, only the month, or day/month.
to get the intersection of the schedule with another person, add together to the command.  
For example:
`today together`,
`1/1 together`  
`1 together`
etc.
- `reset` - stop following another person. Now you are alone again. Use if you want to watch your schedule again.
- `resave` - Change / resave the profile. Use if you have changed your profile or identity ahahahahah. To find a friend, use friend or search.
- `search` or `friend` - search for a person by name. Use to get the schedule of another person - a fellow student, teacher, etc.
- `exit`, `quit` or just press Enter - exit the program. Ctrl+c for console lovers also works. If the program hangs, press Ctrl+break, but it's like a blow to the head, don't forget to save the data!
- `help` - display help
# license
Use this program as you like, but do not forget to mention the author. I'm not responsible if you are banned from modeus if you flood their servers with requests. Use the program wisely.
# contacts
If you have any questions, suggestions or found a bug, write to @denizsincar29 on telegram or deniz@r1oaz.ru.
# changelog
## 2.0:
- 75% of the code was rewritten- the most part of the code was hard to use in the future, navigation was difficult, and the code was not very readable.
The human-parser was rewritten to use intermediate beautiful jsons. Parsing from server output, a huge json directly to human-readable format was a terrible idea.
- Completely rewritten the cache system. Now the cache is stored in jsons, which can be easily read and deleted. The cache is stored in the cache folder.
- completed the overlap of schedules with another person. Now you can see the intersection of your schedule with another person.
- added the ability to search for a person by name. Now you can find the schedule of another person - a fellow student, teacher, etc. without changing the profile. Your main profile (your name and id) is saved in people.json.
Therefore, I added the ability to change the profile, and temperarily switch to another person's schedule without changing the main profile.
- Now schedule is cached in the cache folder. The cache is stored in jsons, which can be easily read and deleted. The full month schedule is cached, but in case it changes, the cache is updated at the start of the program. (to be added)
- Over all,  there are many changes here and there.
## 1.0:
- Initial release.  
The change log was not kepped, but the program had nearly the same functionality. The code was not very readable, and the cache was stored in txt files.

