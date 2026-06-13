from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

import torch
from transformers import PreTrainedTokenizer

from utils.settings import APP_DEBUG


logger = logging.getLogger(__name__)


def _clear_cuda_cache() -> None:
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def prepare_text(
    tokenizer: PreTrainedTokenizer,
    messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    if messages is None:
        messages = []

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    return text


def generate_response(model, tokenizer, messages, max_new_tokens=128):
    messages = messages if messages else []
    text_input = prepare_text(tokenizer, messages)

    if APP_DEBUG:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_debug_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(text_input)
        except Exception as error:
            logger.warning("Failed to save debug file: %s", error)

    model_inputs = tokenizer(
        [text_input],
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
        ).cpu()

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    response = tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
    ).strip()

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return response


def generate_response_batch(model, tokenizer, messages_batch, max_new_tokens=128):
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"

    text_inputs = []

    for messages in messages_batch:
        messages = messages if messages else []
        text_inputs.append(prepare_text(tokenizer, messages))

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
            logger.warning("Failed to save debug batch file: %s", error)

    model_inputs = tokenizer(
        text_inputs,
        return_tensors="pt",
        padding=True,
    ).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
        ).cpu()

    responses = []

    for index, output_id in enumerate(generated_ids):
        input_len = len(model_inputs.input_ids[index])
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
        messages = []

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
                "role": role,
                "content": normalized_content,
            }
        )

    return normalized


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


def generate_response_gemma3(model, tokenizer, messages, max_new_tokens=128):
    processor = tokenizer
    gemma_messages = _normalize_gemma_messages(messages)

    text_input = processor.apply_chat_template(
        gemma_messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    if APP_DEBUG:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"prompt_debug_gemma3_{timestamp}.txt"

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(text_input)
        except Exception as error:
            logger.warning("Failed to save Gemma debug file: %s", error)

    model_inputs = processor(
        text=[text_input],
        return_tensors="pt",
    ).to(model.device)

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
        ).cpu()

    output_ids = generated_ids[0][input_len:]
    response = _decode_gemma_output(processor, output_ids)

    del model_inputs
    del generated_ids
    _clear_cuda_cache()

    return response


def generate_response_batch_gemma3(model, tokenizer, messages_batch, max_new_tokens=128):
    processor = tokenizer

    text_inputs = []

    for messages in messages_batch:
        gemma_messages = _normalize_gemma_messages(messages)

        text_input = processor.apply_chat_template(
            gemma_messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        text_inputs.append(text_input)

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
            logger.warning("Failed to save Gemma batch debug file: %s", error)

    model_inputs = processor(
        text=text_inputs,
        return_tensors="pt",
        padding=True,
    ).to(model.device)

    input_len = model_inputs["input_ids"].shape[-1]

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
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