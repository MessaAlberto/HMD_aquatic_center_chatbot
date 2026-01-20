import copy
from utils.mock_database import COURSE_SCHEDULE, SHOP_INVENTORY, normalize_date


class StateTracker:
    def __init__(self):
        self.history = []
        self.current_state = {
            "intent": None,
            "slots": {}
        }

    def get_state(self):
        return self.current_state

    def update(self, nlu_output):
        """
        Update the dialogue state based on NLU output.
        """
        new_intent = nlu_output.get("intent")
        new_slots = nlu_output.get("slots", {})

        update_report = {
            "event_type": "no_change",
            "details": []
        }

        # CHANGE INTENT (Intelligent Reset)
        if new_intent and new_intent != "out_of_scope":
            if new_intent != self.current_state["intent"]:
                print(f"[DST] Change Intent: {self.current_state['intent']} -> {new_intent}. Reset Slots.")
                update_report["event_type"] = "intent_switch"
                update_report["details"].append(f"Switched to {new_intent}")
                self.current_state["intent"] = new_intent
                self.current_state["slots"] = {}

        # MERGE SLOTS (Overwrite)
        # Keep track of which slots were updated this turn
        updated_keys = []
        for key, value in new_slots.items():
            if value is not None:
                old_val = self.current_state["slots"].get(key)
                
                # Se c'era già un valore diverso -> È una CORREZIONE
                if old_val and old_val != value:
                    if update_report["event_type"] != "intent_switch":
                        update_report["event_type"] = "slot_correction"
                    update_report["details"].append(f"Corrected {key}: {old_val} -> {value}")
                
                # Se era vuoto -> È un FILLING normale
                elif not old_val:
                    if update_report["event_type"] == "no_change":
                        update_report["event_type"] = "slot_filling"

                self.current_state["slots"][key] = value
                updated_keys.append(key)

        # DIPENDENCE MANAGER
        conflict_msg = self._enforce_course_constraints(updated_keys)

        if conflict_msg:
            update_report["event_type"] = "slot_conflict"
            update_report["details"].append(conflict_msg)

        conflict_msg = self._enforce_shop_constraints(updated_keys)

        if conflict_msg:
            update_report["event_type"] = "slot_conflict"
            update_report["details"].append(conflict_msg)

        self.history.append(copy.deepcopy(self.current_state))

        return self.current_state

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
