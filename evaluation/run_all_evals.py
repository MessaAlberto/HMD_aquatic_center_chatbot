import argparse
import gc
import inspect
import traceback

import torch

from llm.loader import load_llm
from evaluation.eval_router import run_evaluation as run_router
from evaluation.eval_NLU import run_evaluation as run_nlu
from evaluation.eval_DM import run_evaluation as run_dm
from evaluation.eval_NLG import run_evaluation as run_nlg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all evaluations with one model load.")
    parser.add_argument("-m", "--models", nargs="+", default=["qwen3_4b"], help="Model names defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Batch size for all evaluations.")
    parser.add_argument("--components", nargs="+", default=["router", "nlu", "dm", "nlg"], choices=["router", "nlu", "dm", "nlg"], help="Components to evaluate.")
    return parser.parse_args()


def clear_model(llm) -> None:
    del llm
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def run_component(component_name: str, run_fn, model_name: str, batch_size: int, llm) -> None:
    print(f"\nRunning {component_name.upper()} evaluation...", flush=True)

    kwargs = {"model_name": model_name, "batch_size": batch_size, "llm": llm}

    if component_name == "nlg" and "manual_review" in inspect.signature(run_fn).parameters:
        kwargs["manual_review"] = True

    run_fn(**kwargs)


def run_for_model(model_name: str, batch_size: int, components: list[str]) -> None:
    print("=" * 80, flush=True)
    print(f"Loading model once: {model_name}", flush=True)

    llm = load_llm(model_name)

    try:
        if "router" in components:
            run_component("router", run_router, model_name, batch_size, llm)

        if "nlu" in components:
            run_component("nlu", run_nlu, model_name, batch_size, llm)

        if "dm" in components:
            run_component("dm", run_dm, model_name, batch_size, llm)

        if "nlg" in components:
            run_component("nlg", run_nlg, model_name, batch_size, llm)

    finally:
        clear_model(llm)
        print(f"\nReleased model from memory: {model_name}", flush=True)


def main() -> None:
    args = parse_args()

    for model_name in args.models:
        try:
            run_for_model(model_name=model_name, batch_size=args.batch_size, components=args.components)
        except Exception:
            print(f"\nEvaluation failed for model: {model_name}", flush=True)
            traceback.print_exc()
            raise


if __name__ == "__main__":
    main()
