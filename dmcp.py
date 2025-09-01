from fastmcp import FastMCP, Context
import uvicorn.config
from schedule import Schedule, People, noone, Event, Events
import os
from pathlib import Path
import dotenv
from datetime import date, time
import logging
import traceback

def format_error_message(e: Exception) -> str:
    """Format error message for logging."""
    logging.exception(e)
    return f"Exception raised: {str(e)}. Tell the user to contact the developer or if he's a developer, to debug the issue.\n{traceback.format_exc()}"


with Path("instructions.md").open("r", encoding="utf-8") as f:
    instructions = f.read()

mcp = FastMCP("NARFU schedule fetcher", instructions=instructions)


@mcp.resource("app://instructions")
def instructions() -> str:
    """Get instructions for the bot."""
    #return INSTRUCTIONS
    with Path("instructions.md").open("r", encoding="utf-8") as f:
        instructions = f.read()
    return instructions

class ScheduleBot:
    # Unified error message
    ERROR_MESSAGE = "Exception raised: {}. Tell the user to contact the developer or if he's a developer, to debug the issue."
    
    def __init__(self):
        # Configure logging
        logging.basicConfig(filename="mcp.log")
        # put an info about current working directory
        logging.info(f"Current working directory: {os.getcwd()}")
        # Create MCP server instance
        
        # Load environment variables
        dotenv.load_dotenv()
        self.email = os.getenv("MODEUS_EMAIL")
        self.password = os.getenv("MODEUS_PASSWORD")
        if not self.email or not self.password:
            logging.error("Email or password not set in environment variables")
            exit(1)
        
        # Initialize data structures
        self.people_path = Path("people.json")
        self.people = self._load_people()
        self.me = self.people[0] if self.people else noone
        self.schedule = Schedule(self.email, self.password, self.me)
        self.results = People()  # For name search results
        self.who_goes_results = People()  # For who_goes pagination
        self.last_schedule = Events()  # For schedule pagination
        
        # Register all tools
        self._register_tools()
    
    def _load_people(self):
        if self.people_path.exists():
            return People.from_cache(str(self.people_path))
        people = People()
        people.to_cache(str(self.people_path))
        return people
    
    def _register_tools(self):
        """Register all methods as MCP tools"""
        mcp.tool()(self.check_auth)
        mcp.tool()(self.search_name)
        mcp.tool()(self.set_person)
        mcp.tool()(self.get_schedule)
        mcp.tool()(self.what_is_now)
        mcp.tool()(self.get_next)
        mcp.tool()(self.who_goes)
        mcp.tool()(self.get_who_goes_page)
        mcp.tool()(self.clear_who_goes)
        mcp.tool()(self.get_schedule_page)
        mcp.tool()(self.debug)  # uncomment for debug tool
        mcp.tool()(self.search_event)
        mcp.tool()(self.get_friends_schedule)
    
    def check_auth(self, ctx: Context) -> str:
        """Check if the user's name is set in the schedule client. Must be called in new chat contexts prior to any other schedule tool. If the user is authorized, read user's name and info in the language you are talking."""
        req = ctx.get_http_request()  # starlet request
        head = req.headers
        username = head.get("username", "unknown")
        user_id = head.get("user_id", "unknown")
        # either username xor user id must be set, id is priority
        if user_id != "unknown":
            r = self.set_person(user_id)
            

        if self.me == noone
            logging.error("User is not set in the schedule client")
            return {
                "status": "not authorized",
                "message": "User is not set in the schedule client. Please use the search_name tool to set your name.",
            }
        return {
            "status": "ok",
            "person_data": self.me.json(),
            "message": "The user is authorized. Don't forget to read out the user's info and check the instructions resource.",
        }
    
    def search_name(self, name: str) -> str:
        """Search the user's name in the schedule api. This tool is called if the user is not autherized or gets the schedule of a friend."""
        if not name:
            return "Name is empty"
        try:
            self.results = self.schedule.search_person(name, by_id=False)
            if not self.results:
                return "No results found. Prompt the user for his name again."
            return self.results.json()
        except Exception as e:
            return format_error_message(e)
    
    def set_person(self, id: str) -> str:
        """Set the user's name in the schedule client after the user has been asked to choose the right one. It is not used to get friends' schedules."""
        if not self.results:
            return {
                "status": "not found",
                "message": "No results found. Prompt the user for his name again.",
            }
        if not id:
            return {
                "status": "not found",
                "message": "ID is empty. Set the person ID as an argument to this tool.",
            }
        try:
            person = self.results.get_person_by_id(id)
            if not person or person == noone:
                return {
                    "status": "not found",
                    "message": "Person not found. Prompt the user for his name again.",
                }
            self.schedule.set_person(person)
            return {
                "status": "ok",
                "message": "User is set in the schedule client",
                "person_data": person.json(),
            }
        except Exception as e:
            return format_error_message(e)
    
    def get_schedule(self, start_date: str, end_date: str) -> str:
        """Get the schedule for the current user between dates (ISO format). Returns the schedule in JSON. Not used to get friends' schedules."""
        try:
            if not start_date or not end_date:
                return "Start date or end date is empty"
            start_date = date.fromisoformat(start_date)
            end_date = date.fromisoformat(end_date)
            self.schedule.overlap = noone
            self.schedule.get_only_friends = False
            self.last_schedule = self.schedule(start_date, end_date)
            if len(self.last_schedule) == 0:
                return "There are no events in the specified range"
            if len(self.last_schedule) > 30:
                return "There are too many events in the specified range. Please narrow it down using pagination tools."
            return self.last_schedule.json()
        except Exception as e:
            return format_error_message(e)
    
    def get_schedule_page(self, page: int = 0, page_size: int = 25) -> str:
        """Get paginated schedule results. Page numbers start at 0."""
        try:
            if not self.last_schedule:
                return "No schedule loaded. Call get_schedule first."
            
            total = len(self.last_schedule)
            start = page * page_size
            end = start + page_size
            
            if start >= total or start < 0:
                if page < 0:
                    return "Did you ever see a universe with negative pages? I don't think so."
                return "Page number out of range"
            
            paginated = {
                "events": [event.json() for event in self.last_schedule[start:end]],
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": end < total
            }
            return str(paginated)
        except Exception as e:
            return format_error_message(e)
    
    def what_is_now(self) -> str:
        """Get the current event or status for the user."""
        try:
            schedule_data = self.schedule.now
            if self.schedule.on_break:
                return "The user is on break"
            elif self.schedule.on_non_working_time:
                return "The user is not studying now"
            return schedule_data.json()  # since it's only one event, we don't need pagination
        except Exception as e:
            return format_error_message(e)
    
    def get_next(self) -> str:
        """Get the next event for the current user."""
        try:
            schedule_data = self.schedule.next
            if not schedule_data:
                return "No next event found"
            return schedule_data.json()
        except Exception as e:
            return format_error_message(e)
    
    def who_goes(self, event_id: str) -> str:
        """Fetch list of people attending an event and store for pagination."""
        try:
            fe = Event(event_id, 0, date.today(), time(0, 0), time(0, 0), 
                "none", "none", "none", "none", "none", "none")
            self.who_goes_results = self.schedule.who_goes(fe)
            if not self.who_goes_results:
                return "No one is going to this event"
            return self.get_who_goes_page(0)  # Return first page by default
        except Exception as e:
            return format_error_message(e)
    
    def get_who_goes_page(self, page: int = 0, page_size: int = 10) -> str:
        """Get paginated who_goes results. Page numbers start at 0."""
        try:
            if not self.who_goes_results:
                return "No who_goes results available. Call who_goes first."
            
            total = len(self.who_goes_results)
            start = page * page_size
            end = start + page_size
            
            if start >= total:
                return "Page number out of range"
            
            paginated = {
                "people": [person.json() for person in self.who_goes_results[start:end]],
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": end < total
            }
            return str(paginated)
        except Exception as e:
            return format_error_message(e)
    
    def clear_who_goes(self) -> str:
        """Clear the stored who_goes results to free memory."""
        self.who_goes_results = People()
        return "Who_goes results cleared"
    
    # debug tool:
    def debug(self) -> str:
        """Debug tool to check the current state of the bot."""
        try:
            return {
                "current_working_directory": os.getcwd(),
                "people_path": str(self.people_path),
                "me": self.me.json(),
            }
        except Exception as e:
            return self.ERROR_MESSAGE.format(str(e))

    def search_event(self, query: str) -> str:
        """Search for an event in the schedule."""
        try:
            if not query:
                return "Query is empty"
            events = self.last_schedule.get_events_by_query(query)
            if len(events) == 0:
                return "No events found"
            return events.json()
        except Exception as e:
            return format_error_message(e)

    def get_friends_schedule(self, friend_id: str, start_date: str, end_date: str) -> str:
        """Get the schedule for a friend or another person. Before using this tool, you need to get the friend's ID using the search_name tool."""
        try:
            if not friend_id or not start_date or not end_date:
                return "Friend name, start date or end date is empty"
            friend = self.people.get_person_by_id(friend_id)
            if friend is noone:
                return "Friend not found"
            self.schedule.overlap = friend
            self.schedule.get_only_friends = True
            start_date = date.fromisoformat(start_date)
            end_date = date.fromisoformat(end_date)
            if start_date > end_date:
                return "Start date is after end date"
            events = self.schedule(start_date, end_date)
            if len(events) == 0:
                return "There are no events in the specified range"
            self.last_schedule = events
            if len(self.last_schedule) > 30:
                return "There are too many events in the specified range. Please narrow it down using pagination tools."
            return events.json()
        except Exception as e:
            return format_error_message(e)



# Create and run the bot
# name is not main, the server imports this file.
bot = ScheduleBot()
# if not name is main, it will autorun the server using stdio protocol
if __name__ == "__main__":
    # it means that the server is run directly via a systemd service, so we need http server
    logging.info("Running the bot as a streamable HTTP server")
    uvicorn_config = dict(forwarded_allow_ips="*", proxy_headers=True, root_path="https://deniz.r1oaz.ru/mcp_schedule")
    mcp.run("streamable-http", host = "0.0.0.0", port = 4000, path = "/", uvicorn_config = uvicorn_config)