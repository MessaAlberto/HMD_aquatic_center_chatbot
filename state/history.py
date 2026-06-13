class History:
    """Stores the conversation turns and exposes formatted history views."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.last_system_action = None
        self.active_task = None
        self.flag = None

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_last_user_message(self) -> str | None:
        for message in reversed(self.messages):
            if message["role"] == "user":
                return message["content"]
        return None

    def get_last_bot_message(self) -> str | None:
        for message in reversed(self.messages):
            if message["role"] == "assistant":
                return message["content"]
        return None

    def set_last_system_action(self, action) -> None:
        self.last_system_action = action

    def get_last_system_action(self):
        return self.last_system_action

    def set_active_task(self, task) -> None:
        self.active_task = task

    def get_active_task(self):
        return self.active_task

    def get_flag(self):
        return self.flag

    def get_last_n_messages(self, n: int = 4) -> list[dict[str, str]]:
        if n <= 0:
            return []
        return self.messages[-n:]

    def get_prompt_formatted_history(self, n: int = 4) -> str:
        """Return the latest turns as plain text for prompt injection-safe contexts."""
        history_messages = self.get_last_n_messages(n)

        if not history_messages:
            return "No previous history."

        lines = []
        for message in history_messages:
            role_name = "ASSISTANT" if message["role"] == "assistant" else "USER"
            lines.append(f"{role_name}: {message['content']}")

        return "\n".join(lines)

    def get_full_conversation(self) -> str:
        """Return the full conversation as a readable transcript."""
        if not self.messages:
            return "No messages in the conversation history."

        transcript = []
        for message in self.messages:
            role = message["role"].capitalize()
            transcript.append(f"{role}: {message['content']}")

        return "\n".join(transcript)

    def get_json_history_and_last_utterance(self, n: int = 4) -> tuple[list[dict[str, str]], str]:
        """Split the current user message from the previous structured history."""
        if not self.messages:
            return [], ""

        last_utterance = self.messages[-1]["content"] if self.messages[-1]["role"] == "user" else ""
        past_messages = self.messages[:-1]
        past_messages = past_messages[-n:] if n > 0 else []

        formatted_history = [{"role": message["role"], "text": message["content"]} for message in past_messages]

        return formatted_history, last_utterance

    def get_json_history_and_last_utterance_filtered(self, n: int = 6, excluded_segments: list[str] | None = None) -> tuple[list[dict[str, str]], str]:
        """Return structured history while removing segments that belong to queued tasks."""
        excluded_segments = excluded_segments or []
        conversation_history, last_utterance = self.get_json_history_and_last_utterance(n=n)

        filtered_history = []
        for message in conversation_history:
            if message["role"] != "user":
                filtered_history.append(message)
                continue

            text = message["text"]
            for segment in excluded_segments:
                text = text.replace(segment, "").strip()

            if text:
                filtered_history.append({"role": message["role"], "text": text})

        return filtered_history, last_utterance

    def print_full_conversation(self) -> None:
        print("\n" + "=" * 50)
        print("FULL CONVERSATION HISTORY")
        print("=" * 50)
        print(self.get_full_conversation())
        print("=" * 50 + "\n")
