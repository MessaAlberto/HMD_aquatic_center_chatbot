import difflib
from datetime import datetime

# ===================
#    STATIC DATA
# ===================
FACILITY_NOTES = {
    "spa": "Reservation required",
    "lido": "Summer season only"
}
OPENING_HOURS = {
    "swimming_pool": {
        "Mon-Fri": "06:00-22:00",
        "Sat": "08:00-20:00",
        "Sun": "09:00-14:00"
    },
    "gym": {
        "Mon-Fri": "06:00-23:00",
        "Sat-Sun": "08:00-20:00"
    },
    "spa": {
        "Mon-Sun": "10:00-21:00"
    },
    "lido": {
        "Mon-Sun": "09:00-19:00"
    },
    "reception": {
        "Mon-Sun": "08:00-20:00"
    }
}

DETAILED_OPENING_HOURS = {
    "swimming_pool": {
        "monday": "06:00-22:00",
        "tuesday": "06:00-22:00",
        "wednesday": "06:00-22:00",
        "thursday": "06:00-22:00",
        "friday": "06:00-22:00",
        "saturday": "08:00-20:00",
        "sunday": "09:00-14:00"
    },
    "gym": {
        "monday": "06:00-23:00",
        "tuesday": "06:00-23:00",
        "wednesday": "06:00-23:00",
        "thursday": "06:00-23:00",
        "friday": "06:00-23:00",
        "saturday": "08:00-20:00",
        "sunday": "08:00-20:00"
    },
    "spa": {
        "monday": "10:00-21:00",
        "tuesday": "10:00-21:00",
        "wednesday": "10:00-21:00",
        "thursday": "10:00-21:00",
        "friday": "10:00-21:00",
        "saturday": "10:00-21:00",
        "sunday": "10:00-21:00"
    },
    "lido": {
        "monday": "09:00-19:00",
        "tuesday": "09:00-19:00",
        "wednesday": "09:00-19:00",
        "thursday": "09:00-19:00",
        "friday": "09:00-19:00",
        "saturday": "09:00-19:00",
        "sunday": "09:00-19:00"
    },
    "reception": {
        "monday": "08:00-20:00",
        "tuesday": "08:00-20:00",
        "wednesday": "08:00-20:00",
        "thursday": "08:00-20:00",
        "friday": "08:00-20:00",
        "saturday": "08:00-20:00",
        "sunday": "08:00-20:00"
    }
}

TIME_RANGES = {
    "morning": ("06:00", "12:00"),
    "afternoon": ("12:00", "18:00"),
    "evening": ("18:00", "23:00")
}

PRICING = {
    "public_swim": {
        "day_pass": 8.50,
        "10_entry_pass": 75.00,
        "monthly_pass": 60.00,
        "annual_pass": 550.00
    },
    "gym": {
        "day_pass": 10.00,
        "10_entry_pass": 90.00,
        "monthly_pass": 45.00,
        "annual_pass": 450.00
    },
    "spa": {
        "day_pass": 25.00,
        "10_entry_pass": 220.00
    },
    "course": {
        "monthly_pass": 80.00,
        "annual_pass": 700.00
    },
    "lido": {
        "day_pass": 10.00,
        "monthly_pass": 70.00,
        "annual_pass": 200.00
    }
}

DISCOUNTS = {
    "child": 0.50,    # 50% discount
    "student": 0.80,  # 20% discount
    "senior": 0.70,   # 30% discount
    "adult": 1.0      # Full price
}

# ===================
#    STATIC DATA
# ===================

RULES_DB = {
    "swimming_pool": {
        "swimming_cap": {
            "rule": "Mandatory in the main pool at all times.",
            "keywords": ["cap", "hair", "head", "hat"]
        },
        "medical_certificate": {
            "rule": "Required for competitive courses and annual_pass subscriptions.",
            "keywords": ["certificate", "medical", "doctor", "health"]
        },
        "shower": {
            "rule": "You must take a shower before entering the pool.",
            "keywords": ["shower", "wash", "clean", "hygiene"]
        },
        "lane_etiquette": {
            "rule": "Always swim on the right side of the lane.",
            "keywords": ["lane", "direction", "right side", "fast", "slow"]
        }
    },
    "gym": {
        "towel": {
            "rule": "Mandatory to use on all machines and benches.",
            "keywords": ["towel", "cloth", "sweat", "wipe"]
        },
        "shoes": {
            "rule": "Clean indoor shoes are required. No street shoes allowed.",
            "keywords": ["shoes", "sneakers", "footwear", "indoor", "boots"]
        },
        "weights": {
            "rule": "Please return all dumbbells and weights to their racks after use.",
            "keywords": ["weights", "dumbbells", "rack", "return", "equipment"]
        }
    },
    "changing_room": {
        "padlock": {
            "rule": "Required for lockers. Bring your own or buy one at the shop.",
            "keywords": ["padlock", "lock", "locker", "key", "safe"]
        },
        "slippers": {
            "rule": "Mandatory in the changing rooms and showers.",
            "keywords": ["slippers", "flip flops", "shoes", "barefoot", "sandals"]
        }
    },
    "spa": {
        "swimsuit": {
            "rule": "Swimsuits are mandatory. Nudity is not allowed.",
            "keywords": ["swimsuit", "naked", "nudity", "bikini", "clothes"]
        },
        "silence": {
            "rule": "Please maintain a quiet environment. Whispering only.",
            "keywords": ["silence", "quiet", "noise", "talk", "speak", "loud"]
        }
    },
    "lido": {
        "food": {
            "rule": "Picnics are allowed only in designated lawn areas.",
            "keywords": ["food", "eat", "picnic", "snack", "drink"]
        },
        "glass": {
            "rule": "Glass bottles and containers are strictly forbidden.",
            "keywords": ["glass", "bottle", "container", "shatter"]
        }
    }
}

COURSES_DB = {
    "aquagym": {
        "days": ["monday", "wednesday", "friday"],
        "ages": ["teen", "adult"],
        "levels": ["beginner", "intermediate", "advanced"]
    },
    "hydrobike": {
        "days": ["tuesday", "thursday"],
        "ages": ["teen", "adult"],
        "levels": ["intermediate", "advanced"]
    },
    "swimming_school": {
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "ages": ["child", "teen", "adult"],
        "levels": ["beginner", "intermediate", "advanced"]
    },
    "newborn_swimming": {
        "days": ["saturday", "sunday"],
        "ages": ["child"],
        "levels": ["beginner"]
    }
}

SHOP_INVENTORY = {
    "goggles": {"price": 15.00, "colors": ["blue", "black", "red", "clear"], "brands": ["speedo", "arena"]},
    "swimsuit": {"price": 35.00, "colors": ["purple", "black", "red", "white"], "sizes": ["s", "m"], "brands": ["arena"]},
    "towel": {"price": 12.00, "colors": ["white", "blue"], "sizes": ["s", "m"], "brands": ["decathlon", "arena"]},
    "slippers": {"price": 10.00, "colors": ["blue", "black", "red"], "sizes": ["xs", "s", "m", "l", "xl"], "brands": ["adidas", "nike"]},
    "swimming_cap": {"price": 5.00, "colors": ["red", "blue", "black", "yellow"], "sizes": ["s", "m"], "brands": ["arena", "speedo"]},
}

# Subscription
USERS_DB = {
    "mario_rossi": {
        "booked_courses": [
            {
                "course_activity": "swimming_school",
                "target_age": "adult",
                "level": "intermediate",
                "day_preference": "tuesday",
            },
            {
                "course_activity": "aquagym",
                "target_age": "adult",
                "level": "beginner",
                "day_preference": "wednesday",
            },
            {
                "course_activity": "hydrobike",
                "target_age": "adult",
                "level": "intermediate",
                "day_preference": "tuesday",
            }
        ],
        "lost_items": [
            {
                "item": "goggles",
                "item_color": "red",
                "location": "swimming_pool",
                "date_lost": "2026-02-22"
            },
            {
                "item": "towel",
                "item_color": "blue",
                "location": "changing_room",
                "date_lost": "2026-01-15"
            }
        ]
    },
    "luigi_verdi": {
        "booked_spa": [
            {
                "date": "2026-06-15",
                "time": "15:30",
                "people_count": 2,
            }
        ],
    }
}


class MockDatabase:
    """
    Slot values are aready cleaned up through dst. They are or None or DB values.
    """

    def __init__(self, dst):
        self.dst = dst

    def _ensure_user_exists(self, user_id):
        if user_id not in USERS_DB:
            USERS_DB[user_id] = {
                "booked_courses": [],
                "booked_spa": [],
                "lost_items": []
            }
        else:
            if "booked_courses" not in USERS_DB[user_id]:
                USERS_DB[user_id]["booked_courses"] = []
            if "booked_spa" not in USERS_DB[user_id]:
                USERS_DB[user_id]["booked_spa"] = []
            if "lost_items" not in USERS_DB[user_id]:
                USERS_DB[user_id]["lost_items"] = []

    def get_opening_hours(self, facility_type=None, date=None, time=None, **kwargs):
        # VALIDATE values if present
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "date",
                    "options": []
                }

        if time:
            try:
                datetime.strptime(time, "%H:%M")
            except ValueError:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "time",
                    "options": []
                }

        # CHECK completeness
        if not facility_type:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "facility_type",
                "options": list(OPENING_HOURS.keys())
            }

        detailed_schedule = DETAILED_OPENING_HOURS[facility_type]
        schedule = OPENING_HOURS[facility_type]
        notes = FACILITY_NOTES.get(facility_type, "")

        if time and not date:
            # return {
            #     "status": "MISSING_SLOT",
            #     "violating_slot": "date",
            #     "options": []
            # }
            return {
                "status": "INFORM",
                "enriched_data": {
                    "schedule": schedule,
                    "notes": notes
                }
            }

        # ENRICH data
        if not date and not time:
            return {
                "status": "INFORM",
                "enriched_data": {
                    "schedule": schedule,
                    "notes": notes
                }
            }

        dt_obj = datetime.strptime(date, "%Y-%m-%d")
        day_name = dt_obj.strftime("%A").lower()
        day_hours = detailed_schedule.get(day_name)

        if date and not time:
            return {
                "status": "INFORM",
                "enriched_data": {
                    "schedule": day_hours,
                    "notes": notes
                }
            }

        open_str, close_str = day_hours.split("-")
        open_time = datetime.strptime(open_str, "%H:%M").time()
        close_time = datetime.strptime(close_str, "%H:%M").time()
        check_time = datetime.strptime(time, "%H:%M").time()

        return {
            "status": "INFORM",
            "enriched_data": {
                "is_open": open_time <= check_time <= close_time,
                "schedule": day_hours,
                "notes": notes
            }
        }

    def get_pricing(self, service_type=None, sub_type=None, user_category=None, **kwargs):
        # VALIDATE values if present
        if service_type:
            service_pricing = PRICING[service_type]
            if sub_type and sub_type not in service_pricing:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "sub_type",
                    "options": list(service_pricing.keys())
                }

        # CHECK completeness
        if not service_type:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "service_type",
                "options": list(PRICING.keys())
            }

        service_pricing = PRICING[service_type]

        if not sub_type:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "sub_type",
                "options": list(service_pricing.keys())
            }

        if not user_category:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "user_category",
                "options": list(DISCOUNTS.keys())
            }

        # ENRICH data
        return {
            "status": "INFORM",
            "enriched_data": {
                "price": service_pricing[sub_type] * DISCOUNTS.get(user_category, 1.0)
            }
        }

    def get_rules(self, topic=None, specific_inquiry=None, **kwargs):
        # VALIDATE values if present
        if topic and topic not in RULES_DB:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "topic",
                "options": list(RULES_DB.keys())
            }

        # CHECK completeness
        if not topic:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "topic",
                "options": list(RULES_DB.keys())
            }

        # ENRICH data
        topic_rules = RULES_DB[topic]

        if not specific_inquiry:
            all_rules_text = {k: v["rule"] for k, v in topic_rules.items()}
            return {
                "status": "INFORM",
                "enriched_data": {
                    "matched_rules": all_rules_text
                }
            }

        inquiry_lower = specific_inquiry.lower()
        matched_rules = {}

        for rule_key, rule_data in topic_rules.items():
            for keyword in rule_data["keywords"]:
                if keyword in inquiry_lower:
                    matched_rules[rule_key] = rule_data["rule"]
                    break

        if matched_rules:
            return {
                "status": "INFORM",
                "enriched_data": {
                    "matched_rules": matched_rules
                }
            }
        else:
            all_rules_text = {k: v["rule"] for k, v in topic_rules.items()}
            return {
                "status": "INFORM",
                "enriched_data": {
                    "matched_rules": all_rules_text
                }
            }

    def get_book_course(self, course_activity=None, target_age=None, level=None, day_preference=None, user=None, confirmation=None, **kwargs):
        user = user or {}
        # VALIDATE values if present
        if course_activity:
            course_rules = COURSES_DB[course_activity]

            if target_age and target_age not in course_rules["ages"]:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "target_age",
                    "options": course_rules["ages"],
                }

            if level and level not in course_rules["levels"]:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "level",
                    "options": course_rules["levels"]
                }

            if day_preference and day_preference not in course_rules["days"]:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "day_preference",
                    "options": course_rules["days"]
                }

        # CHECK completeness
        if not course_activity:
            # Suggest only courses that match the provided filters (if any)
            valid_courses = []

            for course_name, rules in COURSES_DB.items():
                if target_age and target_age not in rules["ages"]:
                    continue
                if level and level not in rules["levels"]:
                    continue
                if day_preference and day_preference not in rules["days"]:
                    continue

                # If we are here (constraints are met or None), the course is valid for all provided filters
                valid_courses.append(course_name)

            # Edge Case: User provided impossible combination of filters
            # (es. advance newborn course)
            # TODO there is no opt, but the return doesn't not specify what's wrong (it's result difficult for the DM understand thatsome filter must be removed)
            if not valid_courses:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "target_age, level, day_preference",
                    "options": list(COURSES_DB.keys()),
                }

            return {
                "status": "MISSING_SLOT",
                "violating_slot": "course_activity",
                "options": valid_courses
            }

        course_rules = COURSES_DB[course_activity]

        if not target_age:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "target_age",
                "options": course_rules["ages"]
            }

        if not level:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "level",
                "options": course_rules["levels"]
            }

        if not day_preference:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "day_preference",
                "options": course_rules["days"]
            }

        if not user.get("name"):
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "name",
                "options": [],
            }

        if not user.get("surname"):
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "surname",
                "options": [],
            }

        # VALIDATE overlaps
        user_id = f"{user.get('name')}_{user.get('surname')}".lower()

        if user_id in USERS_DB:
            user_bookings = USERS_DB[user_id].get("booked_courses", [])

            for booking in user_bookings:
                if booking["course_activity"] == course_activity:

                    # Same day
                    if booking["day_preference"] == day_preference:
                        return {
                            "status": "OVERLAP",
                            "violating_slot": "day_preference",
                            "options": [d for d in course_rules["days"] if d != day_preference],
                            "blacklist": [day_preference]
                        }

                    # Different age or level
                    if booking["level"] != level:
                        return {
                            "status": "OVERLAP",
                            "violating_slot": "level",
                            "options": [booking["level"]],
                            "blacklist": [level]
                        }
                    if booking["target_age"] != target_age:
                        return {
                            "status": "OVERLAP",
                            "violating_slot": "target_age",
                            "options": [booking["target_age"]],
                            "blacklist": [target_age]
                        }

                    # If we are here, same course, age and level but different day. It's okay

        if not confirmation:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "confirmation",
                "options": ["agree", "deny"],
            }

        if confirmation == "deny":
            return {
                "status": "CANCELLED"
            }

        user_id = f"{user.get('name')}_{user.get('surname')}".lower()
        self._ensure_user_exists(user_id)

        USERS_DB[user_id]["booked_courses"].append({
            "course_activity": course_activity,
            "target_age": target_age,
            "level": level,
            "day_preference": day_preference
        })

        return {"status": "CONFIRMED"}

    def get_book_spa(self, date=None, time=None, people_count=None, user=None, confirmation=None, **kwargs):
        user_data = user or {}

        # VALIDATE values if present
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # TODO: if INVALID_VALUE dst should remove this slot
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "date",
                    "options": [],
                }

        if time:
            try:
                check_time = datetime.strptime(time, "%H:%M").time()
                open_time = datetime.strptime("10:00", "%H:%M").time()
                close_time = datetime.strptime("21:00", "%H:%M").time()

                if not (open_time <= check_time <= close_time):
                    return {
                        "status": "INVALID_VALUE",
                        "violating_slot": "time",
                        "options": ["10:00 - 21:00"],
                    }
            except ValueError:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "time",
                    "options": []
                }

        if people_count is not None:
            try:
                p_count = int(people_count)
                if p_count < 1 or p_count > 8:
                    return {
                        "status": "INVALID_VALUE",
                        "violating_slot": "people_count",
                        "options": ["1-8"],
                    }
            except (ValueError, TypeError):
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "people_count",
                    "options": []
                }

        # CHECK completeness
        if not date:
            return {"status": "MISSING_SLOT", "violating_slot": "date", "options": []}

        if not time:
            return {"status": "MISSING_SLOT", "violating_slot": "time", "options": ["10:00 - 21:00"]}

        if not people_count:
            return {"status": "MISSING_SLOT", "violating_slot": "people_count", "options": ["1-8"]}

        if not user_data.get("name"):
            return {"status": "MISSING_SLOT", "violating_slot": "name", "options": []}

        if not user_data.get("surname"):
            return {"status": "MISSING_SLOT", "violating_slot": "surname", "options": []}

        # VALIDATE overlaps
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()

        if user_id in USERS_DB:
            user_spa_bookings = USERS_DB[user_id].get("booked_spa", [])

            for booking in user_spa_bookings:
                if booking["date"] == date:
                    # User already has a spa booking on the same date
                    booked_dates = [b["date"] for b in user_spa_bookings]
                    return {
                        "status": "OVERLAP",
                        "violating_slot": "date",
                        "options": [],
                        "blacklist": booked_dates
                    }

        if not confirmation:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "confirmation",
                "options": ["agree", "deny"]
            }

        if confirmation == "deny":
            return {
                "status": "CANCELLED"
            }

        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()
        self._ensure_user_exists(user_id)

        USERS_DB[user_id]["booked_spa"].append({
            "date": date,
            "time": time,
            "people_count": int(people_count)
        })

        return {"status": "CONFIRMED"}

    def get_modify_booked_course(self,
                                 course_activity_old=None, target_age_old=None, level_old=None, day_preference_old=None,
                                 course_activity_new=None, target_age_new=None, level_new=None, day_preference_new=None,
                                 user=None, confirmation=None, **kwargs):

        user_data = user or {}

        # FASE 1: IDENTITÀ
        if not user_data.get("name"):
            return {"status": "MISSING_SLOT", "violating_slot": "name", "options": []}
        if not user_data.get("surname"):
            return {"status": "MISSING_SLOT", "violating_slot": "surname", "options": []}
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()

        if user_id not in USERS_DB:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": f"name_surname",
                "options": []
            }

        # FASE 2: RICERCA INTELLIGENTE (Auto-completamento)
        user_bookings = USERS_DB.get(user_id, {}).get("booked_courses", [])

        if not user_bookings:
            # L'utente esiste, ma non ha MAI prenotato un corso
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "",
                "options": ["(no previous bookings)"]
            }

        matching_bookings = []

        for b in user_bookings:
            match = True
            if course_activity_old and b["course_activity"] != course_activity_old:
                match = False
            if target_age_old and b["target_age"] != target_age_old:
                match = False
            if level_old and b["level"] != level_old:
                match = False
            if day_preference_old and b["day_preference"] != day_preference_old:
                match = False

            if match:
                matching_bookings.append(b)

        if len(matching_bookings) == 0:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "course_activity_old",
                "options": list(set([b["course_activity"] for b in user_bookings]))}

        elif len(matching_bookings) > 1:
            # Multiple bookings match the provided old values
            unique_courses = list(set([b["course_activity"] for b in matching_bookings]))
            unique_days = list(set([b["day_preference"] for b in matching_bookings]))
            unique_levels = list(set([b["level"] for b in matching_bookings]))
            unique_ages = list(set([b["target_age"] for b in matching_bookings]))

            if not course_activity_old and len(unique_courses) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "course_activity_old", "options": unique_courses}
            if not day_preference_old and len(unique_days) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "day_preference_old", "options": unique_days}
            if not level_old and len(unique_levels) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "level_old", "options": unique_levels}
            if not target_age_old and len(unique_ages) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "target_age_old", "options": unique_ages}

        # A single booking matches the provided old values
        old_booking = matching_bookings[0]
        course_activity_old = old_booking["course_activity"]
        target_age_old = old_booking["target_age"]
        level_old = old_booking["level"]
        day_preference_old = old_booking["day_preference"]
        course_rules_old = COURSES_DB[course_activity_old]

        self.dst.update_predicted_slots({
            "course_activity_old": course_activity_old,
            "target_age_old": target_age_old,
            "level_old": level_old,
            "day_preference_old": day_preference_old
        })

        # FASE 3: IL MERGING
        if not any([course_activity_new, target_age_new, level_new, day_preference_new]):
            avilable_days = [d for d in course_rules_old["days"] if d != day_preference_old]
            # User didn't provide any new value, we can assume they want to change only the day
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "day_preference_new",
                "options": avilable_days
            }

        eval_course = course_activity_new or course_activity_old
        eval_age = target_age_new or target_age_old
        eval_level = level_new or level_old
        eval_day = day_preference_new or day_preference_old

        # FASE 4: VALIDAZIONE DELLA NUOVA PRENOTAZIONE
        new_course_rules = COURSES_DB[eval_course]

        if eval_age not in new_course_rules["ages"]:
            return {"status": "INVALID_VALUE", "violating_slot": "target_age_new", "options": new_course_rules["ages"]}
        if eval_level not in new_course_rules["levels"]:
            return {"status": "INVALID_VALUE", "violating_slot": "level_new", "options": new_course_rules["levels"]}
        if eval_day not in new_course_rules["days"]:
            return {"status": "INVALID_VALUE", "violating_slot": "day_preference_new", "options": new_course_rules["days"]}

        if (eval_course == course_activity_old and eval_age == target_age_old and
                eval_level == level_old and eval_day == day_preference_old):
            # User didn't change anything
            return {
                "status": "OVERLAP",
                "violating_slot": "day_preference_new",
                "options": [d for d in new_course_rules["days"] if d != day_preference_old],
                "blacklist": [day_preference_old]
            }

        # FASE 5: REGOLE DI BUSINESS SULLE SOVRAPPOSIZIONI
        for booking in user_bookings:
            if (booking["course_activity"] == course_activity_old and
                booking["target_age"] == target_age_old and
                booking["level"] == level_old and
                    booking["day_preference"] == day_preference_old):
                continue

            if booking["course_activity"] == eval_course:
                if booking["day_preference"] == eval_day:
                    # User is trying to change to the same day of another booking of the same course
                    return {
                        "status": "OVERLAP",
                        "violating_slot": "day_preference_new",
                        "options": [d for d in new_course_rules["days"] if d != eval_day],
                        "blacklist": [eval_day]
                    }
                if booking["level"] != eval_level:
                    # User is trying to change to a different level on the same course, which is not allowed
                    return {
                        "status": "OVERLAP",
                        "violating_slot": "level_new",
                        "options": [booking["level"]],
                        "blacklist": [eval_level]
                    }
                if booking["target_age"] != eval_age:
                    # User is trying to change to a different target age on the same course, which is not allowed
                    return {
                        "status": "OVERLAP",
                        "violating_slot": "target_age_new",
                        "options": [booking["target_age"]],
                        "blacklist": [eval_age]
                    }

        full_slots_to_save = {
            "course_activity_old": course_activity_old,
            "target_age_old": target_age_old,
            "level_old": level_old,
            "day_preference_old": day_preference_old,
            "course_activity_new": eval_course,
            "target_age_new": eval_age,
            "level_new": eval_level,
            "day_preference_new": eval_day
        }

        # Update possible null value slots in the dialogue state
        self.dst.update_predicted_slots(full_slots_to_save)

        # FASE 6: CONFERMA
        if not confirmation:
            diff_old = []
            diff_new = []

            if target_age_old != eval_age:
                diff_old.append(target_age_old)
                diff_new.append(eval_age)
            if level_old != eval_level:
                diff_old.append(level_old)
                diff_new.append(eval_level)
            if day_preference_old != eval_day:
                diff_old.append(day_preference_old)
                diff_new.append(eval_day)

            old_details = f" ({', '.join(diff_old)})" if diff_old else ""
            new_details = f" ({', '.join(diff_new)})" if diff_new else ""

            return {
                "status": "MISSING_SLOT",
                "violating_slot": "confirmation",
                "options": ["agree", "deny"],
                "enriched_data": {
                    "old_booking": f"{course_activity_old}{old_details}",
                    "new_booking": f"{eval_course}{new_details}"
                }
            }

        if confirmation == "deny":
            return {
                "status": "CANCELLED"
            }

        # --- SALVATAGGIO NEL DB ---
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()
        user_courses = USERS_DB.get(user_id, {}).get("booked_courses", [])

        for i, booking in enumerate(user_courses):
            if (booking["course_activity"] == course_activity_old and
                booking["target_age"] == target_age_old and
                booking["level"] == level_old and
                    booking["day_preference"] == day_preference_old):

                # Rimuove la vecchia prenotazione
                user_courses.pop(i)
                # Inserisce la nuova
                user_courses.append({
                    "course_activity": eval_course,
                    "target_age": eval_age,
                    "level": eval_level,
                    "day_preference": eval_day
                })
                break

        return {"status": "CONFIRMED"}

    def get_modify_booked_spa(self, date_old=None, time_old=None, people_count_old=None,
                              date_new=None, time_new=None, people_count_new=None,
                              user=None, confirmation=None, **kwargs):
        user_data = user or {}

        # FASE 1: IDENTITÀ
        if not user_data.get("name"):
            return {"status": "MISSING_SLOT", "violating_slot": "name", "options": []}
        if not user_data.get("surname"):
            return {"status": "MISSING_SLOT", "violating_slot": "surname", "options": []}
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()

        if user_id not in USERS_DB:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "name",
                "options": []
            }

        # FASE 2: RICERCA INTELLIGENTE (Auto-completamento)
        user_bookings = USERS_DB.get(user_id, {}).get("booked_spa", [])

        if not user_bookings:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "", # La data è il perno della spa, quindi la blocchiamo
                "options": ["(no previous bookings)"]
            }

        matching_bookings = []

        for b in user_bookings:
            match = True
            if date_old and b["date"] != date_old:
                match = False
            if time_old and b["time"] != time_old:
                match = False
            # Convertiamo in stringa per evitare problemi di tipo (int vs str dal DST)
            if people_count_old and str(b["people_count"]) != str(people_count_old):
                match = False

            if match:
                matching_bookings.append(b)

        if len(matching_bookings) == 0:
            return {
                "status": "INVALID_VALUE",
                "violating_slot": "date_old",  # Usiamo la data come perno per l'errore
                "options": list(set([b["date"] for b in user_bookings]))
            }

        elif len(matching_bookings) > 1:
            unique_dates = list(set([b["date"] for b in matching_bookings]))
            unique_times = list(set([b["time"] for b in matching_bookings]))
            unique_counts = list(set([str(b["people_count"]) for b in matching_bookings]))

            if not date_old and len(unique_dates) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "date_old", "options": unique_dates}
            if not time_old and len(unique_times) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "time_old", "options": unique_times}
            if not people_count_old and len(unique_counts) > 1:
                return {"status": "MISSING_SLOT", "violating_slot": "people_count_old", "options": unique_counts}

        # A single booking matches the provided old values
        old_booking = matching_bookings[0]
        date_old = old_booking["date"]
        time_old = old_booking["time"]
        people_count_old = str(old_booking["people_count"])

        self.dst.update_predicted_slots({
            "date_old": date_old,
            "time_old": time_old,
            "people_count_old": people_count_old
        })

        # FASE 3: IL MERGING
        if not any([date_new, time_new, people_count_new]):
            # User didn't provide any new value, we can assume they want to change only the date
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "date_new",
                "options": []
            }

        eval_date = date_new or date_old
        eval_time = time_new or time_old
        eval_count = people_count_new or people_count_old

        # FASE 4: VALIDAZIONE DELLA NUOVA PRENOTAZIONE (Formato e Limiti SPA)
        if date_new:
            try:
                datetime.strptime(eval_date, "%Y-%m-%d")
            except ValueError:
                return {"status": "INVALID_VALUE", "violating_slot": "date_new", "options": []}

        if time_new:
            try:
                check_time = datetime.strptime(eval_time, "%H:%M").time()
                open_time = datetime.strptime("10:00", "%H:%M").time()
                close_time = datetime.strptime("21:00", "%H:%M").time()
                if not (open_time <= check_time <= close_time):
                    return {"status": "INVALID_VALUE", "violating_slot": "time_new", "options": ["10:00 - 21:00"]}
            except ValueError:
                return {"status": "INVALID_VALUE", "violating_slot": "time_new", "options": []}

        if people_count_new:
            try:
                p_count = int(eval_count)
                if p_count < 1 or p_count > 8:
                    return {"status": "INVALID_VALUE", "violating_slot": "people_count_new", "options": ["1-8"]}
            except ValueError:
                return {"status": "INVALID_VALUE", "violating_slot": "people_count_new", "options": []}

        # Controllo anti-pigrizia (se i dati mixati sono uguali a quelli di partenza)
        if (eval_date == date_old and eval_time == time_old and str(eval_count) == str(people_count_old)):
            return {
                "status": "OVERLAP",
                "violating_slot": "time_new",  # Chiediamo un nuovo orario per risolvere il loop
                # Anche se in realtà tutte le fasce orarie sono libere, forniamo un'opzione valida per sbloccare
                "options": ["10:00 - 21:00"],
                "blacklist": [time_old]  # Escludiamo l'orario vecchio per evitare che l'utente lo riproponga
            }

        # FASE 5: REGOLE DI BUSINESS SULLE SOVRAPPOSIZIONI
        for booking in user_bookings:
            # Ignoriamo la prenotazione che stiamo attivamente modificando
            if (booking["date"] == date_old and booking["time"] == time_old and
                    str(booking["people_count"]) == str(people_count_old)):
                continue

            # NUOVA POLICY: Se sta cercando di prenotare in una data in cui ha GIÀ un'altra prenotazione
            if booking["date"] == eval_date:
                booked_dates = [b["date"] for b in user_bookings]
                return {
                    "status": "OVERLAP",
                    "violating_slot": "date_new",  # Diamo la colpa alla data, non più all'orario
                    "options": [],  # Le opzioni sono le date libere, ma non conoscendole a priori lo lasciamo vuoto
                    "blacklist": booked_dates  # Escludiamo tutte le date già prenotate per evitare che l'utente le riproponga
                }

        # FASE 6: CONFERMA
        full_slots_to_save = {
            "name": user_data.get("name"),
            "surname": user_data.get("surname"),
            "date_old": date_old,
            "time_old": time_old,
            "people_count_old": people_count_old,
            "date_new": eval_date,
            "time_new": eval_time,
            "people_count_new": eval_count
        }

        self.dst.update_predicted_slots(full_slots_to_save)

        if not confirmation:
            diff_old = []
            diff_new = []

            if date_old != eval_date:
                diff_old.append(str(date_old))
                diff_new.append(str(eval_date))
            if time_old != eval_time:
                diff_old.append(str(time_old))
                diff_new.append(str(eval_time))
            if str(people_count_old) != str(eval_count):
                diff_old.append(f"{people_count_old} people")
                diff_new.append(f"{eval_count} people")

            old_details = f" ({', '.join(diff_old)})" if diff_old else ""
            new_details = f" ({', '.join(diff_new)})" if diff_new else ""

            return {
                "status": "MISSING_SLOT",
                "violating_slot": "confirmation",
                "options": ["agree", "deny"],
                "enriched_data": {
                    "old_booking": f"Spa{old_details}",
                    "new_booking": f"Spa{new_details}"
                }
            }

        if confirmation == "deny":
            return {
                "status": "CANCELLED"
            }

        # --- SALVATAGGIO NEL DB ---
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()
        user_spas = USERS_DB.get(user_id, {}).get("booked_spa", [])

        for i, booking in enumerate(user_spas):
            if (booking["date"] == date_old and
                booking["time"] == time_old and
                    str(booking["people_count"]) == str(people_count_old)):

                # Rimuove la vecchia prenotazione
                user_spas.pop(i)
                # Inserisce la nuova
                user_spas.append({
                    "date": eval_date,
                    "time": eval_time,
                    "people_count": int(eval_count)
                })
                break

        return {"status": "CONFIRMED"}

    def get_buy_equipment(self, item=None, color=None, size=None, brand=None, confirmation=None, **kwargs):
        # VALIDATE values if present
        if item:
            item_data = SHOP_INVENTORY[item]

            if color and color not in item_data["colors"]:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "color",
                    "options": item_data["colors"]
                }

            if "sizes" in item_data:
                if size and size not in item_data["sizes"]:
                    return {
                        "status": "INVALID_VALUE",
                        "violating_slot": "size",
                        "options": item_data["sizes"]
                    }
            else:
                if size:
                    return {
                        "status": "INVALID_VALUE",
                        "violating_slot": "size",
                        "options": []
                    }

            if brand and brand not in item_data["brands"]:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "brand",
                    "options": item_data["brands"]
                }

        # CHECK completeness
        if not item:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "item",
                "options": list(SHOP_INVENTORY.keys())
            }

        item_data = SHOP_INVENTORY[item]

        if not color:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "color",
                "options": item_data["colors"]
            }

        if "sizes" in item_data and not size:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "size",
                "options": item_data["sizes"]
            }

        if not brand and len(item_data["brands"]) > 1:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "brand",
                "options": item_data["brands"]
            }

        # VALIDATE overlaps
        final_brand = brand or item_data["brands"][0]
        full_slots_to_save = {
            "item": item,
            "color": color,
            "size": size,
            "brand": final_brand
        }
        self.dst.update_predicted_slots(full_slots_to_save)

        if not confirmation:
            return {
                "status": "MISSING_SLOT",
                "violating_slot": "confirmation",
                "options": ["agree", "deny"],
                "enriched_data": {
                    "price": item_data["price"]
                }
            }

        if confirmation == "deny":
            return {
                "status": "CANCELLED"
            }

        return {
            "status": "CONFIRMED",
            "enriched_data": {
                "price": item_data["price"]
            }
        }

    def get_report_lost_item(self, lost_item=None, item_color=None, last_seen_location=None, last_seen_date=None, user=None, **kwargs):
        user_data = user or {}

        if not user_data.get("name"):
            return {"status": "MISSING_SLOT", "violating_slot": "name", "options": []}
        if not user_data.get("surname"):
            return {"status": "MISSING_SLOT", "violating_slot": "surname", "options": []}
        
        user_id = f"{user_data.get('name')}_{user_data.get('surname')}".lower()

        if last_seen_date:
            try:
                date_obj = datetime.strptime(last_seen_date, "%Y-%m-%d")
                if date_obj.date() > datetime.now().date():
                    return {
                        "status": "INVALID_VALUE",
                        "violating_slot": "last_seen_date",
                        "options": ["today or earlier"]
                    }
            except ValueError:
                return {
                    "status": "INVALID_VALUE",
                    "violating_slot": "last_seen_date",
                    "options": []
                }

        if not lost_item:
            return {"status": "MISSING_SLOT", "violating_slot": "lost_item", "options": []}
        if not item_color:
            return {"status": "MISSING_SLOT", "violating_slot": "item_color", "options": []}
        if not last_seen_location:
            return {"status": "MISSING_SLOT", "violating_slot": "last_seen_location", "options": []}
        if not last_seen_date:
            return {"status": "MISSING_SLOT", "violating_slot": "last_seen_date", "options": []}

        user_lost_items = USERS_DB.get(user_id, {}).get("lost_items", [])

        for lost in user_lost_items:
            db_item = str(lost.get("item", "")).lower()
            current_item = str(lost_item).lower()
            
            is_substring = (current_item in db_item) or (db_item in current_item)
            similarity = difflib.SequenceMatcher(None, current_item, db_item).ratio()
            is_typo = similarity >= 0.75
            
            if ((is_substring or is_typo) and
                lost.get("item_color") == item_color and
                lost.get("location") == last_seen_location and
                lost.get("date_lost") == last_seen_date):

                return {
                    "status": "OVERLAP",
                    "violating_slot": "lost_item",
                    "options": [],
                    "blacklist": [lost_item]
                }

        self._ensure_user_exists(user_id)
        
        USERS_DB[user_id]["lost_items"].append({
            "item": lost_item,
            "item_color": item_color,
            "location": last_seen_location,
            "date_lost": last_seen_date
        })

        return {"status": "CONFIRMED"}

    def get_user_identification(self, name=None, surname=None, **kwargs):
        if name or surname:
            return {"status": "CONFIRMED"}
        return {"status": "MISSING_SLOT", "violating_slot": "name", "options": []}

    def get_out_of_scope(self, **kwargs):
        return {"status": "INFORM", "enriched_data": {}}
