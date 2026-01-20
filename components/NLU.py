import json
from prompts import NLU_INTENT_PROMPT

class NLU:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def predict(self, user_input):
        system_msg = {"role": "system", "content": NLU_INTENT_PROMPT}
        
        nlu_out = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg,
            user_input)
        
        print(f"DEBUG NLU Output: {nlu_out}")
        
        # Clean and parse JSON output
        try:
            # Strip markdown code blocks if present
            json_str = nlu_out.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback for parsing errors
            data = {"intent": "out_of_scope", "slots": {}}
        
        print(f"DEBUG NLU Parsed Data: {data}")
        return data