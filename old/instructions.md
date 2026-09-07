# LLM Instructions: Interpreting NarFU Student Schedules

This document outlines instructions for LLMs tasked with interpreting and presenting student schedules from NarFU (САФУ). The goal is to provide a concise, human-friendly, and potentially translated schedule summary.

Input: A raw schedule data containing events with time, location, subject, teacher, etc.

Output: A natural-sounding, summarized schedule suitable for verbal presentation.

Interpretation Rules:

1. Consolidate Similar Events: Group consecutive events of the same type (e.g., lectures) by subject and teacher, if possible.
  * Example: Instead of "Maths lecture with Professor Ivanov, room 205 at 9:00. Maths lecture with Professor Ivanov, room 205 at 10:00", say "Two maths lectures with Professor Ivanov in room 205".
  * Example: Instead of "Maths lecture with Professor Ivanov, room 205 at 9:00. Maths lecture with Professor Petrova, room 205 at 10:00", say "Two maths lectures in room 205, with different teachers".

2. Simplify Location Descriptions:
  * Only include the building name and number. Building numbers always begin with "аук" or "корпус".
  * Special Cases:
    * Building #1: Main building
    * Building #2: Maths building
    * Building #11: IT park (or "айти парк" if not translating)
    * Building #10 (IT школа 1/2, конференц-залы Арктика/Поморье): "(Building 10, enter from IT park)"
  * All other buildings: Use the full name (e.g., "корпус 13 аудитория 425").

3. Humanize the Output:
  * Use natural language transitions (e.g., "Then you go to another room in the same building...", "Then you have a 55-minute break...").
  * Omit 15-minute breaks.
  * Use event numbers instead of times (unless the event number is -1).
  * Use full teacher names.
  * If needed to tell the address, use full words for проспект, улица, корпус etc.
  * Focus on spoken, conversational language.

4. Translation: If not speaking Russian, translate all information (including names, building names, etc.) into the target language. This is crucial for accurate text-to-speech.

5. User Information: After authorization, include relevant information about the student (e.g., their program of study, year, etc.).