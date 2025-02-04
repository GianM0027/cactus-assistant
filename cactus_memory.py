import json

# todo: capire come gestire le conversazioni, quante ne salviamo? In base a cosa decidiamo come tenerle e recuperarle?

class CactusMemory:
    def __init__(self):
        with open("memory.json", "r") as file:
            self._memory = json.load(file)

        self.conversations = self._memory["conversations"]
        self.user_initialization_prompt = self._memory["user_initialization_prompt"]
        self.user_name = self._memory["user_name"]

    def store_conversation(self, message, response):
        self.conversations["user"].extend(message)
        self.conversations["cactus"].extend(response)
        self._memory["conversations"] = self.conversations
        self.save_to_memory()

    def set_user_initialization_prompt(self, new_initialization_prompt):
        self.user_initialization_prompt = new_initialization_prompt
        self._memory["user_initialization_prompt"] = new_initialization_prompt
        self.save_to_memory()

    def set_user_name(self, new_user_name):
        self.user_name = new_user_name
        self._memory["user_name"] = new_user_name
        self.save_to_memory()

    def save_to_memory(self):
        with open("memory.json", "w") as outfile:
            json.dump(self._memory, outfile, indent=4)
