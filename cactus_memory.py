import json

# todo: capire come gestire le conversazioni, quante ne salviamo? In base a cosa decidiamo come tenerle e recuperarle?

class CactusMemory:
    def __init__(self):
        self._conversations = {"user": [], "cactus": []}
        self._user_initialization_prompt = ""
        self._user_name = ""

        self._chat_id = None

    def set_chat_id(self, chat_id):
        self._chat_id = chat_id

    def store_conversation(self, message, response):
        self._conversations["user"].extend(message)
        self._conversations["cactus"].extend(response)
        self.save_to_memory()

    def set_user_initialization_prompt(self, new_initialization_prompt):
        self._user_initialization_prompt = new_initialization_prompt
        self.save_to_memory()

    def set_user_name(self, new_user_name):
        self._user_name = new_user_name
        self.save_to_memory()

    def get_conversation(self):
        return self._conversations

    def get_user_initialization_prompt(self):
        return self._user_initialization_prompt

    def get_user_name(self):
        return self._user_name

    def save_to_memory(self):
        # User updated data (without extra nesting)
        dict_to_save = {
            "conversations": self._conversations,
            "user_initialization_prompt": self._user_initialization_prompt,
            "user_name": self._user_name
        }

        # Load the existing JSON memory
        try:
            with open("memory.json", "r") as file:
                json_memory = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            json_memory = {}  # Initialize empty dictionary if file is missing or invalid

        # Correctly update the chat ID entry
        json_memory[str(self._chat_id)] = dict_to_save

        # Save the updated JSON file
        with open("memory.json", "w") as outfile:
            json.dump(json_memory, outfile, indent=4)

