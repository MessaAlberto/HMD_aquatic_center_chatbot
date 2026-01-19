from typing import Dict, List, Optional
import torch
from transformers import PreTrainedTokenizer


def prepare_text(
    prompt,
    tokenizer: PreTrainedTokenizer,
    messages: Optional[List[Dict[str, str]]] = None,
    n_exchanges: int = 2,
):
    if messages is None:
        messages = []
    messages.append({"role": "user", "content": prompt})

    text = tokenizer.apply_chat_template(
        messages[-n_exchanges * 2:],
        tokenize=False,
        add_generation_prompt=True,
    )

    return text


def generate_response(model, tokenizer, prompt, messages=None, max_new_tokens=128):
    messages = messages if messages else []
    
    text_input = prepare_text(prompt, tokenizer, messages=messages)

    model_inputs = tokenizer([text_input], return_tensors="pt").to(model.device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            # do_sample=True,
            # temperature=0.1
        ).cpu()

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    response = tokenizer.decode(output_ids, skip_special_tokens=True)

    return response
