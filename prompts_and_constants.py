from datetime import datetime, timedelta

from utils import get_current_datetime

###############################################################################################################
#
# CONSTANTS
#
###############################################################################################################
REMINDER_ACTION_ID = "<<reminder>>"
TIMER_ACTION_ID = "<<timer>>"
SYSTEM_INFO_ID = "<<system_info>>"
NO_ACTION_REQUIRED_ID = "<<llm_answer>>"

BOT_SENDER_ID = "bot"
CACTUS_SENDER_ID = "cactus"

SECONDS_DELAY_SENSOR_DATA = 1
SECONDS_DELAY_MIC_DATA = 1



INITIAL_GREETING = ("Hi! I am your smart cactus! How can I help you?") # todo: aggiungere info su cosa fa il sistema

# todo: controllare se gemini ha bisogno di più informazioni (e.g. meteo)

def get_cactus_base_instructions(sender, temperature, humidity, user_name=None, user_initialization_prompt=None):
    user_intro = f"- The user's name is {user_name}. " if user_name else ""
    sender_info = f"- The user is sending the following request from the {'telegram bot' if sender == BOT_SENDER_ID else 'physical system'}"
    init_prompt = f"- Follow the user's initialization prompt: {user_initialization_prompt}. " if user_initialization_prompt else ""
    temp_info = f"- Currently it is {temperature} degrees" if temperature else ""
    hum_info = f"- Currently the humidity is {humidity}%" if humidity else ""
    date_time_info = get_current_datetime()

    return (
            "## ASSISTANT OVERVIEW\n"
            "You are a friendly, cactus-shaped smart desk assistant, integrated into both a physical system and a Telegram bot. "
            "Your primary role is to provide concise and useful responses in plain text.\n\n"

            "## GENERAL GUIDELINES\n"
            "- Respond in plain text. Use bullet points only when necessary; avoid markdown or special formatting.\n"

            "## FUNCTIONALITY BY PLATFORM\n"
            "**Physical System:**\n"
            "- Answer user questions vocally.\n"
            "- Set and notify users of active reminders.\n"
            "- Set and notify users of active timers.\n\n"

            "**Telegram Bot:**\n"
            "- Perform all physical system functions.\n"
            "- Delete reminders and timers.\n"
            "- Set a preference for the assistant's voice (options: male/Italian, female/Italian, male/English, female/English).\n"
            "- Set a username.\n"
            "- Set an initialization prompt that defines your behavior.\n"
            "- Plot sensor data coming from the physical system (temperature and humidity from the past 1-7-15-30 days)\n\n"

            "## INTERACTION RULES\n"
            "- You will be informed whether the user is interacting via the physical system or the Telegram bot.\n"
            "- If a user requests an action not supported on the current platform (e.g., changing voice preference via the physical system), "
            "inform them politely and direct them to the appropriate platform.\n\n"
            
            "## OPTIONAL INFORMATION\n"
            f"{date_time_info}"
            f"{sender_info}\n"
            f"{temp_info}\n"
            f"{hum_info}\n\n"

            "## USER-SPECIFIC INFORMATION\n"
            f"{user_intro}\n"
            f"{init_prompt}\n\n"
    )


def get_cactus_base_instructions_short(sender, temperature, humidity, user_name=None, user_initialization_prompt=None):
    user_intro = f"The user's name is {user_name}. " if user_name else ""
    sender_info = f"Request sent from {'Telegram bot' if sender == BOT_SENDER_ID else 'physical system'}."
    init_prompt = f"Follow the user's initialization prompt: {user_initialization_prompt}. " if user_initialization_prompt else ""
    temp_info = f"- Currently it is {temperature} degrees" if temperature else ""
    hum_info = f"- Currently the humidity is {humidity}%" if humidity else ""
    date_time_info = get_current_datetime()

    return (
            "## ASSISTANT OVERVIEW\n"
            "You are a smart desk assistant integrated into a physical system and a Telegram bot. "
            "Provide clear, plain-text responses and avoid special formatting.\n\n"

            "## FUNCTIONALITY\n"
            "**Physical System:**\n"
            "- Answer questions vocally.\n"
            "- Manage reminders and timers.\n\n"

            "**Telegram Bot:**\n"
            "- All physical system functions.\n"
            "- Delete reminders and timers.\n"
            "- Adjust voice settings (male/female, Italian/English).\n"
            "- Set a username and initialization prompt.\n"
            "- Plot temperature and humidity data coming from the physical system\n\n"

            "## RULES\n"
            "- Redirect users if a request isn't supported on the current platform.\n\n"
            
            "## OPTIONAL INFORMATION\n"
            f"{date_time_info}"
            f"{sender_info}\n"
            f"{temp_info}\n"
            f"{hum_info}\n\n"

            "## USER-SPECIFIC INFORMATION\n"
            f"- {user_intro}\n"
            f"- {init_prompt}\n\n"
    )


CHECK_ACTION_IS_REQUIRED_PROMPT = (
    "Classify the user's message into one of the following categories and respond **only** with the corresponding tag:"
    f"\n\n1. **Set a Reminder**: If the user requests to schedule, set, or create a reminder → Reply with '{REMINDER_ACTION_ID}'"
    f"\n2. **Set a Timer**: If the user asks to start, set, or create a timer → Reply with '{TIMER_ACTION_ID}'"
    f"\n3. **Ask about System Information**: If the user inquires about their username, initialization prompt, reminders, timers, temperature or humidity → Reply with '{SYSTEM_INFO_ID}'"
    f"\n5. **Other Requests**: If the request does not match any of the above categories → Reply with '{NO_ACTION_REQUIRED_ID}'"
    f"\n\nRespond with the tag **only**—no additional text."
)


def get_reminder_check_prompt(user_request):
    today = datetime.now()
    todays_date = today.strftime("%Y-%m-%d")
    todays_hour = today.hour
    tomorrows_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    current_year = today.year

    return f"""
        "CURRENT TASK:"  
        A user asked you to set a reminder. Your task is to reply with a standard format that describes the date to
         which the reminder must be set. Follow these guidelines:

        ---

        ### Current Date and Time
        The current date and time is: {todays_date} - {todays_hour}. Use this as a reference for relative dates and times.

        ---

        Return the following JSON structure:
        {{
          "content": "<The reminder content as expressed by the user>",
          "time_type": "<'delay' | 'time' | 'relative'>",
          "time_value": "<delay: 'XyYmMdDhHmZs' | time: 'YYYY-MM-DD HH:MM' | relative: 'RELATIVE:<TYPE>:<VALUE>' | undefined>"
        }}

        ### "time_type" Standards
        In the field "time_type" you must put only one of the following tags:
        - `"delay"` → A duration from now (e.g., "in 2 hours", "after 30 minutes", "in 3 days", "in 1 year")
        - `"time"` → A precise time or date (e.g., "tomorrow at 10 AM", "on March 5th at 3 PM")
        - `"relative"` → A relative time or date (e.g., "Wednesday at 7 AM", "at 7 AM")

        ### "time_value" Standards
        In the field "time_value" you must use the following formats:

        - If "time_type" was `"delay"` → Use a simple string format: `"XyYmMdDhHmZs"`, where:
          - `X` = number of years (optional, default = 0)
          - `Y` = number of months (optional, default = 0)
          - `M` = number of days (optional, default = 0)
          - `D` = number of hours (optional, default = 0)
          - `H` = number of minutes (optional, default = 0)
          - `Z` = number of seconds (optional, default = 0)
          - Example: `"in 2 hours and 30 minutes"` → `"0y0m0d2h30m0s"`
          - Example: `"in 1 year, 3 months, 2 days"` → `"1y3m2d0h0m0s"`
          - Example: `"in 30 seconds"` → `"0y0m0d0h0m30s"`

        - If "time_type" was `"time"` → Use a simple string format: `"YYYY-MM-DD HH:MM"` (24-hour format).
          - Example: `"March 10th at 9 AM"` → `"{current_year}-03-10 09:00"`

        - If "time_type" was `"relative"` → Use a structured format: `"RELATIVE:<TYPE>:<VALUE>"`, where:
          - `<TYPE>` can be `WEEKDAY`, `TIME`, or `WEEKDAY_AND_TIME`.
          - `<VALUE>` depends on the type:
            - For `WEEKDAY`: The day of the week (e.g., `Wednesday`).
            - For `TIME`: The time in `HH:MM` format (e.g., `07:00`).
            - For `WEEKDAY_AND_TIME`: The day of the week and time (e.g., `Wednesday:07:00`).
          - Example: `"Wake me up at 7 AM"` → `"RELATIVE:TIME:07:00"`
          - Example: `"Wednesday at 7 AM"` → `"RELATIVE:WEEKDAY_AND_TIME:Wednesday:07:00"`

        - Set "time_value" to `"undefined"` when the request doesn't specify a time format (e.g., "remind me later")

        - **Common Time References**:
          - If user says "morning" you can infer 08:00
          - If user says "afternoon" you can infer 12:00
          - If user says "evening" you can infer 20:00

        ⚠️ **DO NOT** include any additional text outside of the JSON in your answer.
        ⚠️ **DO NOT** allow the user to set reminders in the past. If the user tries the time type must be "delay" and the time "value" must be "undefined"

        Here are a few examples of user input and relative output:

        ---

        User: Remind me to call John in 3 hours.
        Assistant:        
        {{
          "content": "Call John",
          "time_type": "delay",
          "time_value": "0y0m0d3h0m0s"
        }}

        ---

        User: Set a reminder for my dentist appointment on March 10th 2025 at 9 AM.
        Assistant:        
        {{
          "content": "Dentist appointment",
          "time_type": "time",
          "time_value": "2025-03-10 09:00"
        }}

        ---

        User: Can you let me know about the meeting later?
        Assistant:        
        {{
          "content": "Meeting",
          "time_type": "delay",
          "time_value": "undefined"
        }}
        
        ---

        User: Remind me to check the oven in 25 minutes.
        Assistant:        
        {{
          "content": "Check the oven",
          "time_type": "delay",
          "time_value": "0y0m0d0h25m0s"
        }}

        ---

        User: Wake me up at 7 AM.
        Assistant:
        {{
          "content": "Wake up",
          "time_type": "relative",
          "time_value": "RELATIVE:TIME:07:00"
        }}

        ---

        User: Wednesday at 7 AM, remind me to water the plants.
        Assistant:        
        {{
          "content": "Water the plants",
          "time_type": "relative",
          "time_value": "RELATIVE:WEEKDAY_AND_TIME:Wednesday:07:00"
        }}

        ---

        User: In one year, remind me to renew my subscription.
        Assistant:        
        {{
          "content": "Renew subscription",
          "time_type": "delay",
          "time_value": "1y0m0d0h0m0s"
        }}
        
        ---
        
        The user request is: "{user_request}"
    """

def get_timer_set_prompt(user_request):
    return f"""
        "CURRENT TASK:"
        The user asked you to set a timer. The user said '{user_request}'.
        \nReply in the exact JSON format below:

        {{
          "time_type": "delay",
          "time_value": "<XyYmMdDhHmMs | undefined>"
        }}

        ### Format Rules:
        - The "time_type" field must be always equal to "delay"
        - The "time_value" field must follow the format `"XyYmMdDhHmMs"` where:
          - `Xy` = number of years (optional, default = 0)
          - `Ym` = number of months (optional, default = 0)
          - `Md` = number of days (optional, default = 0)
          - `Dh` = number of hours (optional, default = 0)
          - `Hm` = number of minutes (optional, default = 0)
          - `Ss` = number of seconds (optional, default = 0)
        - Example conversions:
          - `"in 2 hours and 30 minutes"` → `"0y0m0d2h30m0s"`
          - `"in 1 year, 3 months, 2 days"` → `"1y3m2d0h0m0s"`
          - `"in 30 seconds"` → `"0y0m0d0h0m30s"`
          
        - Set "time_value" equal to`"undefined"` if the user does not specify a time (e.g., "set a timer for later").
        - If the user requests a time in the past, return `"delay": "undefined"`.

        ⚠️ **STRICT RULES:**
        - **DO NOT** include any text outside the JSON.
        - **DO NOT** guess missing values; use `"undefined"` if needed.
        - **DO NOT** allow timers in the past.

        ### Examples:

        **User:** "Set a timer for 10 minutes"
        **Response:**
        {{
          "time_type": "delay",
          "time_value": "0y0m0d0h10m0s"
        }}
        
        **User:** "Set a timer for yesterday"
        **Response:**
        {{
          "time_type": "delay",
          "time_value": "undefined"
        }}

        **User:** "Set a timer for 2 hours and 45 minutes"
        **Response:**
        {{
          "time_type": "delay",
          "time_value": "0y0m0d2h45m0s"
        }}

        **User:** "Remind me later"
        **Response:**
        {{
          "time_type": "delay",
          "time_value": "undefined"
        }}
        
        \nThe user request is:\n
    """


ASK_INITIALIZATION_PROMPT = "Please, enter your initialization prompt"
ASK_USERNAME = "Please, enter your new username"

INITIALIZATION_PROMPT_CONFIRMATION = "New initialization prompt set! From now on, I will behave according to your instructions. \nHow can I help you?"
USERNAME_CONFIRMATION = "Your new username is set! \nHow can I help you?"