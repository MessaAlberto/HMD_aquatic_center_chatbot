import torch
from transformers import AutoTokenizer

from components.NLU import NLU
from components.DM import DM
from components.NLG import NLG
from utils.models import MODELS
from utils.display import dispaly_conversation
# from utils.state_tracker import StateTracker


def main():
    model_name, InitModel, generate_response = MODELS["qwen3"]

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = InitModel(
        model_name,
        dtype="auto",
        device_map="cuda:0"
    )
    messages = []

    nlu = NLU(model, tokenizer)
    dm = DM(database=None)
    nlg = NLG(model, tokenizer)
    # tracker = StateTracker()

    messages = [
        {
            "role": "system",
            "content": f"Hello! You are {model_name} agent. How can I help you?"
        }
    ]

    while True:
        user_input = input(f"Bot: {messages[-1]['content']}\nYou: ")
        if user_input.lower() in ["exit", "quit", "stop"]:
            print("Bot: Goodbye!")
            break

        # messages.append(f"User: {user_input}")

        # --- STEP 1: NLU (Understand) ---
        nlu_result = nlu.predict(user_input, messages, generate_response)
        print(f"DEBUG NLU: {nlu_result}")

        # --- STEP 2: DM (Decide) ---
        # action, data = dm.decide_action(nlu_result, tracker)
        # print(f"DEBUG DM: Action={action}, Data={data}")

        # --- STEP 3: NLG (Respond) ---
        # bot_response = nlg.generate_response(action, data)

        # print(f"Bot: {bot_response}")
        # messages.append(f"Assistant: {bot_response}")


if __name__ == "__main__":
    main()
