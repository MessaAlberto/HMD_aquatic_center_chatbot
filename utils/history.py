FLAG_ACTION_MAP = {
    "confirm_transaction": "EXPECT_CONFIRMATION",
    "confirm_old_values": "EXPECT_CONFIRMATION",
    "offer_chioces": "EXPECT_SELECTION",
    "request_identity": "EXPECT_NAME SURNAME",
    "request_slot": "EXPECT_SLOT_VALUE",
}


class History():
    def __init__(self):
        self.messages = []
        self.last_system_action = None
        self.active_task = None
        self.flag = None

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_last_user_message(self):
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                return msg["content"]
        return None

    def get_last_bot_message(self):
        for msg in reversed(self.messages):
            if msg["role"] == "system":
                return msg["content"]
        return None

    def set_last_system_action(self, action):
        self.last_system_action = action

    def get_last_system_action(self):
        return self.last_system_action
    
    def set_active_task(self, task):
        self.active_task = task

    def get_active_task(self):
        return self.active_task
    
    def set_flag(self, action):
        self.flag = FLAG_ACTION_MAP.get(action, None)

    def get_flag(self):
        return self.flag