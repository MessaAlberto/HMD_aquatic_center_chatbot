from datetime import datetime, timedelta

# ===================
#    STATIC DATA
# ===================

OPENING_HOURS = {
    "swimming_pool": "Mon-Fri: 06:00-22:00, Sat: 08:00-20:00, Sun: 09:00-14:00",
    "gym": "Mon-Fri: 06:00-23:00, Sat-Sun: 08:00-20:00",
    "spa": "Mon-Sun: 10:00-21:00 (Reservation required)",
    "lido": "Mon-Sun: 09:00-19:00 (Summer season only)",
    "reception": "Mon-Sun: 08:00-20:00"
}

PRICING = {
    "swimming_pool": {
        "single_entry": 8.50,
        "10_entries": 75.00,
        "monthly": 60.00,
        "annual": 550.00
    },
    "gym": {
        "single_entry": 10.00,
        "10_entries": 90.00,
        "monthly": 45.00,
        "annual": 450.00
    },
    "spa": {
        "single_entry": 25.00,
        "10_entries": 220.00
    },
    "courses": {
        "single_entry": 12.00,
        "monthly": 80.00,
        "annual": 700.00
    },
    "lido": {
        "single_entry": 10.00,
        "monthly": 70.00,
        "seasonal": 200.00
    }
}

DISCOUNTS = {
    "child": 0.50,   # 50% discount
    "student": 0.80,  # 20% discount (pay 80%)
    "senior": 0.70,  # 30% discount
    "adult": 1.0     # Full price
}

RULES = {
    "swimming cap": "Mandatory in the main pool at all times.",
    "medical certificate": "Required for annual subscriptions and competitive courses.",
    "slippers": "Mandatory in the changing rooms and pool deck.",
    "towel": "Highly recommended for gym and required for SPA.",
    "padlock": "Required for lockers. You can bring your own or buy one at the shop."
}

COURSE_SCHEDULE = {
    "aquagym": ["Monday", "Wednesday", "Friday"],
    "hydrobike": ["Tuesday", "Thursday"],
    "swimming_school": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "neonatal": ["Saturday", "Sunday"]
}

SHOP_INVENTORY = {
    "goggles": {"price": 15.00, "colors": ["blue", "black", "red", "clear"], "brand": "Speedo"},
    "swimsuit": {"price": 35.00, "sizes": ["S", "M", "L", "XL"], "brand": "Arena"},
    "towel": {"price": 12.00, "colors": ["white", "blue"], "brand": "Decathlon"},
    "slippers": {"price": 10.00, "sizes": ["S", "M", "L", "XL"], "brand": "Adidas"},
    "cap": {"price": 5.00, "colors": ["red", "blue", "black", "yellow"], "brand": "Arena"}
}

# Subscription
USERS_DB = {
    "12345": {"name": "Mario Rossi", "status": "Active", "expiry": "2024-12-31", "type": "Gym Annual"},
    "67890": {"name": "Luigi Verdi", "status": "Expired", "expiry": "2023-01-01", "type": "Pool Monthly"}
}

# ===================
#  VALIDATION LISTS (Used by State Tracker for immediate feedback)
# ===================

VALID_DATA = {
    "facility_type": list(OPENING_HOURS.keys()),
    "course_activity": list(COURSE_SCHEDULE.keys()),
    "user_category": list(DISCOUNTS.keys()),
    "subscription_type": ["single_entry", "10_entries", "monthly", "annual"],
    "item": list(SHOP_INVENTORY.keys())
}

# ===================
#   LOGIC FUNCTIONS
# ===================

class MockDatabase:
    def __init__(self):
        pass

    def validate_slot_value(slot_name, value):
        """
        Checks if a slot value exists in the allowed lists.
        Used by the Middleware/State Tracker before calling the DM.
        """
        if not value:
            return True  # Null is handled by DM as 'missing slot', not 'invalid value'

        val_norm = str(value).lower().replace(" ", "_")

        # Map NLU slot names to Validation keys if necessary
        key_map = {
            "facility_type": "facility_type",
            "course": "course_activity",
            "course_activity": "course_activity",
            "user_cat": "user_category",
            "user_category": "user_category",
            "sub_type": "subscription_type",
            "subscription_type": "subscription_type",
            "item": "item"
        }

        if slot_name in key_map:
            check_key = key_map[slot_name]
            if check_key in VALID_DATA:
                # Flexible check (e.g., "pool" in "swimming_pool")
                return any(val_norm in valid_item or valid_item in val_norm for valid_item in VALID_DATA[check_key])

        return True


    def normalize_date(date_str):
        """
        Converts user-provided date strings into datetime.date objects.
        Handles relative terms (today, tomorrow), weekdays, and ISO dates.
        """
        if not date_str:
            return None, None

        today = datetime.now().date()
        date_str = date_str.lower().strip()

        parsed_date = None

        # Handle relative keywords
        if date_str in ["today", "oggi"]:
            parsed_date = today
        elif date_str in ["tomorrow", "domani"]:
            parsed_date = today + timedelta(days=1)
        elif date_str in ["yesterday", "ieri"]:
            parsed_date = today - timedelta(days=1)

        # Handle Weekdays (e.g., "Monday" or "next Friday")
        # If the user says just "Monday", assume it's the "next Monday"
        else:
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            # Clean string (e.g., "next monday" -> "monday")
            clean_day = date_str.replace("next ", "").replace("this ", "").strip()

            if clean_day in weekdays:
                target_idx = weekdays.index(clean_day)
                current_idx = today.weekday()  # 0=Monday, 6=Sunday

                # Calculate how many days ahead
                days_ahead = target_idx - current_idx
                if days_ahead <= 0:  # If it's today or past, go to next week
                    days_ahead += 7

                parsed_date = today + timedelta(days=days_ahead)

        # Handle ISO Dates (YYYY-MM-DD) if the LLM extracted them this way
        if not parsed_date:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass  # Not a valid ISO date

        if parsed_date:
            # Returns the date object and the day name (e.g., "Monday")
            return parsed_date, parsed_date.strftime("%A")

        return None, None


    def query_database(intent, slots):
        """
        Main entry point for the DM.
        Returns a dict with 'status' (success/error) and a 'message' or 'data'.
        """
        print(f"[DB] Querying for intent: {intent} | Slots: {slots}")

        # 1. ASK OPENING HOURS
        if intent == "ask_opening_hours":
            facility = slots.get("facility_type", "reception").lower().replace(" ", "_")
            if facility in OPENING_HOURS:
                return {"status": "success", "message": f"The {facility.replace('_', ' ')} hours are: {OPENING_HOURS[facility]}"}
            return {"status": "error", "message": f"Facility '{facility}' not found."}

        # 2. ASK PRICING
        elif intent == "ask_pricing":
            facility = slots.get("facility_type", "swimming_pool").lower().replace(" ", "_")
            sub_type = slots.get("subscription_type", "single_entry").lower()
            user_cat = slots.get("user_category", "adult").lower()

            if facility not in PRICING:
                return {"status": "error", "message": f"No pricing info for {facility}."}

            base_price = PRICING[facility].get(sub_type)
            if base_price is None:
                return {"status": "error", "message": f"Subscription '{sub_type}' not available for {facility}."}

            # Calculate discount
            multiplier = DISCOUNTS.get(user_cat, 1.0)
            final_price = base_price * multiplier

            return {
                "status": "success",
                "message": f"The price for {sub_type.replace('_', ' ')} ({facility}) for a {user_cat} is €{final_price:.2f}."
            }

        # 3. ASK RULES
        elif intent == "ask_rules":
            topic = slots.get("topic", "").lower()
            # Fuzzy search in keys
            for key, rule in RULES.items():
                if key in topic or topic in key:
                    return {"status": "success", "message": rule}
            return {"status": "success", "message": "No specific rules found for this topic. General rule: be polite and shower before entering."}

        # 4. BOOK COURSE (Critical Validation Logic)
        elif intent == "book_course":
            course = slots.get("course_activity", "").lower()
            date_input = slots.get("day_preference", "")

            # Check course existence
            if course not in COURSE_SCHEDULE:
                return {"status": "error", "message": f"Course '{course}' does not exist."}

            allowed_days = COURSE_SCHEDULE[course]  # Es. ["Monday", "Wednesday"]

            # Normalize date
            if date_input:
                real_date, day_name = normalize_date(date_input)

                if not real_date:
                    # If we couldn't understand the date (e.g., "afternoon")
                    return {"status": "error", "message": f"I didn't understand the date '{date_input}'. Please specify a day (e.g., 'Monday', 'Tomorrow')."}

                # Business Logic Check (Temporal Logic)
                if real_date < datetime.now().date():
                    return {"status": "error", "message": f"You cannot book for the past ({real_date})."}

                # Check course availability for that day
                if day_name not in allowed_days:
                    return {
                        "status": "error",
                        "message": f"The '{course}' course is held on {', '.join(allowed_days)}. It is NOT available on {day_name} ({real_date})."
                    }

                # SUCCESS
                return {"status": "success", "message": f"Booking confirmed for {course} on {day_name}, {real_date}. See you there!"}

            else:
                # If the user did not provide a date (the DM should have asked for it, but just in case)
                return {"status": "error", "message": f"Please specify a day for the {course} course."}

        # 5. BOOK WELLNESS
        elif intent == "book_wellness":
            # Mock logic: assume everything is free except Sundays
            day = slots.get("date", "").lower()
            if "sunday" in day:
                return {"status": "error", "message": "Sorry, the SPA is fully booked on Sundays."}
            return {"status": "success", "message": "SPA Booking confirmed."}

        # 6. BUY EQUIPMENT
        elif intent == "buy_equipment":
            item = slots.get("item", "").lower()
            color = slots.get("color", "").lower()
            size = slots.get("size", "").upper()

            if item not in SHOP_INVENTORY:
                return {"status": "error", "message": f"Sorry, we don't sell '{item}'."}

            product_data = SHOP_INVENTORY[item]

            # Check constraints if provided
            if color and "colors" in product_data and color not in product_data["colors"]:
                return {"status": "error", "message": f"We only have {item} in {product_data['colors']}, not {color}."}

            if size and "sizes" in product_data and size not in product_data["sizes"]:
                return {"status": "error", "message": f"Available sizes for {item}: {product_data['sizes']}."}

            return {"status": "success", "message": f"Item '{item}' available for €{product_data['price']}. You can pick it up at the counter."}

        # 7. MODIFY BOOKING (Mock)
        elif intent == "modify_booking":
            return {"status": "success", "message": "Booking modified successfully."}

        # 8. CHECK SUBSCRIPTION
        elif intent == "check_subscription":
            card_id = slots.get("card_id")
            if card_id in USERS_DB:
                user = USERS_DB[card_id]
                return {"status": "success", "message": f"Subscription for {user['name']}: {user['type']} (Expires: {user['expiry']}). Status: {user['status']}."}
            return {"status": "error", "message": "Card ID not found in our database."}

        # 9. REPORT LOST ITEM
        elif intent == "report_lost_item":
            # Just logging
            return {"status": "success", "message": "Report logged. We will contact you if found."}

        # 10. REPORT ISSUE
        elif intent == "report_issue":
            # Just logging
            return {"status": "success", "message": "Issue reported to maintenance. Thank you."}

        # Default
        return {"status": "success", "message": "Operation completed."}
