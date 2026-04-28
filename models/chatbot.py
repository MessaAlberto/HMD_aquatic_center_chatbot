from transformers import AutoTokenizer

from models.config import MODELS
from components.NLU import NLU
from components.DM import DM
from components.NLG import NLG
from components.dialogue_state_tracker import StateTracker
from components.history import History
from components.db_controller import DBController
from models.qwen3 import generate_response
from utils.display import display_conversation
from models.loader import load_llm


class Chatbot:
    def __init__(self, model_name: str) -> None:
        self.model, self.tokenizer, self.generate_response, _ = load_llm(model_name)

        self.NLU = NLU(self.model, self.tokenizer, self.generate_response)
        self.DM = DM(self.model, self.tokenizer, self.generate_response)
        self.NLG = NLG(self.model, self.tokenizer, self.generate_response)

        self.dst = StateTracker()
        self.db_controller = DBController(self.dst)
        self.history = History()

    def chat_loop(self):
        print("Chatbot is ready! Type 'exit' to quit.")

        while True:
            user_input = input("You: ")
            if user_input.lower() in ["exit", "quit", "stop"]:
                print("Bot: Goodbye!")
                break

            self.history.add_message("user", user_input)
            nlu_result = self.NLU.predict(self.history)
            print(f"DEBUG NLU Result: {nlu_result}")

            dialogue_state = self.dst.update(nlu_result)
            print(f"DEBUG Updated Dialogue State: {dialogue_state}")
            user_profile = self.dst.get_user_profile()

            db_result = self.db_controller.resolve_state(dialogue_state, user_profile)
            print(f"DEBUG DB Result: {db_result}")
            nba = self.DM.predict(dialogue_state, db_result=db_result)
            print(f"DEBUG DM NBA: {nba}")

            response = self.NLG.predict(nba, dialogue_state, self.history)
            self.history.add_message("system", response)
            print(f"Bot: {response}")