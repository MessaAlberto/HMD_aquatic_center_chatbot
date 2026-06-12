from prompts.nlu_prompt import INTENT_SCHEMAS_PROMPTS, NLU_BASE_CONTEXT
from llm.loader import load_llm
import argparse
import json
import time
from collections import defaultdict
from typing import Any, Dict, List

from evaluation.utils import (
    MAX_NEW_TOKENS,
    ensure_project_root,
    get_eval_paths,
    get_total_batches,
    iter_batches,
    load_json_list,
    parse_json_object,
    precision_recall_f1,
    print_batch_done,
    print_final_paths,
    save_json,
)


ensure_project_root(__file__)


PATHS = get_eval_paths(__file__, "nlu")
GROUND_TRUTH_PATH = PATHS["ground_truth"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the NLU component.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4,
                        help="Number of samples processed in each generation batch.")
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
    prediction["intent"] = prediction.get("intent", fallback_intent)
    prediction["slots"] = prediction.get("slots", {}) or {}
    return prediction


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


def normalize_slot_value(slot: str, value: Any) -> Any:
    value = normalize_value(value)

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    value = value.strip().lower()

    if slot in {
        "date",
        "date_old",
        "date_new",
        "last_seen_date",
        "time",
        "time_old",
        "time_new",
        "day_preference",
        "day_preference_old",
        "day_preference_new",
    }:
        for prefix in ["on ", "at ", "for ", "the "]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()

    if slot in {
        "facility_type",
        "service_type",
        "sub_type",
        "topic",
        "course_activity",
        "course_activity_old",
        "course_activity_new",
        "item",
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


def values_equal(slot: str, pred_value: Any, gt_value: Any) -> bool:
    return normalize_slot_value(slot, pred_value) == normalize_slot_value(slot, gt_value)


def sample_is_correct(prediction: Dict[str, Any], sample: Dict[str, Any]) -> bool:
    ground_truth = sample["annotation"]

    if prediction.get("intent") != ground_truth.get("intent"):
        return False

    pred_slots = prediction.get("slots", {}) or {}
    gt_slots = ground_truth.get("slots", {}) or {}
    all_slots = set(pred_slots.keys()) | set(gt_slots.keys())

    for slot in all_slots:
        if slot not in pred_slots or slot not in gt_slots:
            return False

        if not values_equal(slot, pred_slots.get(slot), gt_slots.get(slot)):
            return False

    return True


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    if len(predictions) != len(samples):
        raise ValueError("Predictions and ground truth must have the same length.")

    total = len(samples)
    intent_correct = 0
    exact_match_correct = 0

    intent_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    slot_stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    global_slot_stats = {"tp": 0, "fp": 0, "fn": 0}

    for prediction, sample in zip(predictions, samples):
        ground_truth = sample["annotation"]

        pred_intent = prediction.get("intent")
        gt_intent = ground_truth.get("intent")
        intent_stats[gt_intent]["total"] += 1

        if pred_intent == gt_intent:
            intent_correct += 1
            intent_stats[gt_intent]["correct"] += 1

        if sample_is_correct(prediction, sample):
            exact_match_correct += 1

        pred_slots = prediction.get("slots", {}) or {}
        gt_slots = ground_truth.get("slots", {}) or {}
        all_slots = set(pred_slots.keys()) | set(gt_slots.keys())

        for slot in all_slots:
            pred_has_slot = slot in pred_slots
            gt_has_slot = slot in gt_slots
            pred_value = pred_slots.get(slot)
            gt_value = gt_slots.get(slot)

            if gt_has_slot and not pred_has_slot:
                slot_stats[slot]["fn"] += 1
                global_slot_stats["fn"] += 1
            elif pred_has_slot and not gt_has_slot:
                slot_stats[slot]["fp"] += 1
                global_slot_stats["fp"] += 1
            elif values_equal(slot, pred_value, gt_value):
                slot_stats[slot]["tp"] += 1
                global_slot_stats["tp"] += 1
            else:
                slot_stats[slot]["fp"] += 1
                slot_stats[slot]["fn"] += 1
                global_slot_stats["fp"] += 1
                global_slot_stats["fn"] += 1

    return {
        "total_samples": total,
        "intent_accuracy": intent_correct / total if total else 0.0,
        "exact_match_accuracy": exact_match_correct / total if total else 0.0,
        "wrong_samples": total - exact_match_correct,
        "intents_by_type": {
            intent: {
                "accuracy": values["correct"] / values["total"] if values["total"] else 0.0,
                "correct": values["correct"],
                "total": values["total"],
            }
            for intent, values in intent_stats.items()
        },
        "slots_overall": precision_recall_f1(**global_slot_stats),
        "slots_by_type": {
            slot: precision_recall_f1(**counts)
            for slot, counts in slot_stats.items()
        },
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []

    for prediction, sample in zip(predictions, samples):
        if sample_is_correct(prediction, sample):
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
        load_time = time.time() - load_start
        print(f"Model loaded in {load_time:.1f}s.", flush=True)
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

        print_batch_done(
            batch_idx=batch_idx,
            total_batches=total_batches,
            batch_start=batch_start,
            eval_start=eval_start,
            completed=len(predictions),
            total_samples=total_samples,
        )

    metrics = compute_metrics(predictions, samples)
    wrong_examples = build_error_report(predictions, samples)

    results = {
        "model": model_name,
        "ground_truth_path": str(ground_truth_path),
        "metrics": metrics,
    }

    save_json(results, paths["results"])
    save_json(wrong_examples, paths["errors"])

    return {"results": results, "paths": paths}


def main() -> None:
    args = parse_args()
    output = run_evaluation(model_name=args.model, batch_size=args.batch_size)
    print(json.dumps(output["results"]["metrics"], indent=2, ensure_ascii=False), flush=True)
    print_final_paths(output["paths"])


if __name__ == "__main__":
    main()
