import json
from transformers import AutoTokenizer
from sklearn.metrics import accuracy_score, classification_report

from components.NLU import NLU
from utils.models import MODELS

def evaluate():
    try:
        with open("nlu_test_data.json", "r", encoding="utf-8") as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print("ERROR: Run 'generate_dataset.py' first to create the test data.")
        return

    print(f"Loaded {len(test_data)} test cases. Initializing model...")

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

    print("\n--- Starting NLU Evaluation ---\n")
    
    for i, sample in enumerate(test_data):
        user_input = sample["input"]
        exp_intent = sample["expected_intent"]
        exp_slots = sample["expected_slots"]

        # NLU Prediction
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

        if (i+1) % 20 == 0:
            print(f"Processed {i+1}/{len(test_data)}...")

    print("\n" + "="*40)
    print("EVALUATION RESULTS")
    print("="*40)

    acc = accuracy_score(y_true_intents, y_pred_intents)
    print(f"\nINTENT ACCURACY: {acc:.2%}")
    
    # Print detailed class report if there are errors
    if acc < 1.0:
        print("\nClassification Report (Intents):")
        print(classification_report(y_true_intents, y_pred_intents, zero_division=0))

    if total_slots > 0:
        slot_acc = correct_slots / total_slots
        print(f"SLOT ACCURACY (Micro): {slot_acc:.2%} ({correct_slots}/{total_slots})")
    else:
        print("No slots to evaluate.")

    if len(slot_errors) > 0:
        print("\n--- Slot Error Examples (First 5) ---")
        for err in slot_errors[:5]:
            print(f"Input: {err['input']}")
            print(f"   Slot '{err['slot']}': Expected '{err['expected']}' -> Got '{err['predicted']}'")

if __name__ == "__main__":
    evaluate()