from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

import torch
from transformers import PreTrainedTokenizer

from utils.settings import APP_DEBUG


logger = logging.getLogger(__name__)


def _clear_cuda_cache() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _get_input_device(model) -> torch.device:
    if hasattr(model, "hf_device_map"):
        for device in model.hf_device_map.values():
            if isinstance(device, str) and device not in {"cpu", "disk"}:
                return torch.device(device)
    return model.device


def _normalize_messages(
    messages: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    if messages is None:
        return []

    normalized = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", message.get("text", ""))

        normalized.append(
            {
                "role": str(role),
                "content": str(content),
            }
        )

    return normalized


def _prepare_tokenizer(tokenizer: PreTrainedTokenizer) -> None:
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"


def prepare_text(
    tokenizer: PreTrainedTokenizer,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    normalized_messages = _normalize_messages(messages)

    return tokenizer.apply_chat_template(
        normalized_messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def _save_debug_prompt(filename_prefix: str, text: str) -> None:
    if not APP_DEBUG:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.txt"

    try:
        with open(filename, "w", encoding="utf-8") as file:
            file.write(text)
    except Exception as error:
        logger.warning("Failed to save debug prompt: %s", error)


def _generation_kwargs(tokenizer, max_new_tokens: int) -> Dict[str, Any]:
    return {
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "temperature": None,
        "top_p": None,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }


def generate_response(model, tokenizer, messages, max_new_tokens=128):
    _prepare_tokenizer(tokenizer)

    text_input = prepare_text(tokenizer, messages)
    _save_debug_prompt("prompt_debug", text_input)

    model_inputs = tokenizer(
        [text_input],
        return_tensors="pt",
    ).to(_get_input_device(model))

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            **_generation_kwargs(tokenizer, max_new_tokens),
        ).cpu()

    output_ids = generated_ids[0][input_len:]

    response = tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
    ).strip()

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return response


def generate_response_batch(model, tokenizer, messages_batch, max_new_tokens=128):
    _prepare_tokenizer(tokenizer)

    text_inputs = [
        prepare_text(tokenizer, messages)
        for messages in messages_batch
    ]

    if APP_DEBUG:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_batch_debug_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as file:
                for index, text in enumerate(text_inputs, start=1):
                    file.write(f"=== BATCH PROMPT {index} ===\n")
                    file.write(text)
                    file.write("\n\n")
        except Exception as error:
            logger.warning("Failed to save debug batch prompt: %s", error)

    model_inputs = tokenizer(
        text_inputs,
        return_tensors="pt",
        padding=True,
    ).to(_get_input_device(model))

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            **_generation_kwargs(tokenizer, max_new_tokens),
        ).cpu()

    responses = []

    for output_id in generated_ids:
        trimmed_id = output_id[input_len:]

        response = tokenizer.decode(
            trimmed_id,
            skip_special_tokens=True,
        ).strip()

        responses.append(response)

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return responses


def _normalize_gemma_messages(
    messages: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    if messages is None:
        return []

    normalized = []

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", message.get("text", ""))

        if isinstance(content, list):
            normalized_content = content
        else:
            normalized_content = [
                {
                    "type": "text",
                    "text": str(content),
                }
            ]

        normalized.append(
            {
                "role": str(role),
                "content": normalized_content,
            }
        )

    return normalized


def _prepare_gemma_processor(processor) -> None:
    tokenizer = getattr(processor, "tokenizer", None)

    if tokenizer is None:
        return

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"


def _decode_gemma_output(processor, output_ids) -> str:
    if hasattr(processor, "decode"):
        return processor.decode(
            output_ids,
            skip_special_tokens=True,
        ).strip()

    return processor.tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
    ).strip()


def _gemma_generation_kwargs(processor, max_new_tokens: int) -> Dict[str, Any]:
    tokenizer = getattr(processor, "tokenizer", processor)

    return {
        "max_new_tokens": max_new_tokens,
        "do_sample": False,
        "temperature": None,
        "top_p": None,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }


def generate_response_gemma3(model, tokenizer, messages, max_new_tokens=128):
    processor = tokenizer
    _prepare_gemma_processor(processor)

    model_inputs = processor.apply_chat_template(
        _normalize_gemma_messages(messages),
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(_get_input_device(model))

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
        ).cpu()

    output_ids = generated_ids[0][input_len:]

    if hasattr(processor, "decode"):
        response = processor.decode(
            output_ids,
            skip_special_tokens=True,
        ).strip()
    else:
        response = processor.tokenizer.decode(
            output_ids,
            skip_special_tokens=True,
        ).strip()

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return response


def generate_response_batch_gemma3(model, tokenizer, messages_batch, max_new_tokens=128):
    processor = tokenizer
    _prepare_gemma_processor(processor)

    text_inputs = [
        processor.apply_chat_template(
            _normalize_gemma_messages(messages),
            tokenize=False,
            add_generation_prompt=True,
        )
        for messages in messages_batch
    ]

    if APP_DEBUG:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_batch_debug_gemma3_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as file:
                for index, text in enumerate(text_inputs, start=1):
                    file.write(f"=== GEMMA BATCH PROMPT {index} ===\n")
                    file.write(text)
                    file.write("\n\n")
        except Exception as error:
            logger.warning("Failed to save Gemma debug batch prompt: %s", error)

    model_inputs = processor(
        text=text_inputs,
        return_tensors="pt",
        padding=True,
    ).to(_get_input_device(model))

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            **_gemma_generation_kwargs(processor, max_new_tokens),
        ).cpu()

    responses = []

    for output_id in generated_ids:
        trimmed_id = output_id[input_len:]
        response = _decode_gemma_output(processor, trimmed_id)
        responses.append(response)

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return responses