from copy import deepcopy
from typing import Any


class TaskQueue:
    """Stores one paused task while the system completes another intent first."""

    def __init__(self) -> None:
        self.task: dict[str, Any] | None = None

    def store(self, nlu_result: dict[str, Any], segment: str, dialogue_state: dict[str, Any]) -> None:
        self.task = {
            "intent": nlu_result.get("intent"),
            "segment": segment,
            "nlu": deepcopy(nlu_result),
            "dialogue_state": deepcopy(dialogue_state) if dialogue_state else None,
        }

    def consume_if_resumed(self, current_nlu: dict[str, Any]) -> bool:
        """Clear the queued task when the current NLU result continues it consistently."""
        if not self.task or current_nlu.get("intent") != self.task.get("intent"):
            return False

        current_slots = {key: value for key, value in current_nlu.get("slots", {}).items() if value is not None}
        paused_slots = {key: value for key, value in self.task.get("nlu", {}).get("slots", {}).items() if value is not None}

        if not current_slots:
            return False

        for slot_name, current_value in current_slots.items():
            paused_value = paused_slots.get(slot_name)

            if paused_value is not None and str(current_value).lower() != str(paused_value).lower():
                return False

        self.task = None
        return True

    def get_excluded_segment(self) -> list[str]:
        return [self.task["segment"]] if self.task else []

    def pop_intent(self) -> str | None:
        if not self.task:
            return None

        intent = self.task["intent"]
        self.task = None

        return intent

    def is_active(self) -> bool:
        return self.task is not None
