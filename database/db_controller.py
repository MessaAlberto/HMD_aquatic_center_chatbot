from typing import Dict, Any, Optional
from database.mock_database import MockDatabase, reset_users_db


class DBController:
    def __init__(self, dst):
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
            "out_of_scope": self.db.get_out_of_scope
        }

        self.needs_user_profile = {
            "book_course", "book_spa", "modify_booked_course",
            "modify_booked_spa", "cancel_booked_course", "cancel_booked_spa",
            "report_lost_item"
        }

    def reset_database(self) -> None:
        reset_users_db()

    def resolve_state(self, dialogue_state: Dict[str, Any], user_profile: Dict[str, Any], lenient: bool=False, target_dst=None) -> Optional[Dict[str, Any]]:
        intent = dialogue_state.get("intent")
        slots = dialogue_state.get("slots", {})

        original_dst = self.db.dst
        if target_dst:
            self.db.dst = target_dst

        db_method = self.intent_to_method.get(intent)

        if not db_method:
            if target_dst:
                self.db.dst = original_dst # Restore
            return {
                "status": "UNKNOWN_INTENT"
            }
        
        if intent in self.needs_user_profile:
            # Corretto: user=user_profile
            db_result = db_method(**slots, user=user_profile, lenient=lenient)
        else:
            db_result = db_method(**slots, lenient=lenient)

        # ====================================================
        # PULIZIA CENTRALIZZATA DEGLI SLOT INVALIDI
        # ====================================================
        if db_result and db_result.get("status") == "INVALID_VALUE":
            violating_slot = db_result.get("violating_slot")
            if violating_slot:
                self.db.dst.clean_invalid_slots(violating_slot)

        if target_dst:
            self.db.dst = original_dst # Restore
        return db_result
