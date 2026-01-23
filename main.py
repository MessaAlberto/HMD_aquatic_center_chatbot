import torch
from transformers import AutoTokenizer

from components.NLU import NLU
from components.DM import DM
from components.NLG import NLG
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
    nlg = NLG(model, tokenizer)
    
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
        print(f"DEBUG Dialogue State: {dialogue_state}")

        # --- STEP 2: DM (Decide) ---
        nba = dm.prepare_db_query(dialogue_state)
        dispaly_conversation("DM (Decision)", str(dialogue_state), str(nba))

        if nba.get("nba") == "validate_data":
            # Data validation step
            db_args = {
                "intent": nba.get("intent"),
                "slots": nba.get("slots"),
                "slots_to_validate": nba.get("slots_to_validate"),
                "active_task": nba.get("active_task"),
            }

            if nba.get("user"):
                db_args["user"] = nba.get("user")

            db_result = db.query_database(**db_args)
            nba = dm.make_dm_decision(dialogue_state, db_result=db_result)
        else:
            nba = dm.make_dm_decision(dialogue_state, db_result=None)

        # --- STEP 3: NLG (Respond) ---
        bot_response = nlg.generate_response(nba, user_input)

        dispaly_conversation(NLG, str(nba), bot_response)
        # print(f"Bot: {bot_response}")
        # messages.append(f"Assistant: {bot_response}")


if __name__ == "__main__":
    main()
