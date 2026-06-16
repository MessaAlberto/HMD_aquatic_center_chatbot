from prompts.router_prompt import ROUTER_SYSTEM_PROMPT
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

PATHS = get_eval_paths(__file__, "router")
GROUND_TRUTH_PATH = PATHS["ground_truth"]
SOFT_SEGMENT_F1_THRESHOLD = 0.90

LEADING_FILLERS = [
    "oh and",
    "oh, and",
    "by the way",
    "and",
    "also",
    "hi",
    "hello",
    "thanks",
    "thank you",
    "good morning",
    "good evening",
    "please",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the Router with one simple soft metric.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Number of samples processed in each generation batch.")
    return parser.parse_args()


def build_messages(sample: Dict[str, Any]) -> List[Dict[str, str]]:
    payload = {
        "conversation_history": sample.get("conversation_history", []),
        "last_user_utterance": sample["last_user_utterance"],
    }
    return [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT.strip()},
        {"role": "user", "content": json.dumps(payload, indent=2)},
    ]


def normalize_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        normalized.append({
            "segment": str(segment.get("segment", "")).strip(),
            "intent": str(segment.get("intent", "")).strip(),
        })
    return normalized


def normalize_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    segments = prediction.get("segments", [])
    if not isinstance(segments, list):
        segments = []
    return {"segments": normalize_segments(segments)}


def parse_llm_json(text: str) -> Dict[str, Any]:
    return parse_json_object(
        text=text,
        fallback={"segments": []},
        normalizer=normalize_prediction,
    )


def strip_leading_fillers(text: Any) -> str:
    text = str(text or "").strip()
    changed = True
    while changed:
        changed = False
        for filler in LEADING_FILLERS:
            pattern = rf"^\s*{re.escape(filler)}\b[\s,.:;!-]*"
            new_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            if new_text != text:
                text = new_text
                changed = True
    return text


def normalize_text(text: Any) -> str:
    text = strip_leading_fillers(text).lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def token_f1(pred_text: Any, gt_text: Any) -> float:
    pred_tokens = normalize_text(pred_text).split()
    gt_tokens = normalize_text(gt_text).split()

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


def soft_segment_match(prediction: Dict[str, Any], ground_truth: Dict[str, Any]) -> tuple[bool, List[Dict[str, Any]]]:
    pred = normalize_prediction(prediction)
    gt = normalize_prediction(ground_truth)

    details = []
    if len(pred["segments"]) != len(gt["segments"]):
        return False, [{
            "reason": "segment_count_mismatch",
            "predicted_count": len(pred["segments"]),
            "expected_count": len(gt["segments"]),
        }]

    for index, (pred_segment, gt_segment) in enumerate(zip(pred["segments"], gt["segments"])):
        intent_ok = pred_segment["intent"] == gt_segment["intent"]
        f1 = token_f1(pred_segment["segment"], gt_segment["segment"])
        text_ok = f1 >= SOFT_SEGMENT_F1_THRESHOLD
        details.append({
            "index": index,
            "intent_ok": intent_ok,
            "text_f1": f1,
            "text_ok": text_ok,
            "prediction": pred_segment,
            "ground_truth": gt_segment,
        })
        if not intent_ok or not text_ok:
            return False, details

    return True, details


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(samples)
    correct = 0

    for prediction, sample in zip(predictions, samples):
        ok, _ = soft_segment_match(prediction, sample["annotation"])
        if ok:
            correct += 1

    return {
        "total_samples": total,
        "main_metric": correct / total if total else 0.0,
        "soft_segment_accuracy": correct / total if total else 0.0,
        "wrong_samples": total - correct,
        "soft_segment_f1_threshold": SOFT_SEGMENT_F1_THRESHOLD,
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []
    for prediction, sample in zip(predictions, samples):
        ok, details = soft_segment_match(prediction, sample["annotation"])
        if ok:
            continue
        wrong_examples.append({
            "id": sample.get("id"),
            "input": {
                "conversation_history": sample.get("conversation_history", []),
                "last_user_utterance": sample.get("last_user_utterance"),
            },
            "ground_truth": normalize_prediction(sample["annotation"]),
            "prediction": normalize_prediction(prediction),
            "match_details": details,
        })
    return wrong_examples


def run_evaluation(model_name: str, batch_size: int, llm: Any = None) -> Dict[str, Any]:
    paths = get_eval_paths(__file__, "router", model_name=model_name)
    ground_truth_path = paths["ground_truth"]

    print(f"Loading ground truth from: {ground_truth_path}", flush=True)
    samples = load_json_list(ground_truth_path)
    total_samples = len(samples)
    total_batches = get_total_batches(total_samples, batch_size)

    print(f"Loaded {total_samples} Router test samples.", flush=True)
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

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating Router"):
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
