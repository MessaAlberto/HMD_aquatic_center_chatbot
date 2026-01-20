import torch
from transformers import AutoTokenizer

from components.NLU import NLU
from components.DM import DM
# from components.NLG import NLG
from utils.models import MODELS
from utils.display import dispaly_conversation
from utils.dialogue_state_tracker import StateTracker
from utils.mock_database import MockDatabase


def main():
    model_name, InitModel, generate_response = MODELS["qwen3"]

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = InitModel(
        model_name,
        dtype="auto",
        device_map="cuda:0"
    )

    nlu = NLU(model, tokenizer, generate_response)
    dm = DM(model, tokenizer, generate_response)
    # nlg = NLG(model, tokenizer)
    
    tracker = StateTracker()
    db = MockDatabase()

    print("Chatbot is ready! Type 'exit' to quit.")

    while True:
        user_input = input(f"You: ")
        if user_input.lower() in ["exit", "quit", "stop"]:
            print("Bot: Goodbye!")
            break

        # --- STEP 1: NLU (Understand) ---
        nlu_result = nlu.predict(user_input)
        dispaly_conversation(NLU, user_input, str(nlu_result))

        dialogue_state = tracker.update(nlu_result)

        # --- STEP 2: DM (Decide) ---
        action = dm.predict(dialogue_state, db_result=None)
        dispaly_conversation("DM (Decision)", str(dialogue_state), str(action))

        final_response = None
        if action.get("type") == "query_db":
            query_intent = action.get("intent")
            query_slots = dialogue_state["slots"]

            db_results = db.query_database(query_intent, query_slots)
            print(f"DEBUG DB Results: {db_results}")

            final_response = dm.predict(dialogue_state, db_result=db_results)
            if db_results is None:

                nba = dm.predict(nlu_result, db_results=[])
            else:
                tracker.update(nlu_result, nba, db_results)
        else:
            tracker.update(nlu_result, nba)

        # --- STEP 3: NLG (Respond) ---
        # bot_response = nlg.generate_response(action, data)

        # print(f"Bot: {bot_response}")
        # messages.append(f"Assistant: {bot_response}")


if __name__ == "__main__":
    main()
