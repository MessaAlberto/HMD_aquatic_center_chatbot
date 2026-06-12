from prompts.dm_prompt import DM_SYSTEM_PROMPT
from llm.loader import load_llm
import argparse
import json
import time
from collections import defaultdict
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
    precision_recall_f1,
    print_batch_done,
    print_final_paths,
    save_json,
)


ensure_project_root(__file__)


PATHS = get_eval_paths(__file__, "dm")
GROUND_TRUTH_PATH = PATHS["ground_truth"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the DM LLM output.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4,
                        help="Number of samples processed in each generation batch.")
    return parser.parse_args()


def build_messages(sample: Dict[str, Any]) -> List[Dict[str, str]]:
    payload_str = json.dumps(sample["input"], indent=2)
    return [
        {"role": "system", "content": DM_SYSTEM_PROMPT.strip()},
        {"role": "user", "content": f"CURRENT INPUT:\n{payload_str}"},
    ]


def empty_prediction() -> Dict[str, Any]:
    return {
        "nba": "fallback",
        "slot": None,
        "options": [],
        "blacklist": [],
        "enriched_data": {},
    }


def normalize_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nba": prediction.get("nba"),
        "slot": prediction.get("slot"),
        "options": prediction.get("options", []) or [],
        "blacklist": prediction.get("blacklist", []) or [],
        "enriched_data": prediction.get("enriched_data", {}) or {},
    }


def parse_llm_json(text: str) -> Dict[str, Any]:
    return parse_json_object(
        text=text,
        fallback=empty_prediction(),
        normalizer=normalize_prediction,
    )


def output_is_correct(prediction: Dict[str, Any], ground_truth: Dict[str, Any]) -> bool:
    prediction = normalize_prediction(prediction)
    ground_truth = normalize_prediction(ground_truth)

    for key in ["nba", "slot", "options", "blacklist", "enriched_data"]:
        if not basic_values_equal(prediction.get(key), ground_truth.get(key)):
            return False

    return True


def compute_field_accuracy(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]], field: str) -> float:
    if not samples:
        return 0.0

    correct = 0
    for prediction, sample in zip(predictions, samples):
        prediction = normalize_prediction(prediction)
        ground_truth = normalize_prediction(sample["annotation"])
        if basic_values_equal(prediction.get(field), ground_truth.get(field)):
            correct += 1

    return correct / len(samples)


def compute_metrics(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(samples)
    exact_match_correct = 0

    nba_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    status_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    nba_tp = defaultdict(int)
    nba_fp = defaultdict(int)
    nba_fn = defaultdict(int)

    for prediction, sample in zip(predictions, samples):
        prediction = normalize_prediction(prediction)
        ground_truth = normalize_prediction(sample["annotation"])

        gt_nba = ground_truth.get("nba")
        pred_nba = prediction.get("nba")
        status = sample["input"]["db_result"].get("status")

        nba_stats[gt_nba]["total"] += 1
        status_stats[status]["total"] += 1

        if output_is_correct(prediction, ground_truth):
            exact_match_correct += 1
            status_stats[status]["correct"] += 1

        if pred_nba == gt_nba:
            nba_stats[gt_nba]["correct"] += 1
            nba_tp[gt_nba] += 1
        else:
            nba_fp[pred_nba] += 1
            nba_fn[gt_nba] += 1

    return {
        "total_samples": total,
        "exact_match_accuracy": exact_match_correct / total if total else 0.0,
        "wrong_samples": total - exact_match_correct,
        "nba_accuracy": compute_field_accuracy(predictions, samples, "nba"),
        "slot_accuracy": compute_field_accuracy(predictions, samples, "slot"),
        "options_accuracy": compute_field_accuracy(predictions, samples, "options"),
        "blacklist_accuracy": compute_field_accuracy(predictions, samples, "blacklist"),
        "enriched_data_accuracy": compute_field_accuracy(predictions, samples, "enriched_data"),
        "nba_by_type": {
            nba: {
                "accuracy": values["correct"] / values["total"] if values["total"] else 0.0,
                "correct": values["correct"],
                "total": values["total"],
            }
            for nba, values in sorted(nba_stats.items())
        },
        "status_exact_match_by_type": {
            status: {
                "accuracy": values["correct"] / values["total"] if values["total"] else 0.0,
                "correct": values["correct"],
                "total": values["total"],
            }
            for status, values in sorted(status_stats.items())
        },
        "nba_f1_by_type": {
            nba: precision_recall_f1(tp=nba_tp[nba], fp=nba_fp[nba], fn=nba_fn[nba])
            for nba in sorted(set(nba_tp) | set(nba_fp) | set(nba_fn))
        },
    }


def build_error_report(predictions: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wrong_examples = []

    for prediction, sample in zip(predictions, samples):
        prediction = normalize_prediction(prediction)
        ground_truth = normalize_prediction(sample["annotation"])

        if output_is_correct(prediction, ground_truth):
            continue

        wrong_examples.append({
            "id": sample.get("id"),
            "input": sample.get("input"),
            "ground_truth": ground_truth,
            "prediction": prediction,
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
        load_time = time.time() - load_start
        print(f"Model loaded in {load_time:.1f}s.", flush=True)
    else:
        print(f"Using already loaded model: {model_name}", flush=True)

    predictions = []
    eval_start = time.time()

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating DM"):
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
