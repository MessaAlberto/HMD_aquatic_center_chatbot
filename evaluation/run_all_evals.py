import argparse
import gc
import json
import traceback
from pathlib import Path

import torch

from llm.loader import load_llm
from evaluation.eval_router import run_evaluation as run_router
from evaluation.eval_NLU import run_evaluation as run_nlu
from evaluation.eval_DM import run_evaluation as run_dm
from evaluation.eval_NLG import run_evaluation as run_nlg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all evaluations with one model load and a simple leaderboard metric per component.")
    parser.add_argument("-m", "--models", nargs="+", default=["qwen3_4b"], help="Model names defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Batch size for all evaluations.")
    parser.add_argument("--components", nargs="+", default=["router", "nlu", "dm", "nlg"], choices=["router", "nlu", "dm", "nlg"], help="Components to evaluate.")
    parser.add_argument("--summary-path", type=Path, default=Path("evaluation/results/leaderboard_summary.json"), help="Where to save the compact leaderboard summary.")
    return parser.parse_args()


def clear_model(llm) -> None:
    del llm
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def extract_main_metric(result: dict) -> float:
    metrics = result.get("results", {}).get("metrics", {})
    return float(metrics.get("main_metric", 0.0))


def run_component(component_name: str, run_fn, model_name: str, batch_size: int, llm) -> dict:
    print(f"\nRunning {component_name.upper()} evaluation...", flush=True)
    output = run_fn(model_name=model_name, batch_size=batch_size, llm=llm)
    main_metric = extract_main_metric(output)
    print(f"{component_name.upper()} main_metric: {main_metric:.4f}", flush=True)
    return {
        "component": component_name,
        "main_metric": main_metric,
        "metrics": output.get("results", {}).get("metrics", {}),
        "results_path": str(output.get("paths", {}).get("results", "")),
        "errors_path": str(output.get("paths", {}).get("errors", "")),
        "manual_review_path": str(output.get("paths", {}).get("manual_review", "")),
    }


def run_for_model(model_name: str, batch_size: int, components: list[str]) -> dict:
    print("=" * 80, flush=True)
    print(f"Loading model once: {model_name}", flush=True)
    llm = load_llm(model_name)
    model_summary = {"model": model_name, "components": {}}

    try:
        if "router" in components:
            model_summary["components"]["router"] = run_component("router", run_router, model_name, batch_size, llm)
        if "nlu" in components:
            model_summary["components"]["nlu"] = run_component("nlu", run_nlu, model_name, batch_size, llm)
        if "dm" in components:
            model_summary["components"]["dm"] = run_component("dm", run_dm, model_name, batch_size, llm)
        if "nlg" in components:
            model_summary["components"]["nlg"] = run_component("nlg", run_nlg, model_name, batch_size, llm)
    finally:
        clear_model(llm)
        print(f"\nReleased model from memory: {model_name}", flush=True)

    return model_summary


def main() -> None:
    args = parse_args()
    leaderboard = []

    for model_name in args.models:
        try:
            leaderboard.append(run_for_model(model_name=model_name, batch_size=args.batch_size, components=args.components))
        except Exception:
            print(f"\nEvaluation failed for model: {model_name}", flush=True)
            traceback.print_exc()
            raise

    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(args.summary_path, "w", encoding="utf-8") as file:
        json.dump(leaderboard, file, indent=2, ensure_ascii=False)

    print(f"\nCompact leaderboard saved to: {args.summary_path}", flush=True)
    print(json.dumps(leaderboard, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
