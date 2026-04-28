import re
import difflib
from typing import Any, Dict, Optional
import dateparser
from datetime import datetime, timedelta

VALID_FACILITIES = ["swimming_pool", "gym", "spa", "lido", "reception", "course"]
VALID_SUB_TYPES = ["day_pass", "monthly_pass", "annual_pass", "10_entry_pass"]
VALID_USER_CATEGORIES = ["adult", "child", "senior", "student"]
VALID_TOPICS = ["swimming_pool", "gym", "spa", "lido", "changing_room"]
VALID_COURSES = ["aquagym", "hydrobike", "swimming_school", "newborn_swimming"]
VALID_TARGET_AGES = ["children", "teens", "adults"]
VALID_LEVELS = ["beginner", "intermediate", "advanced"]
VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
VALID_EQUIPMENT = ["swimming_cap", "goggles", "towel", "slippers", "swimsuit"]
VALID_CONFIRMATION = ["agree", "deny"]

INTENT_SCHEMAS = {
    "ask_opening_hours": ["facility_type", "date", "time"],
    "ask_pricing": ["facility_type", "sub_type", "user_category"],
    "ask_rules": ["topic", "specific_inquiry"],
    "book_course": ["course_activity", "target_age", "level", "day_preference", "name", "surname", "confirmation"],
    "book_spa": ["date", "time", "people_count", "name", "surname", "confirmation"],
    "modify_booked_course": ["name", "surname", "course_activity_old", "target_age_old", "level_old", "day_preference_old", "course_activity_new", "target_age_new", "level_new", "day_preference_new", "confirmation"],
    "modify_booked_spa": ["name", "surname", "date_old", "time_old", "people_count_old", "date_new", "time_new", "people_count_new", "confirmation"],
    "buy_equipment": ["item", "size", "color", "brand", "confirmation"],
    "report_lost_item": ["item", "item_color", "last_seen_location", "last_seen_date", "name", "surname"],
    "user_identification": ["name", "surname"],
    "out_of_scope": []
}

class StateTracker:
    def __init__(self, reference_date: Optional[str] = None, reference_time: Optional[str] = None):
        self.ds: Dict[str, Any] = {
            "intent": None,
            "slots": {}
        }

        self.user_profile: Dict[str, Optional[str]] = {
            "name": None,
            "surname": None
        }

        self.reference_datetime = datetime.now()
        if reference_date:
            try:
                dt_str = f"{reference_date} {reference_time}" if reference_time else reference_date
                fmt = "%Y-%m-%d %H:%M" if reference_time else "%Y-%m-%d"
                self.reference_datetime = datetime.strptime(dt_str, fmt)
            except ValueError:
                pass

        self.has_ds_changed = False

    def reset(self) -> None:
        self.ds = {"intent": None, "slots": {}}
        self.user_profile = {"name": None, "surname": None}
        self.has_ds_changed = False

    def _normalize_string(self, text: str) -> str:
        if not text:
            return ""
        text = text.strip().lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return text

    def _parse_temporal_expression(self, expression: str, slot_type: str) -> Optional[str]:
        if not expression:
            return None

        exp_lower = str(expression).lower().strip()
        now = self.reference_datetime

        if "right now" in exp_lower:
            if "time" in slot_type:
                return now.strftime("%H:%M")
            if "date" in slot_type:
                return now.strftime("%Y-%m-%d")

        if "time" in slot_type:
            time_mapping = {
                "morning": "09:00",
                "this morning": "09:00",
                "afternoon": "15:00",
                "evening": "18:00",
                "tonight": "20:00",
                "night": "21:00"
            }
            for key, val in time_mapping.items():
                if key in exp_lower:
                    return val

        if "date" in slot_type:
            exp_lower = exp_lower.replace("on ", "").replace("for ", "").replace("the ", "")

            if "tonight" in exp_lower or "this morning" in exp_lower:
                exp_lower = exp_lower.replace("tonight", "today").replace("this morning", "today")

            if "next weekend" in exp_lower:
                exp_lower = exp_lower.replace("next weekend", "saturday")
            elif "next week" in exp_lower:
                exp_lower = exp_lower.replace("next week", "monday")

            time_words = ["morning", "afternoon", "evening", "night"]
            for tw in time_words:
                exp_lower = exp_lower.replace(tw, "").strip()

            days_with_s = ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]
            for d in days_with_s:
                if d in exp_lower:
                    exp_lower = exp_lower.replace(d, d[:-1])

            if "next " in exp_lower:
                exp_lower = exp_lower.replace("next ", "")

        prefer_dates = 'past' if slot_type == "last_seen_date" else 'future'

        settings = {
            'RELATIVE_BASE': now,
            'PREFER_DATES_FROM': prefer_dates,
            'DATE_ORDER': 'DMY'
        }

        parsed_datetime = dateparser.parse(exp_lower, settings=settings)

        if not parsed_datetime:
            return None

        if "date" in slot_type:
            orig = str(expression).lower()
            if "next " in orig and "next weekend" not in orig and "next week" not in orig:
                if parsed_datetime.date() <= now.date():
                    parsed_datetime += timedelta(days=7)

            if slot_type == "last_seen_date" and parsed_datetime.date() > now.date():
                try:
                    parsed_datetime = parsed_datetime.replace(year=parsed_datetime.year - 1)
                except ValueError:
                    parsed_datetime = parsed_datetime - timedelta(days=365)

            return parsed_datetime.strftime("%Y-%m-%d")

        elif "time" in slot_type:
            return parsed_datetime.strftime("%H:%M")

        return None

    def _validate_slots(self, intent: str, slots: Dict[str, Any]) -> Dict[str, Any]:
        if intent not in INTENT_SCHEMAS:
            return {}

        valid_schema = INTENT_SCHEMAS[intent]
        cleaned_slots = {}

        VALIDATION_MAP = {
            "facility_type": VALID_FACILITIES,
            "topic": VALID_TOPICS,
            "sub_type": VALID_SUB_TYPES,
            "user_category": VALID_USER_CATEGORIES,
            "course_activity": VALID_COURSES,
            "target_age": VALID_TARGET_AGES,
            "level": VALID_LEVELS,
            "day_preference": VALID_DAYS,
            "item": VALID_EQUIPMENT,
            "confirmation": VALID_CONFIRMATION
        }

        is_right_now = any(
            str(v).lower().strip() == "right now"
            for k, v in slots.items() if v is not None and ("date" in k or "time" in k)
        )
        
        if is_right_now:
            if "date" in valid_schema:
                cleaned_slots["date"] = self._parse_temporal_expression("right now", "date")
            if "time" in valid_schema:
                cleaned_slots["time"] = self._parse_temporal_expression("right now", "time")

        for slot_name, value in slots.items():
            if slot_name in cleaned_slots:
                continue

            if slot_name not in valid_schema or value is None or str(value).lower() == "null":
                cleaned_slots[slot_name] = None
                continue

            val_str = str(value).strip().lower()
            val_underscored = val_str.replace(" ", "_")

            if "date" in slot_name:
                parsed = self._parse_temporal_expression(value, slot_name)
                cleaned_slots[slot_name] = parsed if parsed else val_str
            elif "time" in slot_name:
                parsed = self._parse_temporal_expression(value, slot_name)
                cleaned_slots[slot_name] = parsed if parsed else val_str

            elif "people_count" in slot_name:
                try:
                    num = int(value)
                    cleaned_slots[slot_name] = num if 1 <= num <= 8 else None
                except (ValueError, TypeError):
                    cleaned_slots[slot_name] = None

            elif slot_name in ["name", "surname", "color", "item_color", "brand", "size", "last_seen_location", "specific_inquiry"]:
                cleaned_slots[slot_name] = self._normalize_string(val_str) if slot_name in [
                    "name", "surname", "last_seen_location"] else val_str

            elif slot_name in VALIDATION_MAP:
                val_to_check = val_underscored if "_" in val_underscored and slot_name in [
                    "facility_type", "topic", "course_activity", "item", "sub_type"] else val_str

                if val_to_check in VALIDATION_MAP[slot_name]:
                    cleaned_slots[slot_name] = val_to_check
                else:
                    matches = difflib.get_close_matches(val_to_check, VALIDATION_MAP[slot_name], n=1, cutoff=0.7)
                    cleaned_slots[slot_name] = matches[0] if matches else None

            else:
                cleaned_slots[slot_name] = val_str

        return cleaned_slots

    def _handle_context_switch(self, new_intent: Optional[str]) -> None:
        if new_intent and new_intent != self.ds["intent"]:
            self.ds["intent"] = new_intent
            self.ds["slots"] = {slot: None for slot in INTENT_SCHEMAS.get(new_intent, [])}

    def _update_user_profile(self, validated_updates: Dict[str, Any]) -> None:
        if validated_updates.get("name"):
            self.user_profile["name"] = validated_updates["name"]
        if validated_updates.get("surname"):
            self.user_profile["surname"] = validated_updates["surname"]

    def _update_dialogue_state_slots(self, validated_updates: Dict[str, Any]) -> None:
        for slot_name in self.ds["slots"].keys():
            if slot_name in validated_updates and validated_updates[slot_name] is not None:
                self.ds["slots"][slot_name] = validated_updates[slot_name]
            elif slot_name in ["name", "surname"] and self.user_profile.get(slot_name) is not None:
                if self.ds["slots"].get(slot_name) is None:
                    self.ds["slots"][slot_name] = self.user_profile[slot_name]

    def get_user_profile(self) -> Dict[str, Optional[str]]:
        return self.user_profile
    
    def get_has_ds_changed(self) -> bool:
        return self.has_ds_changed

    def update(self, nlu_result: Dict[str, Any]) -> Dict[str, Any]:
        self.has_ds_changed = False
        old_ds = {
            "intent": self.ds["intent"],
            "slots": self.ds["slots"].copy()
        }

        new_intent = nlu_result.get("intent")
        new_slots = nlu_result.get("slots", {})

        self._handle_context_switch(new_intent)

        validated_updates = self._validate_slots(self.ds["intent"], new_slots)

        self._update_user_profile(validated_updates)
        self._update_dialogue_state_slots(validated_updates)

        if self.ds["slots"].get("confirmation") == "agree":
            has_empy_slots = any(
                value is None for key, value in self.ds["slots"].items() if key != "confirmation"
            )
            if has_empy_slots:
                self.ds["slots"]["confirmation"] = None

        if self.ds["slots"] != old_ds["slots"] or self.ds["intent"] != old_ds["intent"]:
            self.has_ds_changed = True

        return self.ds

    def update_predicted_slots(self, db_slots: Dict[str, Any]) -> None:
        if db_slots:
            for key, value in db_slots.items():
                if value is not None:
                    self.ds["slots"][key] = value

    def clean_invalid_slots(self, violating_slots: str) -> None:
        if not violating_slots:
            return
        
        slots_to_clear = [s.strip() for s in violating_slots.split(",")]
        
        for slot in slots_to_clear:
            if slot in self.ds["slots"]:
                self.ds["slots"][slot] = None