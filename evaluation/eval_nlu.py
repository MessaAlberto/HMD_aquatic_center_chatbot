from utils.models import MODELS
from components.NLU import NLU
import json
import sys
import os
from transformers import AutoTokenizer
from sklearn.metrics import accuracy_score, classification_report

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)


def evaluate():
    result_dir = os.path.join(current_dir, "result")
    os.makedirs(result_dir, exist_ok=True)

    result_file = os.path.join(result_dir, "nlu_eval.txt")
    log_lines = []

    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    gt_path = os.path.join(current_dir, "ground_truth_data", "nlu_test_data.json")

    try:
        with open(gt_path, "r", encoding="utf-8") as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print("ERROR: ground_truth_data/nlu_test_data.json not found.")
        return

    log(f"Loaded {len(test_data)} test cases. Initializing model...")

    model_name, InitModel, generate_response = MODELS["qwen3"]
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = InitModel(
        model_name,
        dtype="auto",
        device_map="cuda:0"
    )

    nlu_component = NLU(model, tokenizer, generate_response)

    y_true_intents = []
    y_pred_intents = []

    total_slots = 0
    correct_slots = 0
    slot_errors = []

    log("\n--- Starting NLU Evaluation ---\n")

    for i, sample in enumerate(test_data):
        user_input = sample["input"]
        exp_intent = sample["expected_intent"]
        exp_slots = sample["expected_slots"]

        pred_output = nlu_component.predict(user_input)

        pred_intent = pred_output.get("intent", "out_of_scope")
        pred_slots = pred_output.get("slots", {})

        y_true_intents.append(exp_intent)
        y_pred_intents.append(pred_intent)

        for key, val in exp_slots.items():
            total_slots += 1
            if str(pred_slots.get(key, "")).lower() == str(val).lower():
                correct_slots += 1
            else:
                slot_errors.append({
                    "input": user_input,
                    "slot": key,
                    "expected": val,
                    "predicted": pred_slots.get(key, "MISSING")
                })

        if (i + 1) % 20 == 0:
            log(f"Processed {i + 1}/{len(test_data)}...")

    log("\n" + "=" * 40)
    log("EVALUATION RESULTS")
    log("=" * 40)

    acc = accuracy_score(y_true_intents, y_pred_intents)
    log(f"\nINTENT ACCURACY: {acc:.2%}")

    if acc < 1.0:
        log("\nClassification Report (Intents):")
        log(classification_report(y_true_intents, y_pred_intents, zero_division=0))

    if total_slots > 0:
        slot_acc = correct_slots / total_slots
        log(f"SLOT ACCURACY (Micro): {slot_acc:.2%} ({correct_slots}/{total_slots})")
    else:
        log("No slots to evaluate.")

    if slot_errors:
        log("\n--- Slot Error Examples ---")
        for err in slot_errors:
            log(f"Input: {err['input']}")
            log(f"   Slot '{err['slot']}': Expected '{err['expected']}' -> Got '{err['predicted']}'")

    with open(result_file, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"\nResults saved to: {result_file}")


if __name__ == "__main__":
    evaluate()
