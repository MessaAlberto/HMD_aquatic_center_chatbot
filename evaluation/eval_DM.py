from prompts.dm_prompt import DM_SYSTEM_PROMPT
from llm.loader import load_llm
import argparse
import json
import time
from typing import Any, Dict, List

from evaluation.utils import (
    MAX_NEW_TOKENS,
    basic_values_equal,
    ensure_project_root,
    get_eval_paths,
    get_total_batches,
    iter_batches,
    load_json_list,
    parse_json_object,
    print_batch_done,
    print_final_paths,
    save_json,
)

ensure_project_root(__file__)

PATHS = get_eval_paths(__file__, "dm")
GROUND_TRUTH_PATH = PATHS["ground_truth"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate DM with one deterministic accuracy metric.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Number of samples processed in each generation batch.")
    return parser.parse_args()


def build_messages(sample: Dict[str, Any]) -> List[Dict[str, str]]:
    payload_str = json.dumps(sample["input"], indent=2)
    return [
        {"role": "system", "content": DM_SYSTEM_PROMPT.strip()},
        {"role": "user", "content": f"CURRENT INPUT:\n{payload_str}"},
    ]


def empty_prediction() -> Dict[str, Any]:
    return {"nba": "fallback", "slot": None, "options": [], "blacklist": [], "enriched_data": {}}


def normalize_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nba": prediction.get("nba"),
        "slot": prediction.get("slot"),
        "options": prediction.get("options", []) or [],
        "blacklist": prediction.get("blacklist", []) or [],
        "enriched_data": prediction.get("enriched_data", {}) or {},
    }


def parse_llm_json(text: str) -> Dict[str, Any]:
    return parse_json_object(text=text, fallback=empty_prediction(), normalizer=normalize_prediction)


def normalize_list_as_set(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    normalized = []
    for item in value:
        if isinstance(item, (dict, list)):
            normalized.append(json.dumps(item, sort_keys=True, ensure_ascii=False).lower())
        elif item is None:
            normalized.append("null")
        else:
            normalized.append(str(item).strip().lower())
    return sorted(normalized)


def output_is_correct(prediction: Dict[str, Any], ground_truth: Dict[str, Any]) -> bool:
    prediction = normalize_prediction(prediction)
    ground_truth = normalize_prediction(ground_truth)

    if not basic_values_equal(prediction.get("nba"), ground_truth.get("nba")):
        return False
    if not basic_values_equal(prediction.get("slot"), ground_truth.get("slot")):
        return False
    if normalize_list_as_set(prediction.get("options")) != normalize_list_as_set(ground_truth.get("options")):
        return False
    if normalize_list_as_set(prediction.get("blacklist")) != normalize_list_as_set(ground_truth.get("blacklist")):
        return False
    if not basic_values_equal(prediction.get("enriched_data"), ground_truth.get("enriched_data")):
        return False

    return True


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(samples)
    correct = 0
    for prediction, sample in zip(predictions, samples):
        if output_is_correct(prediction, sample["annotation"]):
            correct += 1
    return {
        "total_samples": total,
        "main_metric": correct / total if total else 0.0,
        "dm_accuracy": correct / total if total else 0.0,
        "wrong_samples": total - correct,
        "options_blacklist_order_insensitive": True,
    }


def field_comparison(prediction: Dict[str, Any], ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    prediction = normalize_prediction(prediction)
    ground_truth = normalize_prediction(ground_truth)
    return {
        "nba_ok": basic_values_equal(prediction.get("nba"), ground_truth.get("nba")),
        "slot_ok": basic_values_equal(prediction.get("slot"), ground_truth.get("slot")),
        "options_ok": normalize_list_as_set(prediction.get("options")) == normalize_list_as_set(ground_truth.get("options")),
        "blacklist_ok": normalize_list_as_set(prediction.get("blacklist")) == normalize_list_as_set(ground_truth.get("blacklist")),
        "enriched_data_ok": basic_values_equal(prediction.get("enriched_data"), ground_truth.get("enriched_data")),
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []
    for prediction, sample in zip(predictions, samples):
        ground_truth = normalize_prediction(sample["annotation"])
        prediction = normalize_prediction(prediction)
        if output_is_correct(prediction, ground_truth):
            continue
        wrong_examples.append({
            "id": sample.get("id"),
            "input": sample.get("input"),
            "ground_truth": ground_truth,
            "prediction": prediction,
            "field_comparison": field_comparison(prediction, ground_truth),
        })
    return wrong_examples


def run_evaluation(model_name: str, batch_size: int, llm: Any = None) -> Dict[str, Any]:
    paths = get_eval_paths(__file__, "dm", model_name=model_name)
    ground_truth_path = paths["ground_truth"]

    print(f"Loading ground truth from: {ground_truth_path}", flush=True)
    samples = load_json_list(ground_truth_path)
    total_samples = len(samples)
    total_batches = get_total_batches(total_samples, batch_size)

    print(f"Loaded {total_samples} DM test samples.", flush=True)
    print(f"Batch size: {batch_size} -> {total_batches} batches.", flush=True)

    if llm is None:
        print(f"Loading model: {model_name}", flush=True)
        load_start = time.time()
        llm = load_llm(model_name)
        print(f"Model loaded in {time.time() - load_start:.1f}s.", flush=True)
    else:
        print(f"Using already loaded model: {model_name}", flush=True)

    predictions = []
    eval_start = time.time()

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating DM"):
        messages_batch = [build_messages(sample) for sample in batch_samples]
        raw_outputs = llm.generate_batch(messages_batch=messages_batch, max_new_tokens=MAX_NEW_TOKENS)
        predictions.extend(parse_llm_json(raw_output) for raw_output in raw_outputs)
        print_batch_done(batch_idx, total_batches, batch_start, eval_start, len(predictions), total_samples)

    metrics = compute_metrics(predictions, samples)
    wrong_examples = build_error_report(predictions, samples)

    results = {"model": model_name, "ground_truth_path": str(ground_truth_path), "metrics": metrics}
    save_json(results, paths["results"])
    save_json(wrong_examples, paths["errors"])
    print_final_paths(paths)
    return {"results": results, "paths": paths}


def main() -> None:
    args = parse_args()
    output = run_evaluation(model_name=args.model, batch_size=args.batch_size)
    print(json.dumps(output["results"]["metrics"], indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
