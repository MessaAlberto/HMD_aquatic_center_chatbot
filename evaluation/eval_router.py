from prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from llm.loader import load_llm
import argparse
import json
import re
import time
from collections import Counter, defaultdict
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


PATHS = get_eval_paths(__file__, "router")
GROUND_TRUTH_PATH = PATHS["ground_truth"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the Router LLM output only.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4,
                        help="Number of samples processed in each generation batch.")
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


def normalize_output(output: Dict[str, Any]) -> Dict[str, Any]:
    return normalize_prediction(output)


def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)

    return text


def token_f1(pred_text: str, gt_text: str) -> float:
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


def intent_sequence(output: Dict[str, Any]) -> List[str]:
    return [segment.get("intent", "") for segment in output.get("segments", [])]


def segment_count(output: Dict[str, Any]) -> int:
    return len(output.get("segments", []))


def output_is_correct(prediction: Dict[str, Any], ground_truth: Dict[str, Any]) -> bool:
    pred = normalize_output(prediction)
    gt = normalize_output(ground_truth)

    if segment_count(pred) != segment_count(gt):
        return False

    for pred_segment, gt_segment in zip(pred["segments"], gt["segments"]):
        if pred_segment["intent"] != gt_segment["intent"]:
            return False

        if normalize_text(pred_segment["segment"]) != normalize_text(gt_segment["segment"]):
            return False

    return True


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(samples)
    exact_match_correct = 0
    segment_count_correct = 0
    intent_sequence_correct = 0

    intent_tp = defaultdict(int)
    intent_fp = defaultdict(int)
    intent_fn = defaultdict(int)
    text_f1_values = []

    for prediction, sample in zip(predictions, samples):
        ground_truth = normalize_output(sample["annotation"])
        prediction = normalize_output(prediction)

        if output_is_correct(prediction, ground_truth):
            exact_match_correct += 1

        if segment_count(prediction) == segment_count(ground_truth):
            segment_count_correct += 1

        if intent_sequence(prediction) == intent_sequence(ground_truth):
            intent_sequence_correct += 1

        pred_intents = Counter(intent_sequence(prediction))
        gt_intents = Counter(intent_sequence(ground_truth))
        all_intents = set(pred_intents.keys()) | set(gt_intents.keys())

        for intent in all_intents:
            tp = min(pred_intents[intent], gt_intents[intent])
            fp = max(0, pred_intents[intent] - gt_intents[intent])
            fn = max(0, gt_intents[intent] - pred_intents[intent])

            intent_tp[intent] += tp
            intent_fp[intent] += fp
            intent_fn[intent] += fn

        for pred_segment, gt_segment in zip(prediction.get("segments", []), ground_truth.get("segments", [])):
            text_f1_values.append(token_f1(pred_segment.get("segment", ""), gt_segment.get("segment", "")))

    return {
        "total_samples": total,
        "exact_match_accuracy": exact_match_correct / total if total else 0.0,
        "wrong_samples": total - exact_match_correct,
        "segment_count_accuracy": segment_count_correct / total if total else 0.0,
        "intent_sequence_accuracy": intent_sequence_correct / total if total else 0.0,
        "average_segment_text_f1": sum(text_f1_values) / len(text_f1_values) if text_f1_values else 0.0,
        "intents_by_type": {
            intent: precision_recall_f1(tp=intent_tp[intent], fp=intent_fp[intent], fn=intent_fn[intent])
            for intent in sorted(set(intent_tp) | set(intent_fp) | set(intent_fn))
        },
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []

    for prediction, sample in zip(predictions, samples):
        ground_truth = normalize_output(sample["annotation"])
        prediction = normalize_output(prediction)

        if output_is_correct(prediction, ground_truth):
            continue

        wrong_examples.append({
            "id": sample.get("id"),
            "input": {
                "conversation_history": sample.get("conversation_history", []),
                "last_user_utterance": sample.get("last_user_utterance"),
            },
            "ground_truth": ground_truth,
            "prediction": prediction,
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
        load_time = time.time() - load_start
        print(f"Model loaded in {load_time:.1f}s.", flush=True)
    else:
        print(f"Using already loaded model: {model_name}", flush=True)

    predictions = []
    eval_start = time.time()

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating Router LLM"):
        messages_batch = [build_messages(sample) for sample in batch_samples]
        raw_outputs = llm.generate_batch(messages_batch=messages_batch, max_new_tokens=MAX_NEW_TOKENS)

        for raw_output in raw_outputs:
            predictions.append(parse_llm_json(raw_output))

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
