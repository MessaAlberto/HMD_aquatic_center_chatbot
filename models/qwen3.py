from typing import Dict, List, Optional
import torch
from transformers import PreTrainedTokenizer
from datetime import datetime

def prepare_text(
    tokenizer: PreTrainedTokenizer,
    messages: Optional[List[Dict[str, str]]] = None,
):
    if messages is None:
        messages = []

    # print(f"DEBUG prepare_text - messages: {messages}")

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    return text


def generate_response(model, tokenizer, messages, max_new_tokens=128):
    messages = messages if messages else []
    text_input = prepare_text(tokenizer, messages)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"prompt_debug_{timestamp}.txt"
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text_input)
    except Exception as e:
        print(f"Failed to save debug file: {e}")

    model_inputs = tokenizer([text_input], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            # do_sample=True,
            # temperature=0.1
        ).cpu()

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    response = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    del model_inputs
    del generated_ids
    torch.cuda.empty_cache()

    return response


def generate_response_batch(model, tokenizer, messages_batch, max_new_tokens=128):
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    text_inputs = []
    for messages in messages_batch:
        messages = messages if messages else []
        text_inputs.append(prepare_text(tokenizer, messages))

    model_inputs = tokenizer(text_inputs, return_tensors="pt", padding=True).to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
        ).cpu()

    responses = []
    for i, output_id in enumerate(generated_ids):
        input_len = len(model_inputs.input_ids[i])
        trimmed_id = output_id[input_len:]
        response = tokenizer.decode(trimmed_id, skip_special_tokens=True).strip()
        responses.append(response)

    del model_inputs
    del generated_ids
    torch.cuda.empty_cache()

    return responses