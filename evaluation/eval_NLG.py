import argparse
import copy
import json
import re
import time
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

HARD_CHECKS = {
    "no_json",
    "no_internal_terms",
    "must_be_question",
    "must_not_be_question",
    "request_slot_focus",
    "must_not_contain",
    "no_false_promise",
    "no_unexpected_money",
    "no_unexpected_times",
}

SOFT_CHECKS = {
    "max_words",
    "max_sentences",
    "max_questions",
    "must_contain",
    "must_contain_any",
    "must_mention_options",
    "flag_step_by_step",
    "flag_second_response",
    "flag_queue_recovery",
}

INTERNAL_TERMS = [
    "dialogue state", "dm instruction", "current dm", "current dialogue",
    "enriched_data", "request_slot", "provide_information", "clarify_invalid_value",
    "resolve_conflict", "notify_success", "notify_aborted", "step_by_step_mode",
    "is_multitask", "is_second_response", "queue_recovery", "service_type",
    "sub_type", "user_category", "facility_type", "course_activity", "target_age",
    "day_preference", "people_count", "name_surname", "last_seen_location",
    "last_seen_date", "specific_inquiry", "nba",
]

FALSE_PROMISE_WORDS = ["confirmed", "booked", "reserved", "finalized", "all set", "saved", "completed"]
QUESTION_STARTERS = {"what", "which", "when", "where", "who", "how", "can", "could", "would", "do", "does", "did", "is", "are"}

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
    "date_old": ["old date", "original date", "date", "day", "when"],
    "date_new": ["new date", "date", "day", "when"],
    "time": ["time", "hour", "when", "10:00", "21:00"],
    "time_old": ["old time", "original time", "time", "hour"],
    "time_new": ["new time", "time", "hour"],
    "people_count": ["people", "person", "guests", "how many"],
    "people_count_old": ["people", "person", "guests"],
    "people_count_new": ["people", "person", "guests"],
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
    "level_new": ["level", "beginner", "intermediate", "advanced"],
    "target_age_new": ["age", "child", "teen", "adult"],
    "day_preference_new": ["day", "monday", "tuesday", "wednesday", "thursday", "friday"],
    "course_activity_new": ["course", "aquagym", "hydrobike", "swimming", "newborn"],
}


class EvalHistory:
    def __init__(self, messages: List[Dict[str, str]] | None = None):
        self.messages = messages or []

    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        return self.messages[-n:]

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate NLG with failed/manual_review/passed statuses.")
    parser.add_argument("-m", "--model", type=str, default="qwen3_4b", help="Model name defined in llm/config.py.")
    parser.add_argument("-b", "--batch-size", type=int, default=4, help="Number of samples processed in each generation batch.")
    parser.add_argument("--ground-truth", type=Path, default=DEFAULT_GROUND_TRUTH_PATH, help="Path to nlg_ground_truth.json.")
    parser.add_argument("--results-dir", type=Path, default=None, help="Optional custom directory for result files.")
    parser.add_argument("--predictions-path", type=Path, default=None, help="Optional path with pre-generated outputs to evaluate.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional limit for quick tests.")
    parser.add_argument("--manual-review", action="store_true", help="Kept for compatibility. Manual review file is always created.")
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
        raise ModuleNotFoundError("Could not import NLG. Expected components/NLG.py from the project root.") from exc


def normalize_prediction_record(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        text = str(value.get("prediction") or value.get("output") or value.get("text") or "")
        responses = value.get("responses")
        if responses is None:
            responses = [text] if text else []
        return {"text": text, "responses": [str(item) for item in responses]}
    return {"text": str(value), "responses": [str(value)]}


def load_predictions(path: Path) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, dict):
        return {str(key): normalize_prediction_record(value) for key, value in data.items()}
    if isinstance(data, list):
        predictions = {}
        for item in data:
            sample_id = item.get("id") or item.get("sample_id")
            if sample_id:
                predictions[str(sample_id)] = normalize_prediction_record(item)
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


def contains_term(text_norm: str, term: str) -> bool:
    term_norm = normalize_option(term)
    alt_norm = term_norm.replace(" ", "-")
    text_space = text_norm.replace("-", " ")
    return term_norm in text_space or alt_norm in text_norm


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def count_sentences(text: str) -> int:
    protected = re.sub(r"(?<=\d)\.(?=\d)", "<DECIMAL_DOT>", text.strip())
    fragments = [item for item in re.split(r"[.!?]+", protected) if item.strip()]
    return len(fragments)


def count_questions(text: str) -> int:
    return text.count("?")


def starts_like_question(text: str) -> bool:
    stripped = text.strip().lower()
    first = re.match(r"^[a-z']+", stripped)
    return bool(first and first.group(0) in QUESTION_STARTERS)


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


def get_effective_actions(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "nba_list" not in input_data:
        return [copy.deepcopy(input_data.get("dm_action", {}))]
    nba_list = copy.deepcopy(input_data.get("nba_list", []))
    step_by_step_mode = bool(input_data.get("step_by_step_mode", False))
    if step_by_step_mode and nba_list:
        nba_list[0]["step_by_step_mode"] = True
    if len(nba_list) > 1:
        for nba in nba_list:
            nba["is_multitask"] = True
    for index, nba in enumerate(nba_list):
        if index > 0:
            nba["is_second_response"] = True
    return nba_list


def get_primary_action(input_data: Dict[str, Any]) -> Dict[str, Any]:
    actions = get_effective_actions(input_data)
    return actions[0] if actions else {}


def extract_money_values(text: str) -> List[float]:
    values = []
    patterns = [r"€\s*(\d+(?:[.,]\d+)?)", r"\b(\d+(?:[.,]\d+)?)\s*(?:euro|euros)\b"]
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
    raw_values = []
    input_data = sample.get("input", {})
    raw_values.extend(flatten_values(input_data.get("dm_action", {})))
    raw_values.extend(flatten_values(input_data.get("nba_list", [])))
    raw_values.extend(flatten_values(sample.get("checks", {}).get("allowed_money_values", [])))

    values = []
    for raw in raw_values:
        if isinstance(raw, str) and not re.search(r"\d", raw):
            continue
        try:
            values.append(float(str(raw).replace(",", ".")))
        except ValueError:
            continue
    return values


def allowed_time_values(sample: Dict[str, Any]) -> List[str]:
    input_data = sample.get("input", {})
    values = []
    values.extend(flatten_values(input_data.get("dm_action", {})))
    values.extend(flatten_values(input_data.get("nba_list", [])))
    values.extend(flatten_values(input_data.get("dialogue_state", {})))
    values.extend(flatten_values(input_data.get("dialogue_state_list", [])))
    values.extend(flatten_values(sample.get("checks", {}).get("allowed_time_values", [])))
    return extract_time_values(" ".join(values))


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
    return (not found, f"Internal terms found: {found}" if found else "")


def check_must_contain(prediction: str, terms: List[str]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    missing = [term for term in terms if not contains_term(text, term)]
    return (not missing, f"Missing required terms: {missing}" if missing else "")


def check_must_contain_any(prediction: str, groups: List[List[str]]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    missing_groups = []
    for group in groups:
        if not any(contains_term(text, term) for term in group):
            missing_groups.append(group)
    return (not missing_groups, f"Missing at least one term from groups: {missing_groups}" if missing_groups else "")


def check_must_not_contain(prediction: str, terms: List[str]) -> Tuple[bool, str]:
    text = normalize_text(prediction)
    found = [term for term in terms if contains_term(text, term)]
    return (not found, f"Forbidden terms found: {found}" if found else "")


def check_options(prediction: str, options: List[Any]) -> Tuple[bool, str]:
    if not options:
        return True, ""
    text = normalize_text(prediction)
    text_compact = text.replace(" ", "").replace("-", "")
    missing = []
    for option in options:
        option_text = normalize_option(option)
        compact_text = option_text.replace(" ", "")
        if not contains_term(text, option_text) and compact_text not in text_compact:
            missing.append(option)
    return (not missing, f"Some valid options are not mentioned: {missing}" if missing else "")


def check_request_slot_focus(prediction: str, slot: str | None) -> Tuple[bool, str]:
    if not slot:
        return True, ""
    keywords = SLOT_KEYWORDS.get(slot, [slot.replace("_", " ")])
    text = normalize_text(prediction)
    if any(contains_term(text, keyword) for keyword in keywords):
        return True, ""
    return False, f"The response does not clearly ask for the expected slot '{slot}'."


def is_negated_finalization(text: str, word: str) -> bool:
    patterns = [
        rf"\bno\b[^.!?]{{0,40}}\b{re.escape(word)}\b",
        rf"\bnot\b[^.!?]{{0,40}}\b{re.escape(word)}\b",
        rf"\bhas not been\b[^.!?]{{0,20}}\b{re.escape(word)}\b",
        rf"\bhasn't been\b[^.!?]{{0,20}}\b{re.escape(word)}\b",
        rf"\bnot\s+{re.escape(word)}\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def check_false_promise(prediction: str, dm_action: Dict[str, Any]) -> Tuple[bool, str]:
    if dm_action.get("nba") == "notify_success" or dm_action.get("slot") == "confirmation":
        return True, ""
    text = normalize_text(prediction)
    found = []
    for word in FALSE_PROMISE_WORDS:
        if contains_term(text, word) and not is_negated_finalization(text, word):
            found.append(word)
    return (not found, f"Possible premature finalization words found: {found}" if found else "")


def check_unexpected_money(prediction: str, sample: Dict[str, Any]) -> Tuple[bool, str]:
    found = extract_money_values(prediction)
    if not found:
        return True, ""
    allowed = allowed_money_values(sample)
    unexpected = [value for value in found if not any(abs(value - allowed_value) < 0.01 for allowed_value in allowed)]
    return (not unexpected, f"Unexpected money values found: {unexpected}; allowed values: {allowed}" if unexpected else "")


def check_unexpected_times(prediction: str, sample: Dict[str, Any]) -> Tuple[bool, str]:
    found = extract_time_values(prediction)
    if not found:
        return True, ""
    allowed = set(allowed_time_values(sample))
    unexpected = [value for value in found if value not in allowed]
    return (not unexpected, f"Unexpected time values found: {unexpected}; allowed values: {sorted(allowed)}" if unexpected else "")


def check_flag_step_by_step(prediction: str) -> Tuple[bool, str]:
    terms = ["one thing", "one step", "first", "start", "starting"]
    text = normalize_text(prediction)
    if any(contains_term(text, term) for term in terms):
        return True, ""
    return False, "step_by_step_mode should explicitly guide the user through one thing/step first."


def check_flag_second_response(prediction: str) -> Tuple[bool, str]:
    terms = ["as for", "regarding", "also", "and", "about"]
    text = normalize_text(prediction)
    if any(contains_term(text, term) for term in terms):
        return True, ""
    return False, "is_second_response should include a natural transition."


def check_flag_queue_recovery(prediction: str, recovered_intent: str | None) -> Tuple[bool, str]:
    terms = ["back", "going back", "previous", "earlier", "return", "resume"]
    if recovered_intent:
        terms.extend(recovered_intent.replace("_", " ").split())
    text = normalize_text(prediction)
    if any(contains_term(text, term) for term in terms):
        return True, ""
    return False, "queue_recovery should transition back to the previous/recovered topic."


def add_result(results: List[Dict[str, Any]], name: str, passed: bool, message: str = "") -> None:
    if name in HARD_CHECKS:
        severity = "hard"
    elif name in SOFT_CHECKS:
        severity = "soft"
    else:
        severity = "soft"
    results.append({"name": name, "severity": severity, "passed": bool(passed), "message": message})


def evaluate_prediction(prediction_record: Dict[str, Any] | str, sample: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(prediction_record, str):
        prediction_record = {"text": prediction_record, "responses": [prediction_record]}

    prediction = prediction_record.get("text", "")
    checks = sample.get("checks", {})
    input_data = sample.get("input", {})
    effective_actions = get_effective_actions(input_data)
    primary_action = get_primary_action(input_data)
    results = []

    passed, message = check_no_json(prediction)
    add_result(results, "no_json", passed, message)

    passed, message = check_no_internal_terms(prediction)
    add_result(results, "no_internal_terms", passed, message)

    max_words = checks.get("max_words", 35 if any(action.get("is_multitask") for action in effective_actions) else 45)
    words = count_words(prediction)
    add_result(results, "max_words", words <= max_words, f"{words} words > max {max_words}" if words > max_words else "")

    if "max_sentences" in checks:
        max_sentences = checks["max_sentences"]
    elif "nba_list" in input_data:
        max_sentences = max(2, len(effective_actions) + 1)
    else:
        max_sentences = 1 if primary_action.get("is_multitask") and not primary_action.get("is_second_response") else 2
    sentences = count_sentences(prediction)
    add_result(results, "max_sentences", sentences <= max_sentences, f"{sentences} sentences > max {max_sentences}" if sentences > max_sentences else "")

    if "max_questions" in checks:
        questions = count_questions(prediction)
        max_questions = checks["max_questions"]
        add_result(results, "max_questions", questions <= max_questions, f"{questions} questions > max {max_questions}" if questions > max_questions else "")

    if checks.get("must_be_question") is True:
        add_result(results, "must_be_question", is_question(prediction), "Response should be a question.")

    if checks.get("must_not_be_question") is True:
        add_result(results, "must_not_be_question", not is_question(prediction), "Response should not be a question.")

    request_actions = [action for action in effective_actions if action.get("nba") == "request_slot"]
    if checks.get("request_slot_focus") is True or request_actions:
        for action in request_actions:
            passed, message = check_request_slot_focus(prediction, action.get("slot"))
            add_result(results, "request_slot_focus", passed, message)

    if checks.get("must_mention_options") is True:
        all_options = []
        for action in effective_actions:
            all_options.extend(action.get("options", []))
        passed, message = check_options(prediction, all_options)
        add_result(results, "must_mention_options", passed, message)

    if checks.get("must_contain"):
        passed, message = check_must_contain(prediction, checks["must_contain"])
        add_result(results, "must_contain", passed, message)

    if checks.get("must_contain_any"):
        passed, message = check_must_contain_any(prediction, checks["must_contain_any"])
        add_result(results, "must_contain_any", passed, message)

    if checks.get("must_not_contain"):
        passed, message = check_must_not_contain(prediction, checks["must_not_contain"])
        add_result(results, "must_not_contain", passed, message)

    if checks.get("no_false_promise", True):
        for action in effective_actions:
            passed, message = check_false_promise(prediction, action)
            add_result(results, "no_false_promise", passed, message)

    if checks.get("no_unexpected_money", True):
        passed, message = check_unexpected_money(prediction, sample)
        add_result(results, "no_unexpected_money", passed, message)

    if checks.get("no_unexpected_times", True):
        passed, message = check_unexpected_times(prediction, sample)
        add_result(results, "no_unexpected_times", passed, message)

    if checks.get("check_flags", True):
        if any(action.get("step_by_step_mode") for action in effective_actions):
            passed, message = check_flag_step_by_step(prediction)
            add_result(results, "flag_step_by_step", passed, message)
        if any(action.get("is_second_response") for action in effective_actions):
            passed, message = check_flag_second_response(prediction)
            add_result(results, "flag_second_response", passed, message)
        for action in effective_actions:
            if action.get("queue_recovery"):
                passed, message = check_flag_queue_recovery(prediction, action.get("recovered_intent"))
                add_result(results, "flag_queue_recovery", passed, message)

    hard_failures = [item for item in results if item["severity"] == "hard" and not item["passed"]]
    soft_failures = [item for item in results if item["severity"] == "soft" and not item["passed"]]

    if hard_failures:
        status = "failed"
    elif soft_failures:
        status = "manual_review"
    else:
        status = "passed"

    return {
        "status": status,
        "checks": results,
        "hard_failed_checks": hard_failures,
        "soft_failed_checks": soft_failures,
    }


def generate_single_prediction(nlg: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
    input_data = sample["input"]
    history = EvalHistory(input_data.get("history", []))
    text = nlg.predict(
        dm_action_data=input_data["dm_action"],
        dialogue_state=input_data["dialogue_state"],
        history=history,
    )
    return {"text": text, "responses": [text]}


def generate_multi_prediction(nlg: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
    input_data = sample["input"]
    nba_list = copy.deepcopy(input_data["nba_list"])
    ds_list = copy.deepcopy(input_data["dialogue_state_list"])
    active_segments = input_data.get("active_segments", [])
    global_history = EvalHistory(copy.deepcopy(input_data.get("history", [])))
    step_by_step_mode = bool(input_data.get("step_by_step_mode", False))

    final_responses = []
    nlg._apply_response_flags(nba_list, step_by_step_mode)

    for index, nba in enumerate(nba_list):
        if index > 0:
            nba["is_second_response"] = True
        temp_history = nlg._build_masked_history(global_history, active_segments, index, final_responses)
        response = nlg.predict(nba, ds_list[index], temp_history)
        final_responses.append(response)

    return {"text": " ".join(final_responses), "responses": final_responses}


def generate_prediction(nlg: Any, sample: Dict[str, Any]) -> Dict[str, Any]:
    input_data = sample["input"]
    if input_data.get("mode") == "multi_response" or "nba_list" in input_data:
        return generate_multi_prediction(nlg, sample)
    return generate_single_prediction(nlg, sample)


def compute_metrics(evaluations: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(evaluations)
    counts = {"passed": 0, "manual_review": 0, "failed": 0}
    for evaluation in evaluations:
        counts[evaluation["status"]] += 1

    accepted = counts["passed"] + counts["manual_review"]
    return {
        "total_samples": total,
        "main_metric": accepted / total if total else 0.0,
        "nlg_auto_acceptance_rate": accepted / total if total else 0.0,
        "passed_samples": counts["passed"],
        "manual_review_samples": counts["manual_review"],
        "failed_samples": counts["failed"],
    }


def build_error_report(prediction_records: List[Dict[str, Any]], evaluations: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    errors = []
    for prediction_record, evaluation, sample in zip(prediction_records, evaluations, samples):
        if evaluation["status"] != "failed":
            continue
        errors.append({
            "id": sample.get("id"),
            "input": sample.get("input"),
            "prediction": prediction_record.get("text", ""),
            "responses": prediction_record.get("responses", []),
            "hard_failed_checks": evaluation["hard_failed_checks"],
            "soft_failed_checks": evaluation["soft_failed_checks"],
        })
    return errors


def build_manual_review_report(prediction_records: List[Dict[str, Any]], evaluations: List[Dict[str, Any]], samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    report = []
    for prediction_record, evaluation, sample in zip(prediction_records, evaluations, samples):
        input_data = sample.get("input", {})
        report.append({
            "id": sample.get("id"),
            "automatic_status": evaluation["status"],
            "needs_manual_review": evaluation["status"] == "manual_review",
            "prediction": prediction_record.get("text", ""),
            "responses": prediction_record.get("responses", []),
            "dialogue_state": input_data.get("dialogue_state", input_data.get("dialogue_state_list", {})),
            "dm_action": input_data.get("dm_action", input_data.get("nba_list", {})),
            "hard_failed_checks": evaluation["hard_failed_checks"],
            "soft_failed_checks": evaluation["soft_failed_checks"],
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
    manual_review: bool = True,
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

    prediction_records = []
    evaluations = []
    eval_start = time.time()

    for batch_idx, _, batch_samples, batch_start in iter_batches(samples, batch_size, "Evaluating NLG"):
        for sample in batch_samples:
            if predictions_by_id is not None:
                prediction_record = predictions_by_id.get(str(sample.get("id")), {"text": "", "responses": []})
            else:
                prediction_record = generate_prediction(nlg, sample)
            prediction_records.append(prediction_record)
            evaluations.append(evaluate_prediction(prediction_record, sample))
        print_batch_done(batch_idx, total_batches, batch_start, eval_start, len(prediction_records), total_samples)

    metrics = compute_metrics(evaluations, samples)
    error_report = build_error_report(prediction_records, evaluations, samples)
    manual_review_report = build_manual_review_report(prediction_records, evaluations, samples)

    results = {
        "model": model_name,
        "predictions_path": str(predictions_path) if predictions_path else None,
        "ground_truth_path": str(ground_truth_path),
        "created_at": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "metrics": metrics,
    }

    prediction_output_records = [
        {
            "id": sample.get("id"),
            "prediction": prediction_record,
            "automatic_status": evaluation["status"],
        }
        for sample, prediction_record, evaluation in zip(samples, prediction_records, evaluations)
    ]

    save_json(results, paths["results"])
    save_json(error_report, paths["errors"])
    save_json(prediction_output_records, paths["predictions"])
    save_json(manual_review_report, paths["manual_review"])

    print_final_paths(paths, include_predictions=True, include_manual_review=True)
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
        manual_review=True,
    )
    print(json.dumps(output["results"]["metrics"], indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
