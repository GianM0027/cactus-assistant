import json
import os
from datetime import datetime


# todo: aggiungere last interaction tag, if a file havent been accessed in X time, delete it

class CactusMemory:

    def __init__(self):
        self.memory_folder = "memory"

        self.user_reminders_key = "user_reminders"
        self.user_initialization_prompt_key = "user_initialization_prompt"
        self.user_name_key = "user_name"
        self.user_language_preference_key = "language_preference"
        self.user_voice_preference_key = "voice_preference"

        self.user_data_structure = {
            self.user_reminders_key: [],
            self.user_initialization_prompt_key: "",
            self.user_name_key: "",
            self.user_language_preference_key: "english",
            self.user_voice_preference_key: "male"
        }

    ################################################################################################################
    #
    # Auxiliary Methods
    #
    ################################################################################################################
    def _get_user_data_path(self, chat_id):
        return os.path.join(self.memory_folder, f"memory_chat_{chat_id}.json")

    def _ensure_memory_file(self, chat_id):
        """Ensures the memory file exists."""
        user_data_path = self._get_user_data_path(chat_id)

        if not os.path.exists(self.memory_folder):
            os.makedirs(self.memory_folder)

        if not os.path.exists(user_data_path):
            self.save_to_memory(chat_id, self.user_data_structure)

    def save_to_memory(self, chat_id, data):
        """Saves the provided data to the memory JSON file."""
        user_data_path = self._get_user_data_path(chat_id)
        with open(user_data_path, "w") as file:
            json.dump(data, file, indent=4)

    ################################################################################################################
    #
    # Set methods
    #
    ################################################################################################################
    def set_reminder(self, chat_id, reminder):
        user_data = self.get_user_data(chat_id)

        if isinstance(reminder, dict) and "date_time" in reminder:
            if isinstance(reminder["date_time"], datetime):
                reminder["date_time"] = reminder["date_time"].isoformat()  # Convert to string

        user_data[self.user_reminders_key].append(reminder)
        self.save_to_memory(chat_id, user_data)

    def set_user_initialization_prompt(self, chat_id, prompt):
        user_data = self.get_user_data(chat_id)
        user_data[self.user_initialization_prompt_key] = prompt
        self.save_to_memory(chat_id, user_data)

    def set_user_name(self, chat_id, name):
        user_data = self.get_user_data(chat_id)
        user_data[self.user_name_key] = name
        self.save_to_memory(chat_id, user_data)

    def set_user_language_preference(self, chat_id, language_preference):
        user_data = self.get_user_data(chat_id)
        user_data[self.user_language_preference_key] = language_preference
        self.save_to_memory(chat_id, user_data)

    def set_user_voice_preference(self, chat_id, voice_preference):
        user_data = self.get_user_data(chat_id)
        user_data[self.user_voice_preference_key] = voice_preference
        self.save_to_memory(chat_id, user_data)

    ################################################################################################################
    #
    # Get methods
    #
    ################################################################################################################
    def get_user_data(self, chat_id):
        self._ensure_memory_file(chat_id)
        user_data_path = self._get_user_data_path(chat_id)
        with open(user_data_path, "r") as file:
            return json.load(file)

    def get_all_users_data(self):
        users_data = {}
        for file in os.listdir(self.memory_folder):
            file_path = os.path.join(self.memory_folder, file)
            if file.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
                users_data[file.replace(".json", "")] = user_data
        return users_data

    def get_user_reminders(self, chat_id):
        user_data = self.get_user_data(chat_id)

        reminders = user_data.get(self.user_reminders_key, [])
        # Convert date_time back to datetime object
        for reminder in reminders:
            if isinstance(reminder, dict) and "date_time" in reminder:
                try:
                    reminder["date_time"] = datetime.fromisoformat(reminder["date_time"])
                except ValueError:
                    pass

        return reminders

    def get_user_initialization_prompt(self, chat_id):
        """Retrieves the user's initialization prompt."""
        user_data = self.get_user_data(chat_id)
        return user_data.get(self.user_initialization_prompt_key, "")

    def get_user_name(self, chat_id):
        """Retrieves the user's name."""
        user_data = self.get_user_data(chat_id)
        return user_data.get(self.user_name_key, "")

    def get_user_language_preference(self, chat_id):
        user_data = self.get_user_data(chat_id)
        return user_data.get(self.user_language_preference_key, "")

    def get_user_voice_preference(self, chat_id):
        user_data = self.get_user_data(chat_id)
        return user_data.get(self.user_voice_preference_key, "")
