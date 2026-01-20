import json
import random

SLOTS_DATA = {
    "facility_open": ["swimming_pool", "gym", "spa", "lido", "reception"],
    "facility_price": ["swimming_pool", "gym", "spa", "courses"],
    "date": ["today", "tomorrow", "Monday", "2023-10-25", "next Friday"],
    "sub_type": ["single_entry", "10_entries", "monthly", "annual"],
    "user_cat": ["adult", "child", "student", "senior"],
    "course": ["aquagym", "hydrobike", "swimming_school", "neonatal"],
    "age": ["kids", "adults", "teens"],
    "level": ["beginner", "intermediate", "advanced"],
    "day": ["Monday", "Tuesday", "Friday"],
    "item_shop": ["goggles", "swimsuit", "towel", "slippers"],
    "color": ["red", "blue", "black"],
    "problem": ["cold shower", "broken locker", "dirty floor"],
    "topic": ["swimming cap", "medical certificate", "slippers"]
}

TEMPLATES = [
    # 1. ask_opening_hours
    ("ask_opening_hours", "When is the {facility_open} open?", {"facility_open": "facility_type"}),
    ("ask_opening_hours", "Is the {facility_open} open {date}?", {"facility_open": "facility_type", "date": "date"}),
    ("ask_opening_hours", "Opening hours for {date} please.", {"date": "date"}),
    
    # 2. ask_pricing
    ("ask_pricing", "How much is the {sub_type} for {facility_price}?", {"sub_type": "subscription_type", "facility_price": "facility_type"}),
    ("ask_pricing", "Price for {user_cat} {sub_type}?", {"user_cat": "user_category", "sub_type": "subscription_type"}),
    ("ask_pricing", "Do you have discounts for {user_cat}?", {"user_cat": "user_category"}),

    # 3. ask_rules
    ("ask_rules", "Do I need a {topic}?", {"topic": "topic"}),
    ("ask_rules", "Is the {topic} mandatory?", {"topic": "topic"}),

    # 4. book_course
    ("ask_pricing", "I want to sign up for {course}.", {"course": "facility_type"}), # Nota: a volte chiedere di iscriversi può essere confuso con info, ma qui forziamo book_course nei next templates
    ("book_course", "Book {course} for {age}.", {"course": "course_activity", "age": "target_age"}),
    ("book_course", "I want the {level} {course} course on {day}.", {"level": "level", "course": "course_activity", "day": "day_preference"}),
    ("book_course", "Sign me up for {course} {age} class.", {"course": "course_activity", "age": "target_age"}),

    # 5. buy_equipment
    ("buy_equipment", "I need to buy {color} {item_shop}.", {"color": "color", "item_shop": "item"}),
    ("buy_equipment", "Do you sell {item_shop}?", {"item_shop": "item"}),

    # 6. report_issue
    ("report_issue", "The {problem} is annoying.", {"problem": "problem_type"}),
    ("report_issue", "I want to report a {problem}.", {"problem": "problem_type"}),
    
    # 7. out_of_scope
    ("out_of_scope", "Can I order a pizza?", {}),
    ("out_of_scope", "What is the capital of Italy?", {}),
    ("out_of_scope", "I like football.", {})
]

def generate_dataset(num_samples=200):
    dataset = []
    
    for _ in range(num_samples):
        intent, text_template, slot_map = random.choice(TEMPLATES)
        
        if intent == "out_of_scope":
            dataset.append({
                "input": text_template,
                "expected_intent": intent,
                "expected_slots": {}
            })
            continue

        current_slots = {}
        filled_text = text_template
        
        for placeholder, schema_name in slot_map.items():
            val = random.choice(SLOTS_DATA[placeholder])
            filled_text = filled_text.replace(f"{{{placeholder}}}", val)
            current_slots[schema_name] = val
            
        dataset.append({
            "input": filled_text,
            "expected_intent": intent,
            "expected_slots": current_slots
        })
    
    unique_data = {v['input']: v for v in dataset}.values()
    
    return list(unique_data)

if __name__ == "__main__":
    data = generate_dataset(300)
    
    with open("nlu_test_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Generati {len(data)} esempi di test in 'nlu_test_data.json'.")