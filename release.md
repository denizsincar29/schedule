# release 1.0-beta2
This is a major beta release. This release has a lot of changes and improovements.
## Changes
- Fixed the schedule difference calculation, human readable outputter is now showing the correct difference. The timetable changes are now correctly shown on the program launch.
- trying to fix the issue where the program gets schedule for one more extra day while you didn't ask for it. E.g. if you ask for 3 days, it will give you 4 days. Still investigating.
- added command "txt" to save the last output to a text file. The file will be saved in the same directory as the program.
- added commands "thisweek" and "nextweek" to get the schedule for the current week and the next week.
- now, output includes the schedule date and name of the person who's schedule is being shown.
- implemented the auto-update feature. The program will now check for updates on launch and will notify you if there is a new version available.