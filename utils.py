from datetime import datetime, timedelta
import re

def extract_between_braces(text):
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1:
        return text[start:end + 1]
    return None

def format_datetime_natural(date_time):
    day = date_time.strftime("%d").lstrip("0")
    month = date_time.strftime("%B")
    time = date_time.strftime("%H:%M")

    return f"For {day} {month} at {time}. Is this correct?"

def extract_exact_datetime(llm_output):
    if not llm_output.get("action_required"):
        return None

    time = llm_output.get("time")

    if time["value"] == "undefined":
        return "undefined"

    today = datetime.now()
    time_data = llm_output.get("time", {})
    time_type = time_data.get("type")
    time_value = time_data.get("value")

    if time_type == "time":
        return datetime.strptime(time_value, "%Y-%m-%d %H:%M")

    elif time_type == "delay":
        match = re.match(r"(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time_value)
        if match:
            years, months, days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
            target_date = today + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            target_date = target_date.replace(year=today.year + years)
            return target_date

    elif time_type == "relative":
        parts = time_value.split(":")
        rel_type, *rel_value = parts[1:]

        if rel_type == "TIME":
            target_time = datetime.strptime(rel_value[0], "%H:%M").time()
            target_datetime = datetime.combine(today.date(), target_time)
            if target_datetime <= today:
                target_datetime += timedelta(days=1)
            return target_datetime

        elif rel_type == "WEEKDAY":
            target_weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(
                rel_value[0])
            days_ahead = (target_weekday - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

        elif rel_type == "WEEKDAY_AND_TIME":
            target_weekday, target_time_str = rel_value
            target_time = datetime.strptime(target_time_str, "%H:%M").time()
            target_weekday = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(
                target_weekday)
            days_ahead = (target_weekday - today.weekday()) % 7
            if days_ahead == 0 and datetime.combine(today.date(), target_time) <= today:
                days_ahead = 7
            return datetime.combine(today.date() + timedelta(days=days_ahead), target_time)

    return None