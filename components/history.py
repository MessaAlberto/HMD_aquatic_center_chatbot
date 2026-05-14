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
            if msg["role"] == "assistant":
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

    def get_flag(self):
        return self.flag

    def get_last_n_messages(self, n=4):
        if n <= 0:
            return []
        return self.messages[-n:]
    
    def get_full_conversation(self):
        """Restituisce l'intera conversazione come una singola stringa formattata."""
        if not self.messages:
            return "Nessun messaggio nella cronologia."
        
        transcript = []
        for msg in self.messages:
            # Formatta il ruolo (es. 'user' -> 'User', 'assistant' -> 'Assistant')
            role = msg["role"].capitalize()
            content = msg["content"]
            transcript.append(f"{role}: {content}")
            
        return "\n".join(transcript)

    def print_full_conversation(self):
        print("\n" + "="*50)
        print("📜 FULL CONVERSATION HISTORY 📜")
        print("="*50)
        print(self.get_full_conversation())
        print("="*50 + "\n")