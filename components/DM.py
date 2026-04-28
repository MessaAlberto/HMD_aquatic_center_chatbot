import json
import re

from prompts.dm_prompt import DM_SYSTEM_PROMPT


class DM:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def parse_llm_json(self, text: str) -> dict:
        """Estrazione robusta del JSON tramite Regex (identica all'NLU)."""
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

    def predict(self, dialogue_state, db_result):
        payload = {
            "dialogue_state": dialogue_state,
            "db_result": db_result
        }
        payload_str = json.dumps(payload, indent=2)

        system_msg = [{"role": "system", "content": DM_SYSTEM_PROMPT}]
        system_msg.append({"role": "system", "content": f"CURRENT INPUT:\n{payload_str}"})

        dm_out = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg
        )

        print(f"DEBUG DM Raw Output: {dm_out}")

        action_data = self.parse_llm_json(dm_out)

        print(f"DEBUG DM Parsed Action Data: {action_data}")
        return action_data