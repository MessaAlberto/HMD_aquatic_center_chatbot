import json
from prompts.nlg_prompt import NLG_BASE_PROMPT, INTENT_PROMPTS


class NLG:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

    def predict(self, dm_action_data: dict, dialogue_state: dict, history) -> str:
        dm_str = json.dumps(dm_action_data, indent=2)
        ds_str = json.dumps(dialogue_state, indent=2)

        current_intent = dialogue_state.get("intent", "default")
        intent_specific_block = INTENT_PROMPTS.get(current_intent, "")

        print(f"DEBUG NLG Intent for Prompt: {intent_specific_block}")

        system_content = (
            f"{NLG_BASE_PROMPT}\n\n"
            f"{intent_specific_block}\n"
            f"--- END OF INSTRUCTIONS & EXAMPLES ---\n"
        )

        messages = [{"role": "system", "content": system_content.strip()}]

        hist_msgs = history.get_last_n_messages(3)
        if hist_msgs:
            messages.extend(hist_msgs)

        # final_command = (
        #     f"CURRENT DIALOGUE STATE:\n{ds_str}\n\n"
        #     f"CURRENT DM INSTRUCTION:\n{dm_str}\n\n"
        #     f"CRITICAL: Ignore the user's latest conversational diversions. You MUST execute the 'nba' and 'slot' specified in the CURRENT DM INSTRUCTION exactly as requested."
        # )
        final_command = (
            f"CURRENT DIALOGUE STATE:\n{ds_str}\n\n"
            f"CURRENT DM INSTRUCTION:\n{dm_str}"
        )

        messages.append({"role": "system", "content": final_command})

        response_text = self.generate_fn(
            self.model,
            self.tokenizer,
            messages
        )

        print(f"DEBUG NLG Input DM Action: {dm_str}")
        print(f"DEBUG NLG Generated: {response_text}")

        return response_text.strip()
