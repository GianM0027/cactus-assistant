import os
import json
from datetime import datetime


class CactusMemory:

    def __init__(self):
        self.memory_path = "local_memory.json"

        self.user_reminders_key = "user_reminders"
        self.user_initialization_prompt_key = "user_initialization_prompt"
        self.user_name_key = "user_name"
        self.user_timers_key = "timers"
        self.user_chat_id_key = "chat_id"

        self.user_data_structure = {
            self.user_reminders_key: [],
            self.user_timers_key: [],
            self.user_initialization_prompt_key: "",
            self.user_name_key: "",
            self.user_chat_id_key: "",
        }

        # Ensures the memory file exists.
        if not os.path.exists(self.memory_path):
            self.save_to_memory(data=self.user_data_structure)

    ################################################################################################################
    #
    # Auxiliary Methods
    #
    ################################################################################################################
    def save_to_memory(self, data):
        with open(self.memory_path, "w") as file:
            json.dump(data, file, indent=4)

    ################################################################################################################
    #
    # Set methods
    #
    ################################################################################################################
    def set_reminder(self, reminder):
        user_data = self.get_user_data()

        # conver datetime to JSON compatible format
        if isinstance(reminder, dict) and "date_time" in reminder:
            if isinstance(reminder["date_time"], datetime):
                reminder["date_time"] = reminder["date_time"].isoformat()

        user_data[self.user_reminders_key].append(reminder)
        self.save_to_memory(user_data)

    def set_timer(self, timer):
        user_data = self.get_user_data()

        if isinstance(timer, dict) and "date_time" in timer:
            if isinstance(timer["date_time"], datetime):
                timer["date_time"] = timer["date_time"].isoformat()

        user_data[self.user_timers_key].append(timer)
        self.save_to_memory(user_data)

    def set_user_initialization_prompt(self, prompt):
        user_data = self.get_user_data()
        user_data[self.user_initialization_prompt_key] = prompt
        self.save_to_memory(user_data)

    def set_user_name(self, name):
        user_data = self.get_user_data()
        user_data[self.user_name_key] = name
        self.save_to_memory(user_data)

    def set_chat_id(self, chat_id):
        user_data = self.get_user_data()
        user_data[self.user_chat_id_key] = chat_id
        self.save_to_memory(user_data)

    ################################################################################################################
    #
    # Get methods
    #
    ################################################################################################################
    def get_user_data(self):
        with open(self.memory_path, "r") as file:
            return json.load(file)

    def get_user_reminders(self):
        user_data = self.get_user_data()

        reminders = user_data.get(self.user_reminders_key, [])
        # Convert date_time back to datetime object
        for reminder in reminders:
            if isinstance(reminder, dict) and "date_time" in reminder:
                try:
                    reminder["date_time"] = datetime.fromisoformat(reminder["date_time"])
                except ValueError:
                    pass

        return reminders

    def get_user_chat_id(self):
        user_data = self.get_user_data()
        return user_data.get(self.user_chat_id_key, "")

    def get_user_timers(self):
        user_data = self.get_user_data()

        timers = user_data.get(self.user_timers_key, [])
        # Convert date_time back to datetime object
        for timer in timers:
            if isinstance(timer, dict) and "date_time" in timer:
                try:
                    timer["date_time"] = datetime.fromisoformat(timer["date_time"])
                except ValueError:
                    pass

        return timers

    def get_user_initialization_prompt(self):
        user_data = self.get_user_data()
        return user_data.get(self.user_initialization_prompt_key, "")

    def get_user_name(self):
        user_data = self.get_user_data()
        return user_data.get(self.user_name_key, "")
