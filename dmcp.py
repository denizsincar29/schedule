from fastmcp import FastMCP, Context
import uvicorn.config
from schedule import Schedule, People, noone, Event, Events
import os
from pathlib import Path
import dotenv
from datetime import date, time
import logging
import traceback

import json

def create_success_response(message: str, data: dict = None) -> str:
    """Create a standardized success JSON response."""
    response = {"status": "ok", "message": message}
    if data:
        response.update(data)
    return json.dumps(response, ensure_ascii=False)

def create_error_response(message: str, error_code: str = "error") -> str:
    """Create a standardized error JSON response."""
    return json.dumps({"status": "error", "error_code": error_code, "message": message})

def format_error_message(e: Exception) -> str:
    """Format error message for logging."""
    logging.exception(e)
    return create_error_response(f"Exception raised: {str(e)}. Tell the user to contact the developer or if he's a developer, to debug the issue.\n{traceback.format_exc()}", "exception")


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
        # self.people = self._load_people()
        self.me = noone
        self.schedule = Schedule(self.email, self.password, self.me)
        self.results = People()  # For name search results
        self.who_goes_results = People()  # For who_goes pagination
        self.last_schedule = Events()  # For schedule pagination
        
        # Register all tools
        self._register_tools()
    
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
        req = ctx.get_http_request()
        head = req.headers
        user_id = head.get("user_id")
        username = head.get("username")

        if not user_id and not username:
            return create_error_response("User not identified. Provide user_id or username in headers.", "auth_failed")

        try:
            if user_id:
                people = self.schedule.search_person(user_id, by_id=True)
            else:
                people = self.schedule.search_person(username, by_id=False)

            if not people:
                return create_error_response("User not found.", "auth_failed")

            self.me = people[0]
            self.schedule.set_person(self.me)
            return create_success_response("User authorized successfully.", {"person_data": self.me.json()})
        except Exception as e:
            return format_error_message(e)
    
    def search_name(self, name: str) -> str:
        """Search the user's name in the schedule api. This tool is called if the user is not autherized or gets the schedule of a friend."""
        if not name:
            return create_error_response("Name is empty", "empty_name")
        try:
            self.results = self.schedule.search_person(name, by_id=False)
            if not self.results:
                return create_error_response("No results found. Prompt the user for his name again.", "no_results")
            return create_success_response("Found people", {"people": self.results.json()})
        except Exception as e:
            return format_error_message(e)
    
    def set_person(self, id: str) -> str:
        """Set the user's name in the schedule client after the user has been asked to choose the right one. It is not used to get friends' schedules."""
        if not self.results:
            return create_error_response("No results found. Prompt the user for his name again.", "no_results")
        if not id:
            return create_error_response("ID is empty. Set the person ID as an argument to this tool.", "empty_id")
        try:
            person = self.results.get_person_by_id(id)
            if not person or person == noone:
                return create_error_response("Person not found. Prompt the user for his name again.", "not_found")
            self.schedule.set_person(person)
            return create_success_response("User is set in the schedule client", {"person_data": person.json()})
        except Exception as e:
            return format_error_message(e)
    
    def get_schedule(self, start_date: str, end_date: str) -> str:
        """Get the schedule for the current user between dates (ISO format). Returns the schedule in JSON. Not used to get friends' schedules."""
        try:
            if not start_date or not end_date:
                return create_error_response("Start date or end date is empty", "empty_date")
            start_date = date.fromisoformat(start_date)
            end_date = date.fromisoformat(end_date)
            self.schedule.overlap = noone
            self.schedule.get_only_friends = False
            self.last_schedule = self.schedule(start_date, end_date)
            if len(self.last_schedule) == 0:
                return create_success_response("There are no events in the specified range", {"events": []})
            if len(self.last_schedule) > 30:
                return create_success_response("There are too many events in the specified range. Please narrow it down using pagination tools.", {"events": self.last_schedule.json(), "pagination_required": True})
            return create_success_response("Schedule retrieved successfully", {"events": self.last_schedule.json()})
        except Exception as e:
            return format_error_message(e)

    def get_schedule_page(self, page: int = 0, page_size: int = 25) -> str:
        """Get paginated schedule results. Page numbers start at 0."""
        try:
            if not self.last_schedule:
                return create_error_response("No schedule loaded. Call get_schedule first.", "no_schedule_loaded")
            
            total = len(self.last_schedule)
            start = page * page_size
            end = start + page_size
            
            if start >= total or start < 0:
                if page < 0:
                    return create_error_response("Did you ever see a universe with negative pages? I don't think so.", "invalid_page")
                return create_error_response("Page number out of range", "page_out_of_range")
            
            paginated = {
                "events": [event.json() for event in self.last_schedule[start:end]],
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": end < total
            }
            return create_success_response("Paginated schedule retrieved successfully", paginated)
        except Exception as e:
            return format_error_message(e)

    def what_is_now(self) -> str:
        """Get the current event or status for the user."""
        try:
            schedule_data = self.schedule.now
            if self.schedule.on_break:
                return create_success_response("The user is on break")
            elif self.schedule.on_non_working_time:
                return create_success_response("The user is not studying now")
            return create_success_response("Current event retrieved", {"event": schedule_data.json()})
        except Exception as e:
            return format_error_message(e)

    def get_next(self) -> str:
        """Get the next event for the current user."""
        try:
            schedule_data = self.schedule.next
            if not schedule_data:
                return create_success_response("No next event found")
            return create_success_response("Next event retrieved", {"event": schedule_data.json()})
        except Exception as e:
            return format_error_message(e)

    def who_goes(self, event_id: str) -> str:
        """Fetch list of people attending an event and store for pagination."""
        try:
            fe = Event(event_id, 0, date.today(), time(0, 0), time(0, 0), 
                "none", "none", "none", "none", "none", "none")
            self.who_goes_results = self.schedule.who_goes(fe)
            if not self.who_goes_results:
                return create_success_response("No one is going to this event", {"people": []})
            return self.get_who_goes_page(0)  # Return first page by default
        except Exception as e:
            return format_error_message(e)

    def get_who_goes_page(self, page: int = 0, page_size: int = 10) -> str:
        """Get paginated who_goes results. Page numbers start at 0."""
        try:
            if not self.who_goes_results:
                return create_error_response("No who_goes results available. Call who_goes first.", "no_results")
            
            total = len(self.who_goes_results)
            start = page * page_size
            end = start + page_size
            
            if start >= total:
                return create_error_response("Page number out of range", "page_out_of_range")
            
            paginated = {
                "people": [person.json() for person in self.who_goes_results[start:end]],
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": end < total
            }
            return create_success_response("Paginated who_goes results retrieved", paginated)
        except Exception as e:
            return format_error_message(e)

    def clear_who_goes(self) -> str:
        """Clear the stored who_goes results to free memory."""
        self.who_goes_results = People()
        return create_success_response("Who_goes results cleared")

    def debug(self) -> str:
        """Debug tool to check the current state of the bot."""
        try:
            data = {
                "current_working_directory": os.getcwd(),
                "people_path": str(self.people_path),
                "me": self.me.json(),
            }
            return create_success_response("Debug information retrieved", data)
        except Exception as e:
            return format_error_message(e)

    def search_event(self, query: str) -> str:
        """Search for an event in the schedule."""
        try:
            if not query:
                return create_error_response("Query is empty", "empty_query")
            events = self.last_schedule.get_events_by_query(query)
            if len(events) == 0:
                return create_success_response("No events found", {"events": []})
            return create_success_response("Events found", {"events": events.json()})
        except Exception as e:
            return format_error_message(e)

    def get_friends_schedule(self, friend_id: str, start_date: str, end_date: str) -> str:
        """Get the schedule for a friend or another person. Before using this tool, you need to get the friend's ID using the search_name tool."""
        try:
            if not friend_id or not start_date or not end_date:
                return create_error_response("Friend name, start date or end date is empty", "missing_parameters")

            # Search for the friend by ID
            friend_results = self.schedule.search_person(friend_id, by_id=True)
            if not friend_results:
                return create_error_response("Friend not found", "friend_not_found")

            friend = friend_results[0]
            self.schedule.overlap = friend
            self.schedule.get_only_friends = True
            start_date = date.fromisoformat(start_date)
            end_date = date.fromisoformat(end_date)
            if start_date > end_date:
                return create_error_response("Start date is after end date", "invalid_date_range")
            events = self.schedule(start_date, end_date)
            if len(events) == 0:
                return create_success_response("There are no events in the specified range", {"events": []})
            self.last_schedule = events
            if len(self.last_schedule) > 30:
                return create_success_response("There are too many events in the specified range. Please narrow it down using pagination tools.", {"events": events.json(), "pagination_required": True})
            return create_success_response("Friend's schedule retrieved successfully", {"events": events.json()})
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