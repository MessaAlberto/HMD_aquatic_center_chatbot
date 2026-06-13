import json
import logging
import re
from typing import Any

from prompts.router_prompt import ROUTER_SYSTEM_PROMPT


logger = logging.getLogger(__name__)

TARGET_MERGE_INTENTS = {
    "book_course",
    "book_spa",
    "modify_booked_course",
    "modify_booked_spa",
    "cancel_booked_course",
    "cancel_booked_spa",
    "report_lost_item",
}


class Router:
    """Splits the latest user message into intent-specific segments."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except Exception:
            pattern = r"```json\s*(.*?)\s*```"
            match = re.search(pattern, text, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass

            return None

    def _fallback_output(self, text: str) -> dict[str, Any]:
        return {
            "segments": [{"segment": text, "intent": "out_of_scope"}],
            "step_by_step_mode": False,
        }

    def _merge_user_identification(self, segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge a name-only segment into a task that requires user identity."""
        user_id_index = next((i for i, segment in enumerate(segments)
                             if segment.get("intent") == "user_identification"), -1)
        target_index = next((i for i, segment in enumerate(segments)
                            if segment.get("intent") in TARGET_MERGE_INTENTS), -1)

        if user_id_index == -1 or target_index == -1 or user_id_index == target_index:
            return segments

        logger.debug("Merging user_identification into %s.", segments[target_index].get("intent"))

        first_segment = segments[user_id_index].get("segment", "")
        second_segment = segments[target_index].get("segment", "")

        if user_id_index < target_index:
            merged_text = f"{first_segment} {second_segment}".strip()
        else:
            merged_text = f"{second_segment} {first_segment}".strip()

        segments[target_index]["segment"] = merged_text
        segments.pop(user_id_index)

        return segments

    def _override_short_answer_intent(self, segments: list[dict[str, Any]], active_intent: str | None) -> list[dict[str, Any]]:
        """Treat a name-only answer as part of the active task when appropriate."""
        if len(segments) == 1 and segments[0].get("intent") == "user_identification" and active_intent in TARGET_MERGE_INTENTS:
            logger.debug("Forcing short-answer user_identification to active intent %s.", active_intent)
            segments[0]["intent"] = active_intent

        return segments

    def parse_llm_json(self, text: str, active_intent: str | None = None) -> dict[str, Any]:
        parsed = self._parse_json(text)
        logger.debug("Parsed router output: %s", parsed)

        if not isinstance(parsed, dict) or "segments" not in parsed:
            return self._fallback_output(text)

        segments = parsed.get("segments", [])
        segments = self._merge_user_identification(segments)
        segments = self._override_short_answer_intent(segments, active_intent)

        step_by_step_mode = len(segments) > 2

        if step_by_step_mode:
            segments = segments[:2]

        return {"segments": segments, "step_by_step_mode": step_by_step_mode}

    def predict(self, history, excluded_segments: list[str] | None = None, active_intent: str | None = None) -> dict[str, Any]:
        conv_history, last_utterance = history.get_json_history_and_last_utterance_filtered(
            n=6, excluded_segments=excluded_segments)

        payload = {
            "conversation_history": conv_history,
            "last_user_utterance": last_utterance,
        }

        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]

        router_output = self.llm.generate(messages=messages, max_new_tokens=256)

        return self.parse_llm_json(router_output, active_intent=active_intent)
