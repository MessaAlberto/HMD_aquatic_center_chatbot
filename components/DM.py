import json
import re

from prompts.dm_prompt import DM_SYSTEM_PROMPT


class DM:
    def __init__(self, llm):
        self.llm = llm

    def parse_llm_json(self, text: str) -> dict:
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

            return {
                "nba": "fallback",
                "slot": None,
                "options": []
            }

    def predict_batch(self, payloads: list) -> list:
        messages_batch = []

        for payload in payloads:
            payload_str = json.dumps(payload, indent=2)

            messages = [
                {"role": "system", "content": DM_SYSTEM_PROMPT},
                {"role": "user", "content": f"CURRENT INPUT:\n{payload_str}"}
            ]

            messages_batch.append(messages)

        dm_outputs = self.llm.generate_batch(
            messages_batch=messages_batch,
            max_new_tokens=256
        )

        return [self.parse_llm_json(out) for out in dm_outputs]