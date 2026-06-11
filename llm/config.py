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

# The tuple contains the model name, a partial function with the model specific arguments, the method to prepare the input text
MODELS: Dict[str, Tuple[str, Callable[..., Any], Callable[..., Any], Callable[..., Any]]] = {
    "qwen3": (
        "Qwen/Qwen3-4B-Instruct-2507",
        partial(AutoModelForCausalLM.from_pretrained, trust_remote_code=True, quantization_config=quantization_config),
        generate_response,
        generate_response_batch
    )
}