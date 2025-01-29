from prompts import CACTUS_INSTRUCTIONS


class CactusMemory:
    def __init__(self, user_preference_prompt=""):
        self.conversations = {"user": [], "cactus": []}
        self.user_preference_prompt = user_preference_prompt
        self.user_name = ""

    def store_conversation(self, request, response):
        self.conversations["user"].append(request)
        self.conversations["cactus"].append(response)

    def get_conversations_chat_template(self, new_request):
        user_requests = [{"role": "user", "content": request} for request in self.conversations["user"]]
        cactus_responses = [{"role": "assistant", "content": response} for response in self.conversations["cactus"]]

        chat = []
        for i in range(len(user_requests)):
            chat.append(user_requests[i])
            chat.append(cactus_responses[i])
        chat.append({"role": "user", "content": new_request})

        chat_template = [
            {
                "role": "system",
                "content": CACTUS_INSTRUCTIONS + "\n" + self.user_preference_prompt,
            },
            chat
        ]

        return chat_template
