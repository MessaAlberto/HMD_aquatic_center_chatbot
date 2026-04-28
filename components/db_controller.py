from typing import Dict, Any, Optional
from components.mock_database import MockDatabase


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
            "buy_equipment": self.db.get_buy_equipment,
            "report_lost_item": self.db.get_report_lost_item
        }

        self.needs_user_profile = {
            "book_course", "book_spa", "modify_booked_course",
            "modify_booked_spa", "report_lost_item"
        }

    def resolve_state(self, dialogue_state: Dict[str, Any], user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        intent = dialogue_state.get("intent")
        slots = dialogue_state.get("slots", {})

        db_method = self.intent_to_method.get(intent)

        if not db_method:
            return {
                "status": "UNKNOWN_INTENT"
            }
        
        if intent in self.needs_user_profile:
            # Corretto: user=user_profile
            db_result = db_method(**slots, user=user_profile)
        else:
            db_result = db_method(**slots)

        # ====================================================
        # PULIZIA CENTRALIZZATA DEGLI SLOT INVALIDI
        # ====================================================
        if db_result and db_result.get("status") == "INVALID_VALUE":
            violating_slot = db_result.get("violating_slot")
            if violating_slot:
                self.db.dst.clean_invalid_slots(violating_slot)
                
        return db_result
