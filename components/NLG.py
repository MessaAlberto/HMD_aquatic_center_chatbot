import json
from prompts import NLG_SYSTEM_PROMPT

class NLG:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def generate_response(self, dm_action_data, last_user_message):
        try:
            dm_instruction_str = json.dumps(dm_action_data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            dm_instruction_str = str(dm_action_data)

        input_data = f"""
USER INPUT: "{last_user_message}"
DM INSTRUCTION:
{dm_instruction_str}
"""

        system_msg = [{"role": "system", "content": NLG_SYSTEM_PROMPT}]

        response_text = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg,
            input_data
        )

        print(f"DEBUG NLG Input Inst: {dm_instruction_str}")
        print(f"DEBUG NLG Generated: {response_text}")

        return response_text.strip()