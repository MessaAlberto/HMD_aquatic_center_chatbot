import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Tuple

from tqdm.auto import tqdm


MAX_NEW_TOKENS = 256


def ensure_project_root(file_path: str, parents_up: int = 1) -> Path:
    project_root = Path(file_path).resolve().parents[parents_up]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


def safe_folder_name(name: str) -> str:
    name = str(name).strip()
    name = re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)
    return name or "unknown_model"


def get_eval_paths(file_path: str, component_name: str, model_name: str | None = None) -> Dict[str, Path]:
    base_dir = Path(file_path).resolve().parent
    name = component_name.lower()
    results_dir = base_dir / "results"

    if model_name is not None:
        results_dir = results_dir / safe_folder_name(model_name)

    return {
        "ground_truth": base_dir / "ground_truth_data" / f"{name}_ground_truth.json",
        "results_dir": results_dir,
        "results": results_dir / f"{name}_results.json",
        "errors": results_dir / f"{name}_errors.json",
        "predictions": results_dir / f"{name}_predictions.json",
        "manual_review": results_dir / f"{name}_manual_review.json",
    }


def load_json_list(path: Path, label: str = "Ground truth") -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{label} file must contain a list of samples.")

    return data


def save_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def parse_json_object(
    text: str,
    fallback: Dict[str, Any],
    normalizer: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
    except Exception:
        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            return fallback

        try:
            parsed = json.loads(match.group(1))
        except Exception:
            return fallback

    if not isinstance(parsed, dict):
        return fallback

    if normalizer is not None:
        return normalizer(parsed)

    return parsed


def normalize_basic_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if value.lower() in {"", "null", "none"}:
            return None
        return value.lower()

    if isinstance(value, list):
        return [normalize_basic_value(item) for item in value]

    if isinstance(value, dict):
        return {str(key): normalize_basic_value(val) for key, val in sorted(value.items())}

    return value


def basic_values_equal(pred_value: Any, gt_value: Any) -> bool:
    return normalize_basic_value(pred_value) == normalize_basic_value(gt_value)


def precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    precision = tp / (tp + fp) if tp + fp > 0 else 0.0
    recall = tp / (tp + fn) if tp + fn > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "support": tp + fn,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def get_total_batches(total_samples: int, batch_size: int) -> int:
    return (total_samples + batch_size - 1) // batch_size


def iter_batches(
    samples: List[Dict[str, Any]],
    batch_size: int,
    description: str,
) -> Iterator[Tuple[int, int, List[Dict[str, Any]], float]]:
    total_samples = len(samples)
    total_batches = get_total_batches(total_samples, batch_size)

    progress_bar = tqdm(
        range(0, total_samples, batch_size),
        desc=description,
        total=total_batches,
        dynamic_ncols=True,
    )

    for batch_idx, start in enumerate(progress_bar, start=1):
        batch_start = time.time()
        batch_samples = samples[start:start + batch_size]
        current_end = start + len(batch_samples)

        print(
            f"Batch {batch_idx}/{total_batches} | "
            f"samples {start + 1}-{current_end}/{total_samples} started",
            flush=True,
        )

        yield batch_idx, start, batch_samples, batch_start


def print_batch_done(
    batch_idx: int,
    total_batches: int,
    batch_start: float,
    eval_start: float,
    completed: int,
    total_samples: int,
) -> None:
    batch_time = time.time() - batch_start
    elapsed = time.time() - eval_start
    speed = completed / elapsed if elapsed > 0 else 0.0

    print(
        f"Batch {batch_idx}/{total_batches} completed in {batch_time:.1f}s | "
        f"{completed}/{total_samples} samples done | "
        f"avg {speed:.2f} samples/s",
        flush=True,
    )


def print_final_paths(
    paths: Dict[str, Path],
    include_predictions: bool = False,
    include_manual_review: bool = False,
) -> None:
    print(f"\nResults saved to: {paths['results']}", flush=True)
    print(f"Wrong examples saved to: {paths['errors']}", flush=True)

    if include_predictions:
        print(f"Predictions saved to: {paths['predictions']}", flush=True)

    if include_manual_review:
        print(f"Manual review file saved to: {paths['manual_review']}", flush=True)
