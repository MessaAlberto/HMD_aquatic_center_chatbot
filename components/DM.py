import json
import re
from typing import Any

from prompts.dm_prompt import DM_SYSTEM_PROMPT


class DM:
    """Predicts the next best action from the current dialogue state."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def parse_llm_json(self, text: str) -> dict[str, Any]:
        """Parse the LLM output and return a safe fallback when parsing fails."""
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

            return {"nba": "fallback", "slot": None, "options": []}

    def predict_batch(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        messages_batch = []

        for payload in payloads:
            payload_str = json.dumps(payload, indent=2)

            messages = [
                {"role": "system", "content": DM_SYSTEM_PROMPT},
                {"role": "user", "content": f"CURRENT INPUT:\n{payload_str}"},
            ]

            messages_batch.append(messages)

        dm_outputs = self.llm.generate_batch(messages_batch=messages_batch, max_new_tokens=256)

        return [self.parse_llm_json(output) for output in dm_outputs]
