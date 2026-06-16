from prompts.nlu_prompt import INTENT_SCHEMAS_PROMPTS, NLU_BASE_CONTEXT
from llm.loader import load_llm
import argparse
import json
import re
import time
from collections import Counter
from typing import Any, Dict, List

from evaluation.utils import (
    MAX_NEW_TOKENS,
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

PATHS = get_eval_paths(__file__, "nlu")
GROUND_TRUTH_PATH = PATHS["ground_truth"]
FREE_TEXT_SLOTS = {"specific_inquiry", "last_seen_location", "lost_item"}
FREE_TEXT_F1_THRESHOLD = 0.50


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate NLU with one slot-level correctness metric.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Number of samples processed in each generation batch.")
    return parser.parse_args()


def build_messages(sample: Dict[str, Any]) -> List[Dict[str, str]]:
    target_intent = sample["target_intent"]
    target_segment = sample["target_segment"]
    schema = INTENT_SCHEMAS_PROMPTS.get(target_intent, INTENT_SCHEMAS_PROMPTS["out_of_scope"])
    system_prompt = f"{NLU_BASE_CONTEXT}\n\n{schema}"
    payload = {
        "conversation_history": sample.get("conversation_history", []),
        "full_user_message": sample.get("full_user_message", target_segment),
        "target_intent": target_intent,
        "target_segment": target_segment,
    }
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": json.dumps(payload, indent=2)},
    ]


def fallback_prediction(fallback_intent: str) -> Dict[str, Any]:
    return {"intent": fallback_intent, "slots": {}}


def normalize_prediction(prediction: Dict[str, Any], fallback_intent: str) -> Dict[str, Any]:
    return {
        "intent": prediction.get("intent", fallback_intent),
        "slots": prediction.get("slots", {}) or {},
    }


def parse_llm_json(text: str, fallback_intent: str) -> Dict[str, Any]:
    return parse_json_object(
        text=text,
        fallback=fallback_prediction(fallback_intent),
        normalizer=lambda parsed: normalize_prediction(parsed, fallback_intent),
    )


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"", "null", "none"}:
            return None
        if value.isdigit():
            return int(value)
        try:
            return float(value)
        except Exception:
            return value.lower()
    return value


def has_value(value: Any) -> bool:
    return normalize_value(value) is not None


def normalize_slot_value(slot: str, value: Any) -> Any:
    value = normalize_value(value)
    if value is None:
        return None
    if not isinstance(value, str):
        return value

    value = value.strip().lower()

    if slot in {
        "date", "date_old", "date_new", "last_seen_date",
        "time", "time_old", "time_new",
        "day_preference", "day_preference_old", "day_preference_new",
    }:
        for prefix in ["on ", "at ", "for ", "the "]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()

    if slot in {
        "facility_type", "service_type", "sub_type", "topic",
        "course_activity", "course_activity_old", "course_activity_new", "item",
    }:
        value = value.replace("-", "_").replace(" ", "_")

    if slot == "last_seen_location":
        for prefix in ["near the ", "near ", "in the ", "in ", "at the ", "at "]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()

    if slot == "specific_inquiry":
        for prefix in ["bring ", "wearing ", "wear ", "using ", "use "]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()

    return value


def normalize_free_text(value: Any) -> str:
    value = normalize_value(value)
    if value is None:
        return ""
    text = str(value).lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_f1(pred_value: Any, gt_value: Any) -> float:
    pred_tokens = normalize_free_text(pred_value).split()
    gt_tokens = normalize_free_text(gt_value).split()
    if not pred_tokens and not gt_tokens:
        return 1.0
    if not pred_tokens or not gt_tokens:
        return 0.0
    pred_counter = Counter(pred_tokens)
    gt_counter = Counter(gt_tokens)
    common = sum((pred_counter & gt_counter).values())
    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(gt_tokens)
    return 2 * precision * recall / (precision + recall)


def free_text_equal(pred_value: Any, gt_value: Any) -> bool:
    pred = normalize_free_text(pred_value)
    gt = normalize_free_text(gt_value)
    if pred == gt:
        return True
    if pred and gt and (pred in gt or gt in pred):
        return True
    return token_f1(pred, gt) >= FREE_TEXT_F1_THRESHOLD


def values_equal(slot: str, pred_value: Any, gt_value: Any) -> bool:
    if slot in FREE_TEXT_SLOTS:
        return free_text_equal(pred_value, gt_value)
    return normalize_slot_value(slot, pred_value) == normalize_slot_value(slot, gt_value)


def non_null_slots(slots: Dict[str, Any]) -> Dict[str, Any]:
    return {slot: value for slot, value in (slots or {}).items() if has_value(value)}


def compare_slots(prediction: Dict[str, Any], sample: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
    gt_slots = non_null_slots(sample["annotation"].get("slots", {}))
    pred_slots = non_null_slots(prediction.get("slots", {}) or {})

    missing_slots = sorted(slot for slot in gt_slots if slot not in pred_slots)
    extra_slots = sorted(slot for slot in pred_slots if slot not in gt_slots)
    wrong_values = []

    for slot in sorted(set(gt_slots) & set(pred_slots)):
        if not values_equal(slot, pred_slots[slot], gt_slots[slot]):
            wrong_values.append({
                "slot": slot,
                "ground_truth": gt_slots[slot],
                "prediction": pred_slots[slot],
                "free_text": slot in FREE_TEXT_SLOTS,
            })

    ok = not missing_slots and not extra_slots and not wrong_values
    details = {
        "missing_slots": missing_slots,
        "extra_slots": extra_slots,
        "wrong_values": wrong_values,
        "ground_truth_non_null_slots": gt_slots,
        "prediction_non_null_slots": pred_slots,
    }
    return ok, details


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(samples)
    correct = 0
    for prediction, sample in zip(predictions, samples):
        ok, _ = compare_slots(prediction, sample)
        if ok:
            correct += 1
    return {
        "total_samples": total,
        "main_metric": correct / total if total else 0.0,
        "nlu_slot_accuracy": correct / total if total else 0.0,
        "wrong_samples": total - correct,
        "free_text_slots": sorted(FREE_TEXT_SLOTS),
        "free_text_f1_threshold": FREE_TEXT_F1_THRESHOLD,
        "null_slots_ignored": True,
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []
    for prediction, sample in zip(predictions, samples):
        ok, details = compare_slots(prediction, sample)
        if ok:
            continue
        wrong_examples.append({
            "id": sample.get("id"),
            "input": {
                "conversation_history": sample.get("conversation_history", []),
                "full_user_message": sample.get("full_user_message"),
                "target_intent": sample.get("target_intent"),
                "target_segment": sample.get("target_segment"),
            },
            "ground_truth": sample.get("annotation"),
            "prediction": prediction,
            "slot_comparison": details,
        })
    return wrong_examples


def run_evaluation(model_name: str, batch_size: int, llm: Any = None) -> Dict[str, Any]:
    paths = get_eval_paths(__file__, "nlu", model_name=model_name)
    ground_truth_path = paths["ground_truth"]

    print(f"Loading ground truth from: {ground_truth_path}", flush=True)
    samples = load_json_list(ground_truth_path)
    total_samples = len(samples)
    total_batches = get_total_batches(total_samples, batch_size)

    print(f"Loaded {total_samples} NLU test samples.", flush=True)
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

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating NLU"):
        messages_batch = [build_messages(sample) for sample in batch_samples]
        outputs = llm.generate_batch(messages_batch=messages_batch, max_new_tokens=MAX_NEW_TOKENS)
        for output, sample in zip(outputs, batch_samples):
            fallback_intent = sample["target_intent"]
            parsed = parse_llm_json(output, fallback_intent)
            parsed["intent"] = fallback_intent
            predictions.append(parsed)
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
