import copy
from utils.mock_database import COURSE_SCHEDULE, SHOP_INVENTORY, normalize_date


class StateTracker:
    def __init__(self):
        # self.history = []
        self.current_state = {
            "intent": None,
            "slots": {}
        }

    def get_state(self):
        return self.current_state

    def merge_slots(self, new_intent, slot_name, new_slots, update_report):
        update_report["event_type"] = "intent_merge"
        update_report["details"] = f"Merged slot for intent {new_intent}"

        old_slots = self.current_state["slots"].copy()
        self.current_state["intent"] = new_intent
        self.current_state["slots"] = new_slots

        # detect changed (user-provided) slots
        for key, value in new_slots.items():
            if value is not None and value != "null" and value != old_slots.get(key):
                update_report["new_values"].append(key)    # it's newly provided

        # carry-over (NOT active)
        if self.current_state["slots"].get(slot_name) in [None, "null"]:
            self.current_state["slots"][slot_name] = old_slots.get(slot_name)

    def format_for_dm(self, update_report):
        return {
            "state": self.current_state,
            "report": update_report
        }

    def update(self, nlu_output):
        """
        Update the dialogue state based on NLU output.
        """
        new_intent = nlu_output.get("intent")
        new_slots = nlu_output.get("slots", {})

        update_report = {
            "event_type": "no_change",
            "details": "",
            "new_values": []
        }

        # Twice Out of Scope Handling
        if new_intent == "out_of_scope":
            if self.current_state["intent"] == "out_of_scope":
                print("[DST] Consecutive Out of Scope detected. No state update.")
                update_report["event_type"] = "no_change"
                update_report["details"] = "Consecutive out_of_scope intents."
                return self.format_for_dm(update_report)

            print("[DST] Out of Scope detected. No state update.")
            update_report["event_type"] = "no_change"
            update_report["details"] = "out_of_scope intent."
            return self.format_for_dm(update_report)
        
        # SPECIAL INTENT HANDLING
        if new_intent != self.current_state["intent"]:

            # Scenario: Switching between information requests (Pricing/Hours) while keeping the facility context.
            if new_intent in ["ask_opening_hours", "ask_pricing"]:
                if self.current_state["intent"] in ["ask_opening_hours", "ask_pricing"]:

                    print(f"[DST] Same Info intent detected: {new_intent}. Merging slot [facility_type].")
                    self.merge_slots(new_intent, "facility_type", new_slots, update_report)

                    return self.format_for_dm(update_report)

            # Scenario: User reports a lost item, then decides to buy a new one.
            # We carry over the 'item' slot so they don't have to specify what they want to buy again.
            if new_intent == "buy_equipment":
                if self.current_state["intent"] == "report_lost_item":

                    print(f"[DST] Switching from report_lost_item to buy_equipment. Merging slot [item].")
                    self.merge_slots(new_intent, "item", new_slots, update_report)

                    return self.format_for_dm(update_report)

            # Scenario: Modification of booking suddenly after booking it (or trying to).
            # If the user switches from a booking intent to modify_booking, we assume they want to modify
            # the booking they were just talking about.
            if new_intent == "modify_booking":      # TODO: refine modification on specific booking type
                if self.current_state["intent"] in ["book_course", "book_wellness"]:
                    print(
                        f"[DST] Switching from {self.current_state['intent']} to modify_booking. Merging booking slots.")

                    update_report["event_type"] = "intent_merge"
                    update_report["details"] = f"Merged slot for intent {new_intent}"

                    previous_time = None
                    if self.current_state["intent"] == "book_course":
                        previously_book_type = self.current_state["slots"].get("course_activity")
                        previous_day = self.current_state["slots"].get("day_preference")
                    else:
                        previously_book_type = "spa"
                        previous_day = self.current_state["slots"].get("date")
                        previous_time = self.current_state["slots"].get("time")

                    self.current_state["intent"] = new_intent
                    self.current_state["slots"] = new_slots

                    # booking_type
                    if self.current_state["slots"].get("booking_type") in [None, "null"]:
                        self.current_state["slots"]["booking_type"] = previously_book_type
                    else:
                        update_report["new_values"].append("booking_type")      # it's newly provided

                    # old_date
                    if self.current_state["slots"].get("old_date") in [None, "null"]:
                        self.current_state["slots"]["old_date"] = previous_day

                    # old_time (only for wellness)
                    if previous_time:
                        if self.current_state["slots"].get("old_time") in [None, "null"]:
                            self.current_state["slots"]["old_time"] = previous_time

                    return self.format_for_dm(update_report)

            # Classic Intent Switch
            print(f"[DST] Change Intent: {self.current_state['intent']} -> {new_intent}.")
            update_report["event_type"] = "intent_switch"
            update_report["details"] = f"Switched to {new_intent}"

            old_slots = self.current_state["slots"].copy()
            for key, value in new_slots.items():
                if value is not None and value != "null" and value != old_slots.get(key):
                    update_report["new_values"].append(key)     # it's newly provided

            self.current_state["intent"] = new_intent
            self.current_state["slots"] = new_slots
            return self.format_for_dm(update_report)

        # Scenario same intent: Filling / Updating Slots
        for key, value in new_slots.items():
            if value is None or value == "null":
                continue    # TODO: if user explicitly says remove the value, we should handle it

            old_val = self.current_state["slots"].get(key)

            if old_val == "null" or old_val != value:
                update_report["new_values"].append(key)    # it's newly provided
                self.current_state["slots"][key] = value

        if update_report["new_values"]:
            update_report["event_type"] = "slot_update"
            update_report["details"] = "Updated slots"

        # self.history.append(copy.deepcopy(self.current_state))

        return self.format_for_dm(update_report)

    def _enforce_course_constraints(self, updated_keys):
        """
        Regola: Se Corso e Giorno sono incompatibili, rimuovi quello più vecchio.
        """
        slots = self.current_state["slots"]
        course = slots.get("course_activity")
        day_raw = slots.get("day_preference")

        if course and day_raw:
            # Day normalization (e.g tomorrow -> Friday)
            _, day_name = normalize_date(day_raw)

            if day_name:
                valid_days = COURSE_SCHEDULE.get(course, [])

                # IF CONFLICT (The day is not valid for the course)
                if day_name not in valid_days:
                    print(f"[DST] Conflict Detected! {course} is not available on {day_name}.")

                    # Resolution Logic: The newly entered information wins
                    if "course_activity" in updated_keys:
                        # The user just changed the course -> The old day is not valid
                        print(f"[DST] Removing invalid day: {day_raw}")
                        slots["day_preference"] = None
                        return f"Removed invalid day {day_raw} for course {course}"

                    elif "day_preference" in updated_keys:
                        # The user just changed the day -> The old course is not valid
                        print(f"[DST] Removing invalid course: {course}")
                        slots["course_activity"] = None
                        return f"Removed invalid course {course} for day {day_raw}"
            else:
                # If the date is not parsable or is in the past, you might decide to remove it
                # But let's leave it to the DB to give the specific error about the date
                return None

    def _enforce_shop_constraints(self, updated_keys):
        """
        Rule: If the item changes, check if Color or Size are still valid.
        """
        slots = self.current_state["slots"]
        item = slots.get("item")
        color = slots.get("color")
        size = slots.get("size")

        if item and item in SHOP_INVENTORY:
            details = SHOP_INVENTORY[item]

            # Check Colore
            if color and "colors" in details:
                if color not in details["colors"]:
                    if "item" in updated_keys:
                        print(f"[DST] Rimuovo colore {color} (non esiste per {item})")
                        slots["color"] = None
                        return f"Removed invalid color {color} for item {item}"
                    elif "color" in updated_keys:
                        print(f"[DST] Rimuovo item {item} (non esiste in {color})")
                        slots["item"] = None
                        return f"Removed invalid item {item} for color {color}"

            # Check Taglia
            if size and "sizes" in details:
                if size not in details["sizes"]:
                    if "item" in updated_keys:
                        print(f"[DST] Rimuovo taglia {size} (non esiste per {item})")
                        slots["size"] = None
                        return f"Removed invalid size {size} for item {item}"
                    elif "size" in updated_keys:
                        print(f"[DST] Rimuovo item {item} (non esiste in taglia {size})")
                        slots["item"] = None
                        return f"Removed invalid item {item} for size {size}"
        return None
