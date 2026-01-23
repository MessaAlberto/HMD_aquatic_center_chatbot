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

    def corr_intent_switch(self, new_intent, slot_name, new_slots, update_report):
        update_report["event_type"] = "correlated_intent_switch"
        update_report["details"] = f"Changed intent to {new_intent} talking about same topic: {slot_name}"

        old_slots = self.current_state["slots"].copy()
        self.current_state["intent"] = new_intent
        self.current_state["slots"] = new_slots

        # detect changed (user-provided) slots
        for key, value in new_slots.items():
            if value is not None and value != old_slots.get(key):
                update_report["new_values"].append(key)    # it's newly provided

        # carry-over (NOT active)
        if self.current_state["slots"].get(slot_name) is None:
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
                    self.corr_intent_switch(new_intent, "facility_type", new_slots, update_report)

                    return self.format_for_dm(update_report)

            # Scenario: User reports a lost item, then decides to buy a new one.
            # We carry over the 'item' slot so they don't have to specify what they want to buy again.
            if new_intent == "buy_equipment":
                if self.current_state["intent"] == "report_lost_item":

                    print(f"[DST] Switching from report_lost_item to buy_equipment. Merging slot [item].")
                    self.corr_intent_switch(new_intent, "item", new_slots, update_report)

                    return self.format_for_dm(update_report)

            # Classic Intent Switch
            print(f"[DST] Change Intent: {self.current_state['intent']} -> {new_intent}.")
            update_report["event_type"] = "intent_switch"
            update_report["details"] = f"Switched to {new_intent}"

            old_slots = self.current_state["slots"].copy()
            for key, value in new_slots.items():
                if value is not None and value != old_slots.get(key):
                    update_report["new_values"].append(key)     # it's newly provided

            self.current_state["intent"] = new_intent
            self.current_state["slots"] = new_slots
            return self.format_for_dm(update_report)

        # Scenario same intent: Filling / Updating Slots
        for key, value in new_slots.items():
            if value is None:
                continue    # TODO: if user explicitly says remove the value, we should handle it

            old_val = self.current_state["slots"].get(key)

            if old_val != value:
                update_report["new_values"].append(key)    # it's newly provided
                self.current_state["slots"][key] = value

        if update_report["new_values"]:
            update_report["event_type"] = "slot_update"
            update_report["details"] = "Updated slots"
        else:
            update_report["event_type"] = "no_change"
            update_report["details"] = "No new slot values provided."

        # self.history.append(copy.deepcopy(self.current_state))

        return self.format_for_dm(update_report)
