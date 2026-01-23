import json
from prompts import DM_NO_NEW_VALUES_PROMPT, DM_ERROR_PROMPT, DM_SUCCESS_PROMPT


class DM:
    def __init__(self, model, tokenizer, generate_fn):
        self.model = model
        self.tokenizer = tokenizer
        self.generate_fn = generate_fn

        # Dialogue Management internal state
        self.user_profile = {
            "name": None,
            "surname": None
        }

        self.active_task = {
            "intent": None,
            "slots": {},
            "slots_to_validate": [],
            "status": "idle"  # idle, filling, ready_to_confirm, confirmed
        }

    def update_internal_state(self, intent, slots, new_values):
        if intent == "out_of_scope":
            return

        # Update user profile if relevant slots are provided
        if intent == "user_identification":
            if slots.get("name"):
                self.user_profile["name"] = slots["name"]
            if slots.get("surname"):
                self.user_profile["surname"] = slots["surname"]
            new_values = self.active_task["slots_to_validate"]    # new_values "name" or "surname" are overwritten
            return

        # Update active task
        self.active_task["intent"] = intent
        self.active_task["slots"].update(slots)
        self.active_task["slots_to_validate"] = new_values
        if all(value is not None for value in self.active_task["slots"].values()):
            self.active_task["status"] = "ready_to_confirm"
        else:
            self.active_task["status"] = "filling"


    def prepare_db_query(self, dst_output):
        intent = dst_output["state"]["intent"]
        slots = dst_output["state"]["slots"]
        new_values = dst_output["report"]["new_values"]

        self.update_internal_state(intent, slots, new_values)

        if len(new_values) > 0:
            db_args = {
                "nba": "validate_data",
                "intent": intent,
                "slots": slots,
                "slots_to_validate": new_values,
                "active_task": self.active_task,
            }

            if self.user_profile["name"] or self.user_profile["surname"]:
                db_args["user"] = self.user_profile

            return db_args
        return None
    
    def make_dm_decision(self, dst_output, db_result=None):
        intent = dst_output["state"]["intent"]

        if db_result is not None:
            normalized_slots = db_result.get("slots", {})
            if normalized_slots:
                dst_output["state"]["slots"] = normalized_slots
                dst_output["report"]["new_values"] = []

        # Update internal state
        slots = dst_output["state"]["slots"]
        new_values = dst_output["report"]["new_values"]
        self.update_internal_state(intent, slots, new_values)

        # Inject user profile into dialogue state for DM decision
        dst_output["state"]["user"] = self.user_profile

        # Choose prompt
        if db_result is not None:
            # If db_result is None, then the slots have already been passed to the db and normalized, easy to check (not necessarily all slots filled):
            # {
            #   "state": {
            #       "intent": "book_course",
            #       "slots": {
            #           "day_preference": "Monday",
            #           "level": "beginner",
            #           "target_age": "null"
            #       },
            #       "user": {
            #           "name": "Alice",
            #           "surname": "Smith"
            #       }
            #   },
            #   "report": {
            #       "event_type": "intent_switch",
            #       "details": "Switched to book_course",
            #       "new_values": []
            #   }
            # }
            #
            # Possible "event_type" values:
            # - "no_change": same intent, no new slots or out_of_scope (single, twice)
            # - "intent_switch": changed intent, no new slots
            # - "correlated_intent_switch": changed intent, some new slots
            sys_prompt = DM_NO_NEW_VALUES_PROMPT
        else:
            # {
            #   "state": {
            #       "intent": "book_course",
            #       "slots": {
            #           "day_preference": "Monday",
            #           "level": "beginner",
            #           "target_age": "teens"
            #       },
            #       "user": {
            #           "name": "Alice",
            #           "surname": "Smith"
            #       }
            #   },
            #   "report": {
            #       "status": "success",
            #       "message": "Fullfilled: book_course",
            #       "matching_booking": { ... }
            #   }
            # }
            dst_output["report"] = {
                k: db_result[k]
                for k in ["status", "message", "matching_booking"]
                if k in db_result
            }

            # Special handling: if intent is "user_identification" but active task is something else, revert intent to active task becuase slots belong to that
            if dst_output["state"]["intent"] == "user_identification":
                if self.active_task["intent"] in ["book_course", "book_spa", "modify_course_booking", "modify_spa_booking"]:
                    dst_output["state"]["intent"] = self.active_task["intent"]

            if db_result["status"] == "error":
                sys_prompt = DM_ERROR_PROMPT
            else:
                sys_prompt = DM_SUCCESS_PROMPT

        system_msg = [{"role": "system", "content": sys_prompt}]
        dm_out = self.generate_fn(
            self.model,
            self.tokenizer,
            system_msg,
            dst_output
        )

        # Parsing JSON output
        try:
            json_str = dm_out.replace("```json", "").replace("```", "").strip()
            action_data = json.loads(json_str)
        except json.JSONDecodeError:
            action_data = {"nba": "error", "validation": {"required": False}}

        print(f"DEBUG DM Parsed Action Data: {action_data}")

        return action_data