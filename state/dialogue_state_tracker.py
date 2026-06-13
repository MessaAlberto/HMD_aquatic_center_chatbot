import difflib
import logging
import re
from datetime import datetime, timedelta
from typing import Any

import dateparser


logger = logging.getLogger(__name__)

VALID_FACILITIES = ["swimming_pool", "gym", "spa", "lido", "reception"]
VALID_SERVICES = ["public_swim", "gym", "spa", "course", "lido"]
VALID_SUB_TYPES = ["day_pass", "monthly_pass", "annual_pass", "10_entry_pass"]
VALID_USER_CATEGORIES = ["adult", "child", "senior", "student"]
VALID_TOPICS = ["swimming_pool", "gym", "spa", "lido", "changing_room"]
VALID_COURSES = ["aquagym", "hydrobike", "swimming_school", "newborn_swimming"]
VALID_TARGET_AGES = ["child", "teen", "adult"]
VALID_LEVELS = ["beginner", "intermediate", "advanced"]
VALID_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
VALID_EQUIPMENT = ["swimming_cap", "goggles", "towel", "slippers", "swimsuit"]
VALID_CONFIRMATION = ["agree", "deny"]

INTENT_SCHEMAS = {
    "ask_opening_hours": ["facility_type", "date", "time"],
    "ask_pricing": ["service_type", "sub_type", "user_category"],
    "ask_rules": ["topic", "specific_inquiry"],
    "book_course": ["course_activity", "target_age", "level", "day_preference", "name", "surname", "confirmation"],
    "book_spa": ["date", "time", "people_count", "name", "surname", "confirmation"],
    "modify_booked_course": ["name", "surname", "course_activity_old", "target_age_old", "level_old", "day_preference_old", "course_activity_new", "target_age_new", "level_new", "day_preference_new", "confirmation"],
    "modify_booked_spa": ["name", "surname", "date_old", "time_old", "people_count_old", "date_new", "time_new", "people_count_new", "confirmation"],
    "cancel_booked_course": ["course_activity", "target_age", "level", "day_preference", "name", "surname", "confirmation"],
    "cancel_booked_spa": ["date", "time", "people_count", "name", "surname", "confirmation"],
    "buy_equipment": ["item", "size", "color", "brand", "confirmation"],
    "report_lost_item": ["lost_item", "item_color", "last_seen_location", "last_seen_date", "name", "surname"],
    "user_identification": ["name", "surname"],
    "greeting_closing": [],
    "out_of_scope": [],
}

VALIDATION_MAP = {
    "facility_type": VALID_FACILITIES,
    "service_type": VALID_SERVICES,
    "topic": VALID_TOPICS,
    "sub_type": VALID_SUB_TYPES,
    "user_category": VALID_USER_CATEGORIES,
    "course_activity": VALID_COURSES,
    "target_age": VALID_TARGET_AGES,
    "level": VALID_LEVELS,
    "day_preference": VALID_DAYS,
    "item": VALID_EQUIPMENT,
    "confirmation": VALID_CONFIRMATION,
}


class StateTracker:
    """Maintains the current dialogue state and normalizes NLU slot updates."""

    def __init__(self, reference_date: str | None = None, reference_time: str | None = None) -> None:
        self.ds: dict[str, Any] = {"intent": None, "slots": {}}
        self.last_completed_ds: dict[str, Any] = {"intent": None, "slots": {}}
        self.user_profile: dict[str, str | None] = {"name": None, "surname": None}
        self.reference_datetime = self._build_reference_datetime(reference_date, reference_time)
        self.has_ds_changed = False

    def _build_reference_datetime(self, reference_date: str | None, reference_time: str | None) -> datetime:
        if not reference_date:
            return datetime.now()

        try:
            dt_str = f"{reference_date} {reference_time}" if reference_time else reference_date
            fmt = "%Y-%m-%d %H:%M" if reference_time else "%Y-%m-%d"
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            return datetime.now()

    def reset(self) -> None:
        """Reset the active state, completed state and stored user profile."""
        self.ds = {"intent": None, "slots": {}}
        self.last_completed_ds = {"intent": None, "slots": {}}
        self.user_profile = {"name": None, "surname": None}
        self.has_ds_changed = False

    def _normalize_string(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"[^a-z0-9\s]", "", text.strip().lower())

    def _parse_temporal_expression(self, expression: str, slot_type: str) -> str | None:
        if not expression:
            return None

        exp_lower = str(expression).lower().strip()
        now = self.reference_datetime

        if "time" in slot_type:
            parsed_time = self._parse_time_expression(exp_lower, now)
            if parsed_time:
                return parsed_time

        is_next = False

        if "date" in slot_type:
            if "right now" in exp_lower:
                return now.strftime("%Y-%m-%d")

            exp_lower = self._clean_date_expression(exp_lower)

            if "next " in exp_lower:
                is_next = True
                exp_lower = exp_lower.replace("next ", "")

            exp_lower = exp_lower.replace("this ", "")

        prefer_dates = "past" if slot_type == "last_seen_date" else "future"
        settings = {"RELATIVE_BASE": now, "PREFER_DATES_FROM": prefer_dates, "DATE_ORDER": "DMY"}
        parsed_datetime = dateparser.parse(exp_lower, settings=settings)

        if not parsed_datetime:
            return None

        if "date" in slot_type:
            if is_next and parsed_datetime.date() <= now.date():
                parsed_datetime += timedelta(days=7)

            if slot_type == "last_seen_date" and parsed_datetime.date() > now.date():
                try:
                    parsed_datetime = parsed_datetime.replace(year=parsed_datetime.year - 1)
                except ValueError:
                    parsed_datetime -= timedelta(days=365)

            return parsed_datetime.strftime("%Y-%m-%d")

        if "time" in slot_type:
            return parsed_datetime.strftime("%H:%M")

        return None

    def _parse_time_expression(self, expression: str, now: datetime) -> str | None:
        time_mapping = {
            "right now": now.strftime("%H:%M"),
            "early morning": "07:00",
            "morning": "09:00",
            "this morning": "09:00",
            "after breakfast": "10:00",
            "lunchtime": "12:30",
            "around lunch": "12:30",
            "after lunch": "14:00",
            "afternoon": "15:00",
            "late afternoon": "17:00",
            "evening": "18:00",
            "after dinner": "20:00",
            "tonight": "20:00",
            "night": "21:00",
        }

        for key, value in time_mapping.items():
            if key in expression:
                return value

        for word in expression.split():
            matches = difflib.get_close_matches(word, time_mapping.keys(), n=1, cutoff=0.75)
            if matches:
                return time_mapping[matches[0]]

        return None

    def _clean_date_expression(self, expression: str) -> str:
        expression = expression.replace("on ", "").replace("for ", "").replace("the ", "")
        expression = expression.replace("tonight", "today").replace("this morning", "today")
        expression = expression.replace("this weekend", "saturday").replace("next weekend", "saturday").replace("weekend", "saturday")
        expression = expression.replace("next week", "monday")

        for time_word in ["morning", "afternoon", "evening", "night"]:
            expression = expression.replace(time_word, "").strip()

        for plural_day in ["mondays", "tuesdays", "wednesdays", "thursdays", "fridays", "saturdays", "sundays"]:
            expression = expression.replace(plural_day, plural_day[:-1])

        return expression

    def _validate_slots(self, intent: str, slots: dict[str, Any]) -> dict[str, Any]:
        if intent not in INTENT_SCHEMAS:
            return {}

        valid_schema = INTENT_SCHEMAS[intent]
        cleaned_slots: dict[str, Any] = {}

        if self._contains_right_now(slots):
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

            cleaned_slots[slot_name] = self._clean_slot_value(slot_name, value)

        return cleaned_slots

    def _contains_right_now(self, slots: dict[str, Any]) -> bool:
        return any(str(value).lower().strip() == "right now" for key, value in slots.items() if value is not None and ("date" in key or "time" in key))

    def _clean_slot_value(self, slot_name: str, value: Any) -> Any:
        val_str = str(value).strip().lower()
        val_underscored = val_str.replace(" ", "_")

        if "date" in slot_name or "time" in slot_name:
            parsed = self._parse_temporal_expression(value, slot_name)
            return parsed if parsed else val_str

        if "people_count" in slot_name:
            try:
                number = int(value)
                return number if 1 <= number <= 8 else None
            except (ValueError, TypeError):
                return None

        if slot_name in ["name", "surname", "last_seen_location"]:
            return self._normalize_string(val_str)

        if slot_name in ["color", "item_color", "brand", "size", "specific_inquiry"]:
            return val_str

        if slot_name in VALIDATION_MAP:
            value_to_check = val_underscored if "_" in val_underscored and slot_name in ["facility_type", "topic", "course_activity", "item", "sub_type"] else val_str

            if value_to_check in VALIDATION_MAP[slot_name]:
                return value_to_check

            matches = difflib.get_close_matches(value_to_check, VALIDATION_MAP[slot_name], n=1, cutoff=0.7)
            return matches[0] if matches else None

        return val_str

    def _handle_context_switch(self, new_intent: str | None) -> None:
        if not new_intent:
            return

        if new_intent != self.ds["intent"] or not self.ds.get("slots"):
            self.ds["intent"] = new_intent

            if new_intent == self.last_completed_ds.get("intent") and new_intent.startswith("ask_"):
                self.ds["slots"] = self.last_completed_ds["slots"].copy()
            else:
                self.ds["slots"] = {slot: None for slot in INTENT_SCHEMAS.get(new_intent, [])}

    def _update_user_profile(self, validated_updates: dict[str, Any]) -> None:
        if validated_updates.get("name"):
            self.user_profile["name"] = validated_updates["name"]
        if validated_updates.get("surname"):
            self.user_profile["surname"] = validated_updates["surname"]

    def _update_dialogue_state_slots(self, validated_updates: dict[str, Any]) -> None:
        for slot_name in self.ds["slots"].keys():
            if slot_name in validated_updates and validated_updates[slot_name] is not None:
                self.ds["slots"][slot_name] = validated_updates[slot_name]
            elif slot_name in ["name", "surname"] and self.user_profile.get(slot_name) is not None and self.ds["slots"].get(slot_name) is None:
                self.ds["slots"][slot_name] = self.user_profile[slot_name]

    def _get_actual_changes(self, validated_updates: dict[str, Any]) -> list[str]:
        actual_changes = []

        for slot_name, new_value in validated_updates.items():
            old_value = self.ds["slots"].get(slot_name)

            if new_value is not None and str(old_value) != str(new_value):
                actual_changes.append(slot_name)
                logger.debug("Slot changed: %s | %s -> %s", slot_name, old_value, new_value)

        return actual_changes

    def _clear_unsafe_confirmation(self, validated_updates: dict[str, Any], actual_changes: list[str]) -> None:
        if "confirmation" in actual_changes and len(actual_changes) > 1:
            logger.debug("Clearing confirmation because other slot changes were detected in the same turn.")
            validated_updates["confirmation"] = None

    def _remove_confirmation_if_state_incomplete(self) -> None:
        if self.ds["slots"].get("confirmation") != "agree":
            return

        has_empty_slots = any(value is None for key, value in self.ds["slots"].items() if key != "confirmation")

        if has_empty_slots:
            logger.debug("Clearing confirmation because the dialogue state is still incomplete.")
            self.ds["slots"]["confirmation"] = None

    def get_user_profile(self) -> dict[str, str | None]:
        return self.user_profile

    def get_has_ds_changed(self) -> bool:
        return self.has_ds_changed

    def update(self, nlu_result: dict[str, Any]) -> dict[str, Any]:
        """Apply a new NLU result to the dialogue state."""
        self.has_ds_changed = False
        old_ds = {"intent": self.ds["intent"], "slots": self.ds["slots"].copy()}

        new_intent = nlu_result.get("intent")
        new_slots = nlu_result.get("slots", {})

        self._handle_context_switch(new_intent)

        validated_updates = self._validate_slots(self.ds["intent"], new_slots)
        actual_changes = self._get_actual_changes(validated_updates)

        logger.debug("DST actual changes: %s", actual_changes)

        self._clear_unsafe_confirmation(validated_updates, actual_changes)
        self._update_user_profile(validated_updates)
        self._update_dialogue_state_slots(validated_updates)
        self._remove_confirmation_if_state_incomplete()

        if self.ds["slots"] != old_ds["slots"] or self.ds["intent"] != old_ds["intent"]:
            self.has_ds_changed = True

        logger.debug("Updated DST: %s", self.ds)
        logger.debug("Updated user profile: %s", self.user_profile)

        return self.ds

    def update_predicted_slots(self, db_slots: dict[str, Any]) -> None:
        """Fill slots predicted by the database layer."""
        for key, value in (db_slots or {}).items():
            if value is not None:
                self.ds["slots"][key] = value

    def clean_invalid_slots(self, violating_slots: str) -> None:
        """Clear slots rejected by the database validation layer."""
        if not violating_slots:
            return

        for slot in [item.strip() for item in violating_slots.split(",")]:
            if slot in self.ds["slots"]:
                self.ds["slots"][slot] = None
            if slot in self.user_profile:
                self.user_profile[slot] = None

    def complete_task(self) -> None:
        """Store the completed task and clear the active dialogue state."""
        self.last_completed_ds = {"intent": self.ds["intent"], "slots": self.ds["slots"].copy()}

        if "confirmation" in self.last_completed_ds["slots"]:
            self.last_completed_ds["slots"]["confirmation"] = None

        self.ds["intent"] = None
        self.ds["slots"] = {}
