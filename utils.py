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

#todo: check carefully (test)
def extract_exact_datetime(llm_output, bot, chat_id):
    time_type = llm_output.get("time_type")
    time_value = llm_output.get("time_value")

    if time_value == "undefined":
        return None

    # consider seconds for the timer, don't consider seconds for reminders
    today = datetime.now().replace(microsecond=0)

    if time_type == "time":
        # no reminders in the past and no reminders for less than 1 minute
        time_value_in_the_past = datetime.strptime(time_value, "%Y-%m-%d %H:%M") < datetime.now()
        if time_value_in_the_past:
            bot.send_message(chat_id, "Sorry, you can't set a reminder in the past, is there anything else I can do for you?")
            return None

        return datetime.strptime(time_value, "%Y-%m-%d %H:%M")

    elif time_type == "delay":
        match = re.match(r"(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", time_value)
        if match:
            years, months, days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())

            target_date = today + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            target_date = target_date.replace(year=today.year + years)

            time_value_in_the_past = target_date < datetime.now()
            if time_value_in_the_past:
                bot.send_message(chat_id,
                                 "Sorry, you can't set a reminder in the past, is there anything else I can do for you?")
                return None

            return target_date

    elif time_type == "relative":
        parts = time_value.split(":")
        rel_type, *rel_value = parts[1:]

        if rel_type == "TIME":
            target_time = datetime.strptime(rel_value[0], "%H:%M").time()
            target_datetime = datetime.combine(today.date(), target_time)
            if target_datetime <= today:
                target_datetime += timedelta(days=1)

            time_value_in_the_past = target_datetime < datetime.now()
            if time_value_in_the_past:
                bot.send_message(chat_id,
                                 "Sorry, you can't set a reminder in the past, is there anything else I can do for you?")
                return None

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


def parse_time_delay(time_str):
    match = re.match(r"(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", str(time_str))
    if match:
        years, months, days, hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    else:
        return None

    # Build the natural language description
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")

    # Join the parts with commas and 'and'
    if len(parts) == 0:
        return "0 seconds"
    elif len(parts) == 1:
        return parts[0]
    else:
        return ', '.join(parts[:-1]) + ' and ' + parts[-1]
