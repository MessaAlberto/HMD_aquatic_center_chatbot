from models.config import MODELS
from transformers import AutoTokenizer

def load_llm(model_name: str):
    name, init_model, generate_response, generate_response_batch = MODELS[model_name]
    model = init_model(name, device_map="cuda:0")
    tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True)

    return model, tokenizer, generate_response, generate_response_batch