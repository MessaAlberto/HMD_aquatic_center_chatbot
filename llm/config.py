from typing import Any, Callable, Dict, Tuple
from functools import partial

import torch
from transformers import AutoModelForCausalLM, Gemma3ForConditionalGeneration, BitsAndBytesConfig

from llm.generation import (
    generate_response,
    generate_response_batch,
    generate_response_gemma3,
    generate_response_batch_gemma3,
)


quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
)


def load_causal_model(model_id: str, device_map: str = "auto", **kwargs: Any):
    return AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        device_map=device_map,
        quantization_config=quantization_config,
        **kwargs,
    )


def load_gemma3_model(model_id: str, device_map: str = "auto", **kwargs: Any):
    return Gemma3ForConditionalGeneration.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16,
        device_map=device_map,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        ),
        **kwargs,
    )


MODELS: Dict[str, Tuple[str, Callable[..., Any], Callable[..., Any], Callable[..., Any]]] = {
    "qwen3_4b": (
        "Qwen/Qwen3-4B-Instruct-2507",
        partial(load_causal_model, trust_remote_code=True),
        generate_response,
        generate_response_batch,
    ),
    "qwen25_3b": (
        "Qwen/Qwen2.5-3B-Instruct",
        partial(load_causal_model, trust_remote_code=True),
        generate_response,
        generate_response_batch,
    ),
    "llama32_3b": (
        "meta-llama/Llama-3.2-3B-Instruct",
        load_causal_model,
        generate_response,
        generate_response_batch,
    ),
    "gemma3_4b": (
        "google/gemma-3-4b-it",
        load_gemma3_model,
        generate_response_gemma3,
        generate_response_batch_gemma3,
    ),
    "phi4_mini": (
        "microsoft/Phi-4-mini-instruct",
        partial(
            load_causal_model,
            trust_remote_code=False,
            attn_implementation="eager",
        ),
        generate_response,
        generate_response_batch,
    ),
    "mistral7b": (
        "mistralai/Mistral-7B-Instruct-v0.3",
        load_causal_model,
        generate_response,
        generate_response_batch,
    ),
}