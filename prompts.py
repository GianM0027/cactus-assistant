from datetime import datetime, timedelta

INITIAL_GREETING = (
    "Hi! I am your smart cactus!\n"
    "From here you can:"
    "\n- Set the address of the connection your cactus assistant will be connected to."
    "\n- Chat with the assistant and obtain written responses."
    "\n- Set the behavior of your assistant."
    "\n- Access, modify or delete the assistant behavioral prompts and memory.json.")

CACTUS_BASE_INSTRUCTIONS = (
    "You are a cactus-shaped smart desk assistant who provides concise, useful responses in plain text. "
    "You can only use bullet points when necessary, no other formatting is allowed. "
    "Your core capability beyond standard LLM functions is: "
    "\n- setting reminders when users request them. "
    "\nFor requests outside your abilities (like physical actions or impossible tasks), politely explain your limitations. "
    "Example: If asked to cook food, set reminders for the past or other absurd requests, explain you cannot perform these tasks. "
    "Answer normally all questions that don't require physical actions or computational efforts."
)

CHECK_ACTION_IS_REQUIRED_PROMPT = (
    CACTUS_BASE_INSTRUCTIONS +
    "\n\nYour task now is to assess whether the user is asking you to perform one of the actions above or is making another request."
    "\n- If the user is asking to set a reminder, reply with <<reminder>>"
    "\n\nIf the user is not asking you to perform an action, normally reply to their request. The user request is:\n"
)

def get_reminder_check_prompt():
    today = datetime.now()
    todays_date = today.strftime("%Y-%m-%d")
    todays_hour = today.hour
    tomorrows_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    current_year = today.year

    return f"""
        You are tasked with extracting structured information from user messages regarding reminders.
        Your job is to analyze a given user request and determine whether the user is asking to set a reminder.
        Then reply with the standard format described below

        ---

        ### Current Date and Time
        The current date and time is: {todays_date} {todays_hour}. Use this as a reference for relative dates and times.

        ---

        If the user **is not** asking to set a reminder, return the following JSON:
        {{
          "action_required": false
        }}

        If the user **is** asking to set a reminder, return the following JSON structure:
        {{
          "action_required": true,
          "content": "<The reminder content as expressed by the user>",
          "time": {{
            "type": "<'delay' | 'time' | 'relative'>",
            "value": "<delay: 'XyYmMdDhHmMs' | time: 'YYYY-MM-DD HH:MM' | relative: 'RELATIVE:<TYPE>:<VALUE>' | undefined>"
          }}
        }}

        ### Time "type" Standards
        In the field "type" you must put only one of the following tags:
        - `"delay"` → A duration from now (e.g., "in 2 hours", "after 30 minutes", "in 3 days", "in 1 year")
        - `"time"` → A precise time or date (e.g., "tomorrow at 10 AM", "on March 5th at 3 PM")
        - `"relative"` → A relative time or date (e.g., "Wednesday at 7 AM", "at 7 AM")

        ### Time "value" Standards
        In the field "value" you must use the following formats:

        - If time "type" was `"delay"` → Use a simple string format: `"XyYmMdDhHmM"`, where:
          - `X` = number of years (optional, default = 0)
          - `Y` = number of months (optional, default = 0)
          - `M` = number of days (optional, default = 0)
          - `H` = number of hours (optional, default = 0)
          - `m` = number of minutes (optional, default = 0)
          - Example: `"in 2 hours and 30 minutes"` → `"0y0m0d2h30m0s"`
          - Example: `"in 1 year, 3 months, 2 days and 3 seconds"` → `"1y3m2d0h0m3s"`

        - If time "type" was `"time"` → Use a simple string format: `"YYYY-MM-DD HH:MM"` (24-hour format).
          - Example: `"March 10th at 9 AM"` → `"{current_year}-03-10 09:00"`
          - Example: `"tomorrow at 9 PM"` → `"{tomorrows_date} 21:00"`

        - If time "type" was `"relative"` → Use a structured format: `"RELATIVE:<TYPE>:<VALUE>"`, where:
          - `<TYPE>` can be `WEEKDAY`, `TIME`, or `WEEKDAY_AND_TIME`.
          - `<VALUE>` depends on the type:
            - For `WEEKDAY`: The day of the week (e.g., `Wednesday`).
            - For `TIME`: The time in `HH:MM` format (e.g., `07:00`).
            - For `WEEKDAY_AND_TIME`: The day of the week and time (e.g., `Wednesday:07:00`).
          - Example: `"Wake me up at 7 AM"` → `"RELATIVE:TIME:07:00"`
          - Example: `"Wednesday at 7 AM"` → `"RELATIVE:WEEKDAY_AND_TIME:Wednesday:07:00"`

        - `"undefined"` → When the request doesn't specify a time format (e.g., "remind me later")

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
          "action_required": true,
          "content": "Call John",
          "time": {{
            "type": "delay",
            "value": "0y0m0d3h0m0s"
          }}
        }}

        ---

        User: Set a reminder for my dentist appointment on March 10th 2025 at 9 AM.
        Assistant:
        {{
          "action_required": true,
          "content": "Dentist appointment",
          "time": {{
            "type": "time",
            "value": "2025-03-10 09:00"
          }}
        }}

        ---

        User: Can you let me know about the meeting later?
        Assistant:
        {{
          "action_required": true,
          "content": "Meeting",
          "time": {{
            "type": "delay",
            "value": "undefined"
          }}
        }}

        ---

        User: I need to buy groceries.
        Assistant:
        {{
          "action_required": false
        }}

        ---

        User: Remind me to check the oven in 25 minutes.
        Assistant:
        {{
          "action_required": true,
          "content": "Check the oven",
          "time": {{
            "type": "delay",
            "value": "0y0m0d0h25m"
          }}
        }}

        ---

        User: Wake me up at 7 AM.
        Assistant:
        {{
          "action_required": true,
          "content": "Wake up",
          "time": {{
            "type": "relative",
            "value": "RELATIVE:TIME:07:00"
          }}
        }}

        ---

        User: Wednesday at 7 AM, remind me to water the plants.
        Assistant:
        {{
          "action_required": true,
          "content": "Water the plants",
          "time": {{
            "type": "relative",
            "value": "RELATIVE:WEEKDAY_AND_TIME:Wednesday:07:00"
          }}
        }}

        ---

        User: In one year, remind me to renew my subscription.
        Assistant:
        {{
          "action_required": true,
          "content": "Renew subscription",
          "time": {{
            "type": "delay",
            "value": "1y0m0d0h0m0s"
          }}
        }}

        ---

        User: I'll do it in a few hours.
        Assistant:
        {{
          "action_required": false
        }}
    """

ASK_INITIALIZATION_PROMPT = "Please, enter your initialization prompt"
ASK_USERNAME = "Please, enter your new username"

INITIALIZATION_PROMPT_CONFIRMATION = "New initialization prompt set! From now on, I will behave according to your instructions. \nHow can I help you?"
USERNAME_CONFIRMATION = "Your new username is set! \nHow can I help you?"