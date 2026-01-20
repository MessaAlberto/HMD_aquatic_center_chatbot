import json
from prompts import DM_ACTION_PROMPT


class DM:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def predict(self, dialogue_state, db_result=None):
        # Format the system prompt with current state and db result (if any)
        # If db_result is None, we can pass "None" or empty string to the prompt
        db_context = json.dumps(db_result) if db_result else "No database query performed yet."
        state_context = json.dumps(dialogue_state)

        formatted_system_prompt = DM_ACTION_PROMPT.replace(
            "{dialogue_state}", state_context).replace("{db_result}", db_context)

        system_msg = [{"role": "system", "content": formatted_system_prompt}]

        # We don't need user input here, the state IS the input for the DM decision
        # But generate_fn expects an 'input' argument. We can pass a dummy or the intent.
        dummy_input = f"Decide action for intent: {dialogue_state.get('intent')}"

        dm_out = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg,
            input=dummy_input
        )

        print(f"DEBUG DM Raw Output: {dm_out}")

        # Parse output (Expected JSON)
        try:
            json_str = dm_out.replace("```json", "").replace("```", "").strip()
            action_data = json.loads(json_str)
        except json.JSONDecodeError:
            # Fallback
            action_data = {"type": "error", "message": "DM parsing failed"}

        return action_data
