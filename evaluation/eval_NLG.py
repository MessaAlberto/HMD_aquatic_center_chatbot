import argparse
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from evaluation.utils import (
    ensure_project_root,
    get_eval_paths,
    get_total_batches,
    iter_batches,
    load_json_list,
    print_batch_done,
    print_final_paths,
    save_json,
)

ensure_project_root(__file__)

PATHS = get_eval_paths(__file__, "nlg")
DEFAULT_GROUND_TRUTH_PATH = PATHS["ground_truth"]
MAX_NEW_TOKENS = 256

INTERNAL_TERMS = [
    "dialogue state",
    "dm instruction",
    "current dm",
    "current dialogue",
    "enriched_data",
    "request_slot",
    "provide_information",
    "clarify_invalid_value",
    "resolve_conflict",
    "notify_success",
    "notify_aborted",
    "step_by_step_mode",
    "is_multitask",
    "is_second_response",
    "queue_recovery",
    "service_type",
    "sub_type",
    "user_category",
    "facility_type",
    "course_activity",
    "target_age",
    "day_preference",
    "people_count",
    "name_surname",
    "last_seen_location",
    "last_seen_date",
    "specific_inquiry",
    "nba",
]

FALSE_PROMISE_WORDS = [
    "confirmed",
    "booked",
    "reserved",
    "finalized",
    "all set",
    "saved",
    "completed",
]

QUESTION_STARTERS = {
    "what", "which", "when", "where", "who", "how", "can", "could", "would", "do", "does", "did", "is", "are"
}

SLOT_KEYWORDS = {
    "facility_type": ["facility", "area", "service", "pool", "gym", "spa", "lido", "reception"],
    "service_type": ["service", "pass", "entry", "course", "gym", "spa", "lido", "swim"],
    "sub_type": ["pass", "entry", "subscription", "monthly", "annual", "10-entry", "single"],
    "user_category": ["adult", "child", "student", "senior", "category", "ticket"],
    "topic": ["area", "facility", "rules", "policy", "policies", "pool", "gym", "spa", "lido", "changing"],
    "specific_inquiry": ["rule", "rules", "policy", "about", "know"],
    "course_activity": ["course", "aquagym", "hydrobike", "swimming", "newborn"],
    "target_age": ["age", "child", "teen", "adult"],
    "level": ["level", "beginner", "intermediate", "advanced"],
    "day_preference": ["day", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
    "date": ["date", "day", "when"],
    "time": ["time", "hour", "when", "10:00", "21:00"],
    "people_count": ["people", "person", "guests", "how many"],
    "name": ["name", "first name"],
    "surname": ["surname", "last name"],
    "name_surname": ["name", "surname", "full name", "first name", "last name"],
    "confirmation": ["confirm", "correct", "agree", "proceed", "is that right"],
    "item": ["item", "equipment", "goggles", "towel", "swimsuit", "slippers", "cap"],
    "color": ["color", "colour", "blue", "black", "red", "white", "green", "yellow", "clear", "purple"],
    "size": ["size", "xs", "s", "m", "l", "xl"],
    "brand": ["brand", "arena", "speedo", "decathlon", "adidas", "nike"],
    "lost_item": ["item", "lost", "towel", "goggles", "wallet", "backpack"],
    "item_color": ["color", "colour"],
    "last_seen_location": ["where", "location", "area", "last see", "last seen"],
    "last_seen_date": ["when", "date", "day", "last see", "last seen"],
}

CATEGORY_FOR_CHECK = {
    "no_json": "style_compliance",
    "no_internal_terms": "style_compliance",
    "max_words": "style_compliance",
    "max_sentences": "style_compliance",
    "max_questions": "style_compliance",
    "must_be_question": "dialogue_act_accuracy",
    "must_not_be_question": "dialogue_act_accuracy",
    "request_slot_focus": "dialogue_act_accuracy",
    "must_contain": "slot_factual_accuracy",
    "must_contain_any": "slot_factual_accuracy",
    "must_mention_options": "completeness",
    "must_not_contain": "hallucination_free",
    "no_false_promise": "hallucination_free",
    "no_unexpected_money": "hallucination_free",
    "no_unexpected_times": "hallucination_free",
}

class EvalHistory:
    def __init__(self, messages: List[Dict[str, str]] | None = None):
        self.messages = messages or []

    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        return self.messages[-n:]

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the NLG LLM output with rule-based checks.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Number of samples shown in each progress batch.")
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH_PATH, help="Path to nlg_ground_truth.json.")
    parser.add_argument("--results-dir", type=Path, default=None, help="Optional custom directory for result files.")
    parser.add_argument("--predictions-path", type=Path, default=None, help="Optional path with pre-generated outputs to evaluate.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional limit for quick tests.")
    parser.add_argument("--manual-review", action="store_true", help="Create nlg_manual_review.json with empty human scores.")
    return parser.parse_args()

def load_nlg_class():
    try:
        from components.NLG import NLG
        return NLG
    except ModuleNotFoundError as exc:
        if exc.name not in {"components", "components.NLG"}:
            raise

    try:
        from NLG import NLG
        return NLG
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Could not import NLG. Expected components/NLG.py from the project root."
        ) from exc


def load_predictions(path: Path) -> Dict[str, str]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return {str(key): str(value) for key, value in data.items()}

    if isinstance(data, list):
        predictions = {}
        for item in data:
            sample_id = item.get("id") or item.get("sample_id")
            prediction = item.get("prediction") or item.get("output") or item.get("text")
            if sample_id and prediction is not None:
                predictions[str(sample_id)] = str(prediction)
        return predictions

    raise ValueError("Predictions file must be a dict or a list of prediction records.")

def normalize_text(text: str) -> str:
    text = text.lower().replace("_", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_option(value: Any) -> str:
    text = str(value).lower().replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))

def count_sentences(text: str) -> int:
    fragments = [item for item in re.split(r"[.!?]+", text.strip()) if item.strip()]
    return len(fragments)

def count_questions(text: str) -> int:
    return text.count("?")

def starts_like_question(text: str) -> bool:
    stripped = text.strip().lower()
    first = re.match(r"^[a-z']+", stripped)
    if not first:
        return False
    return first.group(0) in QUESTION_STARTERS

def is_question(text: str) -> bool:
    return "?" in text or starts_like_question(text)

def flatten_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        values = []
        for key, val in value.items():
            values.extend(flatten_values(key))
            values.extend(flatten_values(val))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(flatten_values(item))
        return values
    return [str(value)]

def extract_money_values(text: str) -> List[float]:
    values = []
    patterns = [
        r"€\s*(\d+(?:[.,]\d+)?)",
        r"\b(\d+(?:[.,]\d+)?)\s*(?:euro|euros)\b",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text.lower()):
            try:
                values.append(float(match.replace(",", ".")))
            except ValueError:
                continue
    return values

def extract_time_values(text: str) -> List[str]:
    return re.findall(r"\b\d{1,2}:\d{2}\b", text)

def allowed_money_values(sample: Dict[str, Any]) -> List[float]:
    values = []
    raw_values = []
    raw_values.extend(flatten_values(sample.get("input", {}).get("dm_action", {})))
    raw_values.extend(flatten_values(sample.get("checks", {}).get("allowed_money_values", [])))

    for raw in raw_values:
        if isinstance(raw, str) and not re.search(r"\d", raw):
            continue
        try:
            values.append(float(str(raw).replace(",", ".")))
        except ValueError:
            continue

    return values

def allowed_time_values(sample: Dict[str, Any]) -> List[str]:
    values = []
    values.extend(flatten_values(sample.get("input", {}).get("dm_action", {})))
    values.extend(flatten_values(sample.get("input", {}).get("dialogue_state", {})))
    values.extend(flatten_values(sample.get("checks", {}).get("allowed_time_values", [])))
    return extract_time_values(" ".join(values))

def contains_term(text_norm: str, term: str) -> bool:
    term_norm = normalize_option(term)
    alt_norm = term_norm.replace(" ", "-")
    text_space = text_norm.replace("-", " ")
    return term_norm in text_space or alt_norm in text_norm

def check_no_json(prediction: str) -> Tuple[bool, str]:
    stripped = prediction.strip()
    if not stripped:
        return False, "Empty output."
    if stripped.startswith("{") or stripped.startswith("["):
        return False, "Output looks like JSON instead of natural language."
    if re.search(r'"\s*(nba|slot|enriched_data|intent)\s*"', prediction, flags=re.IGNORECASE):
        return False, "Output contains JSON-like internal fields."
    return True, ""

def check_no_internal_terms(prediction: str) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    found = [term for term in INTERNAL_TERMS if contains_term(text, term)]
    if found:
        return False, f"Internal terms found: {found}"
    return True, ""

def check_must_contain(prediction: str, terms: List[str]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    missing = [term for term in terms if not contains_term(text, term)]
    if missing:
        return False, f"Missing required terms: {missing}"
    return True, ""

def check_must_contain_any(prediction: str, groups: List[List[str]]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    missing_groups = []
    for group in groups:
        if not any(contains_term(text, term) for term in group):
            missing_groups.append(group)
    if missing_groups:
        return False, f"Missing at least one term from groups: {missing_groups}"
    return True, ""

def check_must_not_contain(prediction: str, terms: List[str]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    found = [term for term in terms if contains_term(text, term)]
    if found:
        return False, f"Forbidden terms found: {found}"
    return True, ""

def check_options(prediction: str, options: List[Any]) -> Tuple[bool, str]:
    if not options:
        return True, ""
    text = normalize_text(prediction)
    missing = []
    for option in options:
        option_text = normalize_option(option)
        compact_text = option_text.replace(" ", "")
        text_compact = text.replace(" ", "").replace("-", "")
        if not contains_term(text, option_text) and compact_text not in text_compact:
            missing.append(option)
    if missing:
        return False, f"Some valid options are not mentioned: {missing}"
    return True, ""

def check_request_slot_focus(prediction: str, slot: str | None) -> Tuple[bool, str]:
    if not slot:
        return True, ""
    keywords = SLOT_KEYWORDS.get(slot, [slot.replace("_", " ")])
    text = normalize_text(prediction)
    if any(contains_term(text, keyword) for keyword in keywords):
        return True, ""
    return False, f"The response does not clearly ask for the expected slot '{slot}'."

def check_false_promise(prediction: str, dm_action: Dict[str, Any]) -> Tuple[bool, str]:
    nba = dm_action.get("nba")
    slot = dm_action.get("slot")

    if nba == "notify_success" or slot == "confirmation":
        return True, ""

    text = normalize_text(prediction)
    found = [word for word in FALSE_PROMISE_WORDS if contains_term(text, word)]
    if found:
        return False, f"Possible premature finalization words found: {found}"
    return True, ""

def check_unexpected_money(prediction: str, sample: Dict[str, Any]) -> Tuple[bool, str]:
    found = extract_money_values(prediction)
    if not found:
        return True, ""

    allowed = allowed_money_values(sample)
    unexpected = []
    for value in found:
        if not any(abs(value - allowed_value) < 0.01 for allowed_value in allowed):
            unexpected.append(value)

    if unexpected:
        return False, f"Unexpected money values found: {unexpected}; allowed values: {allowed}"
    return True, ""

def check_unexpected_times(prediction: str, sample: Dict[str, Any]) -> Tuple[bool, str]:
    found = extract_time_values(prediction)
    if not found:
        return True, ""

    allowed = set(allowed_time_values(sample))
    unexpected = [value for value in found if value not in allowed]
    if unexpected:
        return False, f"Unexpected time values found: {unexpected}; allowed values: {sorted(allowed)}"
    return True, ""

def evaluate_prediction(prediction: str, sample: Dict[str, Any]) -> Dict[str, Any]:
    checks = sample.get("checks", {})
    input_data = sample.get("input", {})
    dm_action = input_data.get("dm_action", {})
    results = []

    def add_check(name: str, passed: bool, message: str = "", mandatory: bool = True) -> None:
        results.append({
            "name": name,
            "category": CATEGORY_FOR_CHECK.get(name, "other"),
            "passed": bool(passed),
            "mandatory": bool(mandatory),
            "message": message,
        })

    passed, message = check_no_json(prediction)
    add_check("no_json", passed, message)

    passed, message = check_no_internal_terms(prediction)
    add_check("no_internal_terms", passed, message)

    max_words = checks.get("max_words", 35 if dm_action.get("is_multitask") else 45)
    words = count_words(prediction)
    add_check("max_words", words <= max_words, f"{words} words > max {max_words}" if words > max_words else "")

    max_sentences = checks.get("max_sentences", 1 if dm_action.get("is_multitask") and not dm_action.get("is_second_response") else 2)
    sentences = count_sentences(prediction)
    add_check("max_sentences", sentences <= max_sentences, f"{sentences} sentences > max {max_sentences}" if sentences > max_sentences else "")

    if "max_questions" in checks:
        questions = count_questions(prediction)
        max_questions = checks["max_questions"]
        add_check("max_questions", questions <= max_questions, f"{questions} questions > max {max_questions}" if questions > max_questions else "")

    if checks.get("must_be_question") is True:
        add_check("must_be_question", is_question(prediction), "Response should be a question.")

    if checks.get("must_not_be_question") is True:
        add_check("must_not_be_question", not is_question(prediction), "Response should not be a question.")

    if checks.get("request_slot_focus") is True or dm_action.get("nba") == "request_slot":
        passed, message = check_request_slot_focus(prediction, dm_action.get("slot"))
        add_check("request_slot_focus", passed, message)

    if checks.get("must_mention_options") is True:
        passed, message = check_options(prediction, dm_action.get("options", []))
        add_check("must_mention_options", passed, message)

    if checks.get("must_contain"):
        passed, message = check_must_contain(prediction, checks["must_contain"])
        add_check("must_contain", passed, message)

    if checks.get("must_contain_any"):
        passed, message = check_must_contain_any(prediction, checks["must_contain_any"])
        add_check("must_contain_any", passed, message)

    combined_forbidden = list(checks.get("must_not_contain", []))
    passed, message = check_must_not_contain(prediction, combined_forbidden)
    if combined_forbidden:
        add_check("must_not_contain", passed, message)

    if checks.get("no_false_promise", True):
        passed, message = check_false_promise(prediction, dm_action)
        add_check("no_false_promise", passed, message)

    if checks.get("no_unexpected_money", True):
        passed, message = check_unexpected_money(prediction, sample)
        add_check("no_unexpected_money", passed, message)

    if checks.get("no_unexpected_times", True):
        passed, message = check_unexpected_times(prediction, sample)
        add_check("no_unexpected_times", passed, message)

    mandatory_checks = [item for item in results if item["mandatory"]]
    passed_count = sum(1 for item in mandatory_checks if item["passed"])
    failed = [item for item in mandatory_checks if not item["passed"]]
    score = passed_count / len(mandatory_checks) if mandatory_checks else 0.0

    return {
        "passed": len(failed) == 0,
        "score": score,
        "checks": results,
        "failed_checks": failed,
    }

def generate_prediction(nlg: Any, sample: Dict[str, Any]) -> str:
    input_data = sample["input"]
    history = EvalHistory(input_data.get("history", []))
    return nlg.predict(
        dm_action_data=input_data["dm_action"],
        dialogue_state=input_data["dialogue_state"],
        history=history,
    )

def compute_metrics(evaluations: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(evaluations)
    passed = sum(1 for evaluation in evaluations if evaluation["passed"])
    avg_score = sum(evaluation["score"] for evaluation in evaluations) / total if total else 0.0

    category_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    intent_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    nba_stats = defaultdict(lambda: {"total": 0, "passed": 0})

    for evaluation, sample in zip(evaluations, samples):
        intent = sample.get("input", {}).get("dialogue_state", {}).get("intent", "unknown")
        nba = sample.get("input", {}).get("dm_action", {}).get("nba", "unknown")
        intent_stats[intent]["total"] += 1
        nba_stats[nba]["total"] += 1
        if evaluation["passed"]:
            intent_stats[intent]["passed"] += 1
            nba_stats[nba]["passed"] += 1

        for check in evaluation["checks"]:
            if not check["mandatory"]:
                continue
            category = check["category"]
            category_stats[category]["total"] += 1
            if check["passed"]:
                category_stats[category]["passed"] += 1

    def summarize(stats: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        return {
            key: {
                "accuracy": value["passed"] / value["total"] if value["total"] else 0.0,
                "passed": value["passed"],
                "total": value["total"],
            }
            for key, value in sorted(stats.items())
        }

    return {
        "total_samples": total,
        "automatic_success_rate": passed / total if total else 0.0,
        "wrong_samples": total - passed,
        "average_rule_score": avg_score,
        "category_accuracy": summarize(category_stats),
        "success_by_intent": summarize(intent_stats),
        "success_by_nba": summarize(nba_stats),
    }

def build_error_report(predictions: List[str], evaluations: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    errors = []
    for prediction, evaluation, sample in zip(predictions, evaluations, samples):
        if evaluation["passed"]:
            continue
        errors.append({
            "id": sample.get("id"),
            "input": sample.get("input"),
            "prediction": prediction,
            "score": evaluation["score"],
            "failed_checks": evaluation["failed_checks"],
        })
    return errors


def build_manual_review_report(
    predictions: List[str],
    evaluations: List[Dict[str, Any]],
    samples: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    report = []

    for prediction, evaluation, sample in zip(predictions, evaluations, samples):
        input_data = sample.get("input", {})
        report.append({
            "id": sample.get("id"),
            "prediction": prediction,
            "automatic_passed": evaluation["passed"],
            "automatic_score": evaluation["score"],
            "dialogue_state": input_data.get("dialogue_state", {}),
            "dm_action": input_data.get("dm_action", {}),
            "checks": sample.get("checks", {}),
            "semantic_score": None,
            "naturalness_score": None,
            "notes": "",
        })

    return report

def run_evaluation(
    model_name: str,
    batch_size: int,
    llm: Any = None,
    ground_truth_path: Path | None = None,
    results_dir: Path | None = None,
    predictions_path: Path | None = None,
    max_samples: int | None = None,
    manual_review: bool = False,
) -> Dict[str, Any]:
    paths = get_eval_paths(__file__, "nlg", model_name=model_name)

    if results_dir is not None:
        results_dir = Path(results_dir)
        paths["results_dir"] = results_dir
        paths["results"] = results_dir / "nlg_results.json"
        paths["errors"] = results_dir / "nlg_errors.json"
        paths["predictions"] = results_dir / "nlg_predictions.json"
        paths["manual_review"] = results_dir / "nlg_manual_review.json"

    ground_truth_path = Path(ground_truth_path) if ground_truth_path is not None else paths["ground_truth"]
    predictions_path = Path(predictions_path) if predictions_path is not None else None

    print(f"Loading NLG test samples from: {ground_truth_path}", flush=True)
    samples = load_json_list(ground_truth_path, label="NLG ground truth")
    if max_samples is not None:
        samples = samples[:max_samples]

    total_samples = len(samples)
    total_batches = get_total_batches(total_samples, batch_size)

    print(f"Loaded {total_samples} NLG test samples.", flush=True)
    print(f"Batch size: {batch_size} -> {total_batches} batches.", flush=True)

    predictions_by_id = None
    nlg = None

    if predictions_path is not None:
        print(f"Loading pre-generated predictions from: {predictions_path}", flush=True)
        predictions_by_id = load_predictions(predictions_path)
    else:
        load_start = time.time()

        if llm is None:
            print(f"Loading model: {model_name}", flush=True)
            from llm.loader import load_llm
            llm = load_llm(model_name)
            print(f"Model loaded in {time.time() - load_start:.1f}s.", flush=True)
        else:
            print(f"Using already loaded model: {model_name}", flush=True)

        NLG = load_nlg_class()
        nlg = NLG(llm)
        print(f"NLG ready in {time.time() - load_start:.1f}s.", flush=True)

    predictions = []
    evaluations = []
    eval_start = time.time()

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating NLG"):
        for sample in batch_samples:
            if predictions_by_id is not None:
                prediction = predictions_by_id.get(str(sample.get("id")), "")
            else:
                prediction = generate_prediction(nlg, sample)

            predictions.append(prediction)
            evaluations.append(evaluate_prediction(prediction, sample))

        print_batch_done(
            batch_idx=batch_idx,
            total_batches=total_batches,
            batch_start=batch_start,
            eval_start=eval_start,
            completed=len(predictions),
            total_samples=total_samples,
        )

    metrics = compute_metrics(evaluations, samples)
    error_report = build_error_report(predictions, evaluations, samples)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = {
        "model": model_name,
        "predictions_path": str(predictions_path) if predictions_path else None,
        "ground_truth_path": str(ground_truth_path),
        "created_at": timestamp,
        "metrics": metrics,
    }

    prediction_records = [
        {
            "id": sample.get("id"),
            "prediction": prediction,
            "automatic_passed": evaluation["passed"],
            "score": evaluation["score"],
        }
        for sample, prediction, evaluation in zip(samples, predictions, evaluations)
    ]

    save_json(results, paths["results"])
    save_json(error_report, paths["errors"])
    save_json(prediction_records, paths["predictions"])

    if manual_review:
        manual_review_report = build_manual_review_report(predictions, evaluations, samples)
        save_json(manual_review_report, paths["manual_review"])

    return {"results": results, "paths": paths}


def main() -> None:
    args = parse_args()
    output = run_evaluation(
        model_name=args.model,
        batch_size=args.batch_size,
        ground_truth_path=args.ground_truth,
        results_dir=args.results_dir,
        predictions_path=args.predictions_path,
        max_samples=args.max_samples,
        manual_review=args.manual_review,
    )

    print(json.dumps(output["results"]["metrics"], indent=2, ensure_ascii=False), flush=True)
    print_final_paths(
        output["paths"],
        include_predictions=True,
        include_manual_review=args.manual_review,
    )


if __name__ == "__main__":
    main()
