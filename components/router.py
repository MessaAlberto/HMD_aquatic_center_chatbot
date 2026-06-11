import json
import re

from prompts.router_prompt import ROUTER_SYSTEM_PROMPT
import logging

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, llm):
        self.llm = llm

    def parse_llm_json(self, text: str, active_intent: str = None) -> dict:
        try:
            parsed = json.loads(text)
        except Exception:
            pattern = r"```json\s*(.*?)\s*```"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                except Exception:
                    parsed = None
            else:
                parsed = None

        logger.debug("Parsed Router Output: %s", parsed)

        if not isinstance(parsed, dict) or "segments" not in parsed:
            return {
                "segments": [{"segment": text, "intent": "out_of_scope"}],
                "step_by_step_mode": False
            }

        segments = parsed.get("segments", [])

        target_merge_intents = {
            "book_course", "book_spa", "modify_booked_course", "modify_booked_spa",
            "cancel_booked_course", "cancel_booked_spa", "report_lost_item"
        }

        # ---------------------------------------------------------
        # POST-PROCESSING 1: Merge di due segmenti (Testo + Nome)
        # ---------------------------------------------------------
        user_id_idx = next((i for i, seg in enumerate(segments) if seg.get("intent") == "user_identification"), -1)
        target_idx = next((i for i, seg in enumerate(segments) if seg.get("intent") in target_merge_intents), -1)

        if user_id_idx != -1 and target_idx != -1 and user_id_idx != target_idx:
            logger.debug("Merging 'user_identification' into '%s'.", segments[target_idx].get("intent"))

            if user_id_idx < target_idx:
                merged_text = f"{segments[user_id_idx].get('segment', '')} {segments[target_idx].get('segment', '')}".strip()
            else:
                merged_text = f"{segments[target_idx].get('segment', '')} {segments[user_id_idx].get('segment', '')}".strip()

            segments[target_idx]["segment"] = merged_text
            segments.pop(user_id_idx)

        # ---------------------------------------------------------
        # POST-PROCESSING 2: Override della short-answer singola
        # ---------------------------------------------------------
        if len(segments) == 1 and segments[0].get("intent") == "user_identification" and active_intent in target_merge_intents:
            logger.debug("Short answer name-fill detected. Forcing intent from 'user_identification' to active '%s'.", active_intent)
            segments[0]["intent"] = active_intent

        step_by_step_mode = len(segments) > 2

        if step_by_step_mode:
            segments = segments[:2]

        return {
            "segments": segments,
            "step_by_step_mode": step_by_step_mode
        }

    def predict(self, history, excluded_segments=None, active_intent=None) -> dict:
        messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]

        conv_history, last_utterance = history.get_json_history_and_last_utterance_filtered(
            n=6,
            excluded_segments=excluded_segments
        )

        payload = {
            "conversation_history": conv_history,
            "last_user_utterance": last_utterance
        }

        messages.append({"role": "user", "content": json.dumps(payload, indent=2)})

        router_out = self.llm.generate(
            messages=messages,
            max_new_tokens=256
        )

        return self.parse_llm_json(router_out, active_intent=active_intent)