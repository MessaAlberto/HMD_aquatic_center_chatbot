class TaskQueue:
    def __init__(self):
        self.task = None

    def store(self, nlu_result: dict, segment: str, dialogue_state: dict) -> None:
        self.task = {
            "intent": nlu_result.get("intent"),
            "segment": segment,
            "nlu": nlu_result.copy(),
            "dialogue_state": dialogue_state.copy() if dialogue_state else None
        }

    def consume_if_resumed(self, current_nlu: dict) -> bool:
        if not self.task or current_nlu.get("intent") != self.task.get("intent"):
            return False

        current_slots = {k: v for k, v in current_nlu.get("slots", {}).items() if v is not None}
        paused_slots = {k: v for k, v in self.task.get("nlu", {}).get("slots", {}).items() if v is not None}

        if not current_slots:
            return False

        for slot, current_val in current_slots.items():
            paused_val = paused_slots.get(slot)
            if paused_val is not None and str(current_val).lower() != str(paused_val).lower():
                return False

        self.task = None
        return True

    def get_excluded_segment(self) -> list:
        return [self.task["segment"]] if self.task else []

    def pop_intent(self) -> str:
        if not self.task:
            return None
        intent = self.task["intent"]
        self.task = None
        return intent

    def is_active(self) -> bool:
        return self.task is not None