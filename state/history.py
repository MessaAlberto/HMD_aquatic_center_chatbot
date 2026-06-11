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
    
    # ====================================================
    # NUOVO METODO PER I SYSTEM PROMPT (ANTI-RLHF)
    # ====================================================
    def get_prompt_formatted_history(self, n=4) -> str:
        """
        Restituisce gli ultimi 'n' messaggi come stringa di puro testo.
        Da usare per NLU e Router per evitare che l'LLM interpreti i ruoli nativi.
        """
        hist_msgs = self.get_last_n_messages(n)
        if not hist_msgs:
            return "No previous history."
        
        history_text = ""
        for msg in hist_msgs:
            role_name = "ASSISTANT" if msg["role"] == "assistant" else "USER"
            history_text += f"{role_name}: {msg['content']}\n"
            
        return history_text.strip()
    # ====================================================

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

    # ====================================================
    # METODO PER INPUT STRUTTURATO (JSON PAYLOAD)
    # ====================================================
    def get_json_history_and_last_utterance(self, n=4) -> tuple:
        """
        Scorpora l'ultimo messaggio dell'utente dalla history passata.
        Restituisce (lista_history_passata, ultimo_messaggio).
        """
        if not self.messages:
            return [], ""
            
        # L'ultimo messaggio è l'input corrente dell'utente
        last_utterance = self.messages[-1]["content"] if self.messages[-1]["role"] == "user" else ""
        
        # Prendiamo gli 'n' messaggi precedenti, escludendo l'ultimo
        past_msgs = self.messages[:-1]
        past_msgs = past_msgs[-n:] if n > 0 else []
        
        formatted_history = [{"role": m["role"], "text": m["content"]} for m in past_msgs]
        
        return formatted_history, last_utterance

    def get_json_history_and_last_utterance_filtered(self, n=6, excluded_segments=None):
        if excluded_segments is None:
            excluded_segments = []

        conv_history, last_utterance = self.get_json_history_and_last_utterance(n=n)

        filtered_history = []
        for msg in conv_history:
            if msg["role"] != "user":
                filtered_history.append(msg)
                continue

            text = msg["text"]
            for segment in excluded_segments:
                text = text.replace(segment, "").strip()

            if text:
                filtered_history.append({"role": msg["role"], "text": text})

        return filtered_history, last_utterance

    def print_full_conversation(self):
        print("\n" + "="*50)
        print("📜 FULL CONVERSATION HISTORY 📜")
        print("="*50)
        print(self.get_full_conversation())
        print("="*50 + "\n")