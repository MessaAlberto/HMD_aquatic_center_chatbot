import json
from prompts import NLU_INTENT_PROMPT

class NLU:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def predict(self, user_input, history):
        prompt = NLU_INTENT_PROMPT.format(history=history, input=user_input)
        
        raw_output = self.generate_fn(self.model, self.tokenizer, prompt, messages=[])
        
        # Clean and parse JSON output
        try:
            # Strip markdown code blocks if present
            json_str = raw_output.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback for parsing errors
            data = {"intent": "out_of_scope", "slots": {}}
            
        return data