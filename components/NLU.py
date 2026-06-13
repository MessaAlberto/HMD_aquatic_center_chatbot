import json
import logging
import re
from typing import Any

from prompts.nlu_prompt import INTENT_SCHEMAS_PROMPTS, NLU_BASE_CONTEXT


logger = logging.getLogger(__name__)


class NLU:
    """Extracts intent-specific slots from router segments."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def parse_llm_json(self, text: str, fallback_intent: str) -> dict[str, Any]:
        """Parse the LLM JSON output and preserve the expected intent on failure."""
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

            return {"intent": fallback_intent, "slots": {}}

    def _build_messages(self, segment: dict[str, Any], history) -> list[dict[str, str]]:
        target_intent = segment.get("intent", "out_of_scope")
        segment_text = segment.get("segment", "")

        schema_and_examples = INTENT_SCHEMAS_PROMPTS.get(target_intent, INTENT_SCHEMAS_PROMPTS["out_of_scope"])
        system_prompt = f"{NLU_BASE_CONTEXT}\n\n{schema_and_examples}"

        conv_history, last_utterance = history.get_json_history_and_last_utterance(n=4)

        payload = {
            "conversation_history": conv_history,
            "full_user_message": last_utterance,
            "target_intent": target_intent,
            "target_segment": segment_text,
        }

        return [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]

    def predict_batch(self, segments: list[dict[str, Any]], history) -> list[dict[str, Any]]:
        messages_batch = [self._build_messages(segment, history) for segment in segments]
        nlu_outputs = self.llm.generate_batch(messages_batch=messages_batch, max_new_tokens=256)

        results = []

        for index, output in enumerate(nlu_outputs):
            target_intent = segments[index].get("intent", "out_of_scope")
            parsed_data = self.parse_llm_json(output, target_intent)
            parsed_data["intent"] = target_intent

            logger.debug("NLU segment %s raw output: %s", index, output)
            logger.debug("NLU segment %s parsed output: %s", index, parsed_data)

            results.append(parsed_data)

        return results
