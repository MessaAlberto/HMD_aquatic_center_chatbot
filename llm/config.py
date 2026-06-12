from typing import Any, Callable, Dict, Tuple
from functools import partial
import torch
from transformers import AutoModelForCausalLM, BitsAndBytesConfig

from llm.generation import generate_response, generate_response_batch

quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)

MODEL_LOADER = partial(
    AutoModelForCausalLM.from_pretrained,
    torch_dtype=torch.float16,
    device_map="auto",
    quantization_config=quantization_config,
)

MODELS: Dict[str, Tuple[str, Callable[..., Any], Callable[..., Any], Callable[..., Any]]] = {
    "qwen3_4b": (
        "Qwen/Qwen3-4B-Instruct-2507",
        partial(MODEL_LOADER, trust_remote_code=True),
        generate_response,
        generate_response_batch,
    ),
    "qwen25_3b": (
        "Qwen/Qwen2.5-3B-Instruct",
        partial(MODEL_LOADER, trust_remote_code=True),
        generate_response,
        generate_response_batch,
    ),
    "llama32_3b": (
        "meta-llama/Llama-3.2-3B-Instruct",
        MODEL_LOADER,
        generate_response,
        generate_response_batch,
    ),
    "gemma3_4b": (
        "google/gemma-3-4b-it",
        MODEL_LOADER,
        generate_response,
        generate_response_batch,
    ),
    "phi4_mini": (
        "microsoft/Phi-4-mini-instruct",
        MODEL_LOADER,
        generate_response,
        generate_response_batch,
    ),
    "mistral7b": (
        "mistralai/Mistral-7B-Instruct-v0.3",
        MODEL_LOADER,
        generate_response,
        generate_response_batch,
    ),
}