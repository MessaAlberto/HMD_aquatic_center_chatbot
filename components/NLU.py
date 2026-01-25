import json
from prompts import NLU_INTENT_PROMPT, NLU_CONTEXT_INSTRUCTION

class NLU:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def clean_slot_values(self, slots: dict):
        return {k: (None if v in ["null", "None", ""] else v) for k, v in slots.items()}

    def predict(self, user_input, history):
        # Get last system action and corresponding flag
        last_system_msg = history.get_last_bot_message() or "None"
        flag = history.get_flag() or "None"
        active_task = history.get_active_task() or "None"

        # Prepare context-aware instruction
        context_instruction = NLU_CONTEXT_INSTRUCTION.format(
            system_last_msg=last_system_msg,
            flag_instruction=flag,
            active_task=active_task
        )

        full_content = context_instruction + "\n\n" + NLU_INTENT_PROMPT
        system_msg = [{"role": "system", "content": full_content}]
        
        nlu_out = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg,
            user_input)
        
        print(f"DEBUG NLU Context Flag: {flag}")
        print(f"DEBUG NLU Context Instruction: {context_instruction}")
        print(f"DEBUG NLU Output: {nlu_out}")
        
        # Clean and parse JSON output
        try:
            # Strip markdown code blocks if present
            json_str = nlu_out.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)

            # Clean "null" string
            if "slots" in data:
                data["slots"] = self.clean_slot_values(data["slots"])

        except json.JSONDecodeError:
            # Fallback for parsing errors
            data = {"intent": "out_of_scope", "slots": {}}
        
        print(f"DEBUG NLU Parsed Data: {data}")
        return data