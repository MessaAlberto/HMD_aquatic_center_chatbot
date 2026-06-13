from typing import Any

from database.mock_database import MockDatabase, reset_users_db


class DBController:
    """Routes resolved dialogue states to the corresponding database operation."""

    def __init__(self, dst) -> None:
        self.db = MockDatabase(dst)

        self.intent_to_method = {
            "ask_opening_hours": self.db.get_opening_hours,
            "ask_pricing": self.db.get_pricing,
            "ask_rules": self.db.get_rules,
            "book_course": self.db.get_book_course,
            "book_spa": self.db.get_book_spa,
            "modify_booked_course": self.db.get_modify_booked_course,
            "modify_booked_spa": self.db.get_modify_booked_spa,
            "cancel_booked_course": self.db.get_cancel_booked_course,
            "cancel_booked_spa": self.db.get_cancel_booked_spa,
            "buy_equipment": self.db.get_buy_equipment,
            "report_lost_item": self.db.get_report_lost_item,
            "user_identification": self.db.get_user_identification,
            "greeting_closing": self.db.get_greeting_closing,
            "out_of_scope": self.db.get_out_of_scope,
        }

        self.needs_user_profile = {
            "book_course", "book_spa", "modify_booked_course", "modify_booked_spa",
            "cancel_booked_course", "cancel_booked_spa", "report_lost_item",
        }

    def reset_database(self) -> None:
        reset_users_db()

    def resolve_state(self, dialogue_state: dict[str, Any], user_profile: dict[str, Any], lenient: bool = False, target_dst=None) -> dict[str, Any] | None:
        """Resolve a dialogue state through the database and clean invalid slots when needed."""
        intent = dialogue_state.get("intent")
        slots = dialogue_state.get("slots", {})
        db_method = self.intent_to_method.get(intent)

        if not db_method:
            return {"status": "UNKNOWN_INTENT"}

        original_dst = self.db.dst

        try:
            if target_dst is not None:
                self.db.dst = target_dst

            if intent in self.needs_user_profile:
                db_result = db_method(**slots, user=user_profile, lenient=lenient)
            else:
                db_result = db_method(**slots, lenient=lenient)

            if db_result and db_result.get("status") == "INVALID_VALUE":
                violating_slot = db_result.get("violating_slot")
                if violating_slot:
                    self.db.dst.clean_invalid_slots(violating_slot)

            return db_result
        finally:
            self.db.dst = original_dst
