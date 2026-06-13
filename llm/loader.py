import os

from dotenv import load_dotenv
from huggingface_hub import login
from transformers import AutoProcessor, AutoTokenizer

from llm.config import MODELS

load_dotenv()


def login_to_huggingface() -> None:
    token = os.getenv("HF_TOKEN")

    if not token:
        print("HF_TOKEN not found. Public models can still be loaded.")
        return

    try:
        login(token=token)
        print("Hugging Face login completed.")
    except Exception as error:
        print(f"Hugging Face login failed: {error}")


class LLMService:
    def __init__(self, model_name: str, device_map: str = "auto") -> None:
        login_to_huggingface()

        if model_name not in MODELS:
            available_models = ", ".join(MODELS.keys())
            raise ValueError(
                f"Unknown model '{model_name}'. Available models: {available_models}"
            )

        model_id, init_model, generate_response, generate_response_batch = MODELS[model_name]

        self.model_name = model_name
        self.model_id = model_id
        self.model = init_model(model_id, device_map=device_map)

        if model_name == "gemma3_4b":
            self.tokenizer = AutoProcessor.from_pretrained(
                model_id,
                trust_remote_code=True,
            )
        elif model_name == "phi4_mini":
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,
            )

        self._generate_response = generate_response
        self._generate_response_batch = generate_response_batch

    def generate(self, messages: list[dict[str, str]], max_new_tokens: int = 128) -> str:
        return self._generate_response(
            model=self.model,
            tokenizer=self.tokenizer,
            messages=messages,
            max_new_tokens=max_new_tokens,
        )

    def generate_batch(
        self,
        messages_batch: list[list[dict[str, str]]],
        max_new_tokens: int = 128,
    ) -> list[str]:
        return self._generate_response_batch(
            model=self.model,
            tokenizer=self.tokenizer,
            messages_batch=messages_batch,
            max_new_tokens=max_new_tokens,
        )


def load_llm(model_name: str, device_map: str = "auto") -> LLMService:
    return LLMService(model_name=model_name, device_map=device_map)