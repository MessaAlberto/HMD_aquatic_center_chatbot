import json
import re

from prompts.nlu_prompt import (
    NLU_CONTEXT,
    NLU_PROMPT_V2,
    ONE_SHOT_EXAMPLE
)


class NLU:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def parse_llm_json(self, text: str) -> dict:
        """Estrazione robusta del JSON tramite Regex."""
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
            return {"intent": "out_of_scope", "slots": {}}

    def predict(self, history):
        # Assemblaggio del Prompt: v2_one_shot
        intent_prompt = f"{NLU_CONTEXT}\n{NLU_PROMPT_V2}\n{ONE_SHOT_EXAMPLE}"

        messages = [{"role": "system", "content": intent_prompt}]
        hist_msgs = history.get_last_n_messages(5)

        if hist_msgs:
            messages.extend(hist_msgs)

        nlu_out = self.generate_fn(
            self.model,
            self.tokenizer,
            messages)

        print(f"DEBUG NLU Raw Output: {nlu_out}")

        data = self.parse_llm_json(nlu_out)

        print(f"DEBUG NLU Parsed Data: {data}")
        return data
