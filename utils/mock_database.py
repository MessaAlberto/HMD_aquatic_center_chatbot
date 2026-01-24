from datetime import datetime, timedelta

# ===================
#    STATIC DATA
# ===================

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
        "Mon-Sun": "10:00-21:00",
        "notes": "Reservation required"
    },
    "lido": {
        "Mon-Sun": "09:00-19:00",
        "notes": "Summer season only"
    },
    "reception": {
        "Mon-Sun": "08:00-20:00"
    }
}

TIME_RANGES = {
    "morning": ("06:00", "12:00"),
    "afternoon": ("12:00", "18:00"),
    "evening": ("18:00", "23:00")
}

PRICING = {
    "swimming_pool": {
        "single_entry": 8.50,
        "10_entries": 75.00,
        "monthly": 60.00,
        "annual": 550.00
    },
    "gym": {
        "single_entry": 10.00,
        "10_entries": 90.00,
        "monthly": 45.00,
        "annual": 450.00
    },
    "spa": {
        "single_entry": 25.00,
        "10_entries": 220.00
    },
    "courses": {
        "monthly": 80.00,
        "annual": 700.00
    },
    "lido": {
        "single_entry": 10.00,
        "monthly": 70.00,
        "annual": 200.00
    }
}

DISCOUNTS = {
    "child": 0.50,   # 50% discount
    "student": 0.80,  # 20% discount
    "senior": 0.70,  # 30% discount
    "adult": 1.0     # Full price
}

RULES = {
    "swimming cap": "Mandatory in the main pool at all times.",
    "medical certificate": "Required for annual subscriptions and competitive courses.",
    "slippers": "Mandatory in the changing rooms and pool deck.",
    "towel": "Highly recommended for gym and required for SPA.",
    "padlock": "Required for lockers. You can bring your own or buy one at the shop."
}

COURSE_SCHEDULE = {
    "aquagym": ["Monday", "Wednesday", "Friday"],
    "hydrobike": ["Tuesday", "Thursday"],
    "swimming_school": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "neonatal": ["Saturday", "Sunday"]
}

SHOP_INVENTORY = {
    "goggles": {"price": 15.00, "colors": ["blue", "black", "red", "clear"], "brand": "Speedo"},
    "swimsuit": {"price": 35.00, "sizes": ["S", "M"], "brand": "Arena"},
    "towel": {"price": 12.00, "colors": ["white", "blue"], "brand": "Decathlon"},
    "slippers": {"price": 10.00, "sizes": ["XS", "M", "L", "XL"], "brand": "Adidas"},
    "cap": {"price": 5.00, "colors": ["red", "blue", "black", "yellow"], "brand": "Arena"}
}

# Subscription
USERS_DB = {
    "mario_rossi": {
        "booked_courses": [
            {
                "course_activity": "swimming_school",
                "target_age": "adults",
                "level": "intermediate",
                "day_preference": "Monday",
            }
        ],
        "lost_items": [
            {
                "item": "goggles",
                "item_color": "red",
                "location": "swimming_pool",
                "date_lost": "22/02/2026"
            },
            {
                "item": "towel",
                "item_color": "blue",
                "location": "changing_room",
                "date_lost": "15/01/2026"
            }
        ]
    },
    "luigi_verdi": {
        "booked_spa": [
            {
                "date": "15/04/2026",
                "time": "15:30",
                "people_count": 2,
            }
        ],
    }
}


# ===================
#   HELP FUNCTIONS
# ===================


def normalize_date(date_str):
    """
    Converts user-provided date strings into datetime.date objects.
    Handles:
        - Relative terms: today, tomorrow, yesterday
        - Weekdays: Monday, next Monday, this Monday
        - ISO dates: YYYY-MM-DD
        - European dates: DD/MM or DD/MM/YYYY
    Returns:
        parsed_date (datetime.date) or None
        day_name (str, e.g., "Monday") or None
    """
    if not date_str:
        return None, None

    today = datetime.now().date()
    date_str = date_str.lower().strip()

    parsed_date = None

    # Handle relative keywords
    if date_str == "today":
        parsed_date = today
    elif date_str == "tomorrow":
        parsed_date = today + timedelta(days=1)
    elif date_str == "yesterday":
        parsed_date = today - timedelta(days=1)

    # Handle Weekdays (e.g., "Monday" or "next Friday")
    if not parsed_date:
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        clean_day = date_str.replace("next ", "").replace("this ", "").strip()

        if clean_day in weekdays:
            target_idx = weekdays.index(clean_day)
            current_idx = today.weekday()  # 0=Monday, 6=Sunday

            days_ahead = target_idx - current_idx
            # If user says "next" or the day is today/past, go to next week
            if "next" in date_str or days_ahead <= 0:
                days_ahead += 7
            parsed_date = today + timedelta(days=days_ahead)

    # Handle ISO Dates (YYYY-MM-DD)
    if not parsed_date:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass  # Not a valid ISO date

    # European date DD/MM or DD/MM/YYYY
    if not parsed_date:
        try:
            parts = date_str.split("/")
            if len(parts) == 2:
                day, month = int(parts[0]), int(parts[1])
                year = today.year  # assume current year if missing
            elif len(parts) == 3:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                raise ValueError
            parsed_date = datetime(year, month, day).date()
        except ValueError:
            pass

    if parsed_date:
        # Returns the date object and the day name (e.g., "Monday")
        return parsed_date, parsed_date.strftime("%A")

    return None, None


def get_day_interval(hours_info, day_name):
    if not day_name:
        return None

    day = day_name[:3]  # Monday -> Mon
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for key, interval in hours_info.items():
        if key == "notes":
            continue

        if "-" in key:
            start, end = key.split("-")
            if days.index(start) <= days.index(day) <= days.index(end):
                return interval
        else:
            if key == day:
                return interval

    return None


def retrieve_matching_bookings(bookings, mapping_old_to_db, normalized_slots):
    matching_bookings = []

    for booked in bookings:
        all_match = True
        for slot_key, db_key in mapping_old_to_db.items():
            user_value = normalized_slots.get(slot_key)
            if user_value:      # Match only on provided old fields
                if user_value.lower() != booked.get(db_key, "").lower():
                    all_match = False
                    break

        if all_match:
            matching_bookings.append(booked)

    if not matching_bookings:
        return None, {
            "status": "error",
            "message": f"No matching booking in DB",
            "slots": normalized_slots
        }
    
    if len(matching_bookings) > 1:
        return None, {
            "status": "success",
            "message": f"Found {len(matching_bookings)} matching booking in DB",
            "slots": normalized_slots,
            "matching_bookings": matching_bookings
        }
    
    # Only one booking matches, proceed with new values
    booking_to_modify = matching_bookings[0]

    # If old booking not complete, return for confirmation
    missing_old = [k for k in mapping_old_to_db.keys() if not normalized_slots.get(k)]
    if missing_old:
        return None, {
            "status": "success",
            "message": f"Missing: {', '.join(missing_old)}",
            "slots": normalized_slots,
            "matching_booking": booking_to_modify
        }
    
    return booking_to_modify, None


def slot_normalization_course(slots, slots_to_validate):
    normalized_slots = {}
    for key in slots_to_validate:
        value = slots.get(key)
        if value is None:       # TODO: if user explicitly says remove the value, we should handle it
            continue
        # date normalization
        if "day_preference" in key:
            __ , day_name = normalize_date(value)
            normalized_slots[key] = day_name if day_name else value
        else:
            # simple normalization: lowercase + strip
            normalized_slots[key] = str(value).strip().lower()
    return normalized_slots


def slot_normalization_spa(slots, slots_to_validate):
    normalized_slots = {}
    for key in slots_to_validate:
        value = slots.get(key)
        if value is None:
            continue
        # date normalization
        if "date" in key:
            parsed_date, __ = normalize_date(value)
            normalized_slots[key] = parsed_date.strftime("%d/%m/%Y") if parsed_date else value
        elif "time" in key:
            time_str = str(value).strip().lower()
            if time_str in TIME_RANGES:
                start, end = TIME_RANGES[time_str]

                start_dt = datetime.strptime(start, "%H:%M")
                end_dt = datetime.strptime(end, "%H:%M")
                delta = (end_dt - start_dt).total_seconds() / 2

                # Mean hour
                mean_dt = start_dt + timedelta(seconds=delta)
                normalized_slots[key] = mean_dt.strftime("%H:%M")
            else:
                # Try to parse HH:MM
                try:
                    t = datetime.strptime(time_str, "%H:%M").time()
                    normalized_slots[key] = t.strftime("%H:%M")
                except ValueError:
                    # fallback: keep original string
                    normalized_slots[key] = value
        else:
            # simple normalization: lowercase + strip
            normalized_slots[key] = str(value).strip().lower()
    return normalized_slots


def validate_day_preference_on_course(course, day_preference):
    valid_days = COURSE_SCHEDULE.get(course, [])
    if day_preference and day_preference.title() not in valid_days:
        return False, valid_days
    return True, []


def validate_time_in_range(time_str):
    spa_hours = OPENING_HOURS["spa"]["Mon-Sun"]
    open_time, close_time = spa_hours.split("-")
    check_time = time_str
    if check_time:
        try:
            check_t = datetime.strptime(check_time, "%H:%M").time()
            open_t = datetime.strptime(open_time, "%H:%M").time()
            close_t = datetime.strptime(close_time, "%H:%M").time()

            if not (open_t <= check_t <= close_t):
                return False
        except ValueError:
            return False
    return True


def slot_normalization_lost_item(slots, slots_to_validate):
    normalized_slots = {}
    for key in slots_to_validate:
        value = slots.get(key)
        if value is None:
            continue
        # date normalization
        if "date_lost" in key:
            parsed_date, _ = normalize_date(value)
            normalized_slots[key] = parsed_date.strftime("%d/%m/%Y") if parsed_date else value
        else:
            # simple normalization: lowercase + strip
            normalized_slots[key] = str(value).strip().lower()
    return normalized_slots


def get_user_key(name, surname):
    if not name or not surname:
        return None
    return f"{name.strip().lower()}_{surname.strip().lower()}"

# ===================
#   LOGIC FUNCTIONS
# ===================

def query_opening_hours(slots):
    facility = slots.get("facility_type") or "swimming_pool"
    date_str = slots.get("date")
    time_str = slots.get("time")

    if not date_str and not time_str:
        return {
            "status": "success",
            "message": "Missing: date and time",
        }

    facility_norm = facility.lower().replace(" ", "_")
    if facility_norm not in OPENING_HOURS:
        return {
            "status": "error",
            "message": f"Not found facility in DB"
        }

    normalized_date, day_name = normalize_date(date_str)
    date_display = normalized_date.strftime("%d/%m/%Y") if normalized_date else date_str

    hours_info = OPENING_HOURS[facility_norm]
    interval = get_day_interval(hours_info, day_name)

    if not interval:
        return {
            "status": "success",
            "message": f"Fullfilled: closed (allowed: {', '.join(hours_info.keys())})",
            "slots": {"facility_type": facility_norm, "date": date_display, "time": time_str}
        }

    open_time, close_time = interval.split("-")
    open_t = datetime.strptime(open_time, "%H:%M").time()
    close_t = datetime.strptime(close_time, "%H:%M").time()

    is_open = True
    if time_str:
        try:
            time_key = time_str.lower()
            if time_key in TIME_RANGES:
                start, end = TIME_RANGES[time_key]
                start_t = datetime.strptime(start, "%H:%M").time()
                end_t = datetime.strptime(end, "%H:%M").time()
                is_open = not (end_t <= open_t or start_t >= close_t)
            else:
                check_t = datetime.strptime(time_str, "%H:%M").time()
                is_open = open_t <= check_t <= close_t
        except ValueError:
            is_open = False
    else:
        is_open = True

    return {
        "status": "success",
        "message": f"Fullfilled: {is_open} (allowed: {', '.join(hours_info.keys())})",
        "slots": {"facility_type": facility_norm, "date": date_display, "time": time_str, "notes": hours_info.get("notes")}
    }


def query_pricing(slots):
    facility_raw = slots.get("facility_type")
    sub_type_raw = slots.get("subscription_type")
    user_cat_raw = slots.get("user_category")

    if not facility_raw:
        return {
            "status": "error",
            "message": "Missing facility."
        }

    facility = facility_raw.lower().replace(" ", "_")
    sub_type = sub_type_raw.lower() if sub_type_raw else None
    user_cat = user_cat_raw.lower() if user_cat_raw else "adult"

    if facility not in PRICING:
        return {
            "status": "error",
            "message": "Not found facility in DB",
            "slots": {"facility_type": facility_raw, "subscription_type": sub_type_raw, "user_category": user_cat_raw}
        }

    available_subs = PRICING[facility]

    if not sub_type or sub_type not in available_subs:
        subs_list = ", ".join(available_subs.keys())
        return {
            "status": "success",
            "message": f"Fullfilled: available subscriptions: {subs_list}",
            "slots": {"facility_type": facility_raw, "subscription_type": sub_type_raw, "user_category": user_cat_raw}
        }

    if user_cat not in DISCOUNTS:
        user_cat = "adult"

    base_price = available_subs[sub_type]
    multiplier = DISCOUNTS[user_cat]
    final_price = base_price * multiplier

    return {
        "status": "success",
        "message": f"Fullfilled: price is €{final_price:.2f}",
        "slots": {"facility_type": facility_raw, "subscription_type": sub_type_raw, "user_category": user_cat_raw}
    }


def query_rules(slots):
    topic = slots.get("topic")
    if not topic:
        return {
            "status": "error",
            "message": f"Not found topic in DB (allowed: {', '.join(RULES.keys())})",
            "slots": {"topic": topic}
        }

    topic_norm = topic.lower().replace(" ", "_")

    for key, rule in RULES.items():
        key_norm = key.lower().replace(" ", "_")

        # Special case: cap must match only swimming_cap
        if topic_norm == "cap":
            if key_norm == "swimming_cap":
                return {
                    "status": "success",
                    "message": f"Fullfilled: {rule}",
                    "slots": {"topic": topic}
                }
            continue

        # Exact or substring match
        if topic_norm == key_norm or topic_norm in key_norm or key_norm in topic_norm:
            return {
                "status": "success",
                "message": f"Fullfilled: {rule}",
                "slots": {"topic": topic}
            }

        # 4 consecutive characters match
        for i in range(len(topic_norm) - 3):
            if topic_norm[i:i+4] in key_norm:
                return {
                    "status": "success",
                    "message": f"Fullfilled: {rule}",
                    "slots": {"topic": topic}
                }

    return {
        "status": "error",
        "message": f"Not found topic in DB (allowed: {', '.join(RULES.keys())})",
        "slots": {"topic": topic}
    }


def query_user_identification(slots):
    name = slots.get("name")
    surname = slots.get("surname")

    if not name or not surname:
        return {
            "status": "error",
            "message": f"Missing: {'name and surname' if not name and not surname else 'name' if not name else 'surname'}."
        }

    user = f"{name.strip().lower()}_{surname.strip().lower()}"
    if not user:
        return {
            "status": "success",
            "message": f"Not found user in DB.",
            "slots": {"name": name, "surname": surname}
        }

    return {
        "status": "success",
        "message": f"Found user: {user}.",
        "slots": {"name": name, "surname": surname}
    }


def query_book_course(slots, slots_to_validate, user):
    # Normalized
    normalized_slots = slot_normalization_course(slots, slots_to_validate)

    # Validate day_preference for course_activity
    course = normalized_slots.get("course_activity")
    day_pref = normalized_slots.get("day_preference")
    is_valid, allowed_days = validate_day_preference_on_course(course, day_pref)
    if not is_valid:
        return {
            "status": "error",
            "message": f"'{day_pref}' is not valid for '{course}' (allowed: {', '.join(allowed_days)})",
            "slots": normalized_slots
        }

    # Check completeness
    required_fields = ["course_activity", "target_age", "level", "day_preference"]
    missing_fields = [f for f in required_fields if f not in normalized_slots]
    if missing_fields:
        return {
            "status": "success",
            "message": f"Missing: {', '.join(missing_fields)}",
            "slots": normalized_slots,
        }

    # User key
    user_key = get_user_key(user.get("name"), user.get("surname"))

    # Check if user exists in DB
    existing_user = USERS_DB.get(user_key)
    if existing_user:
        # If user has booked courses, compare fields
        bookings = existing_user.get("booked_courses", [])

        for booked in bookings:
            # target_age must be the same
            if booked.get("target_age") != normalized_slots.get("target_age"):
                return {
                    "status": "error",
                    "message": f"Missmatch: {booked.get("target_age")}(DB) vs {normalized_slots.get("target_age")}(input)",
                    "slots": normalized_slots
                }

            # Check overlaps on "course_activity" and "day_preference" with exception for "target_age" and "level"
            exclude_keys = {"target_age", "level"}
            overlap = set(booked.keys()).intersection(set(normalized_slots.keys())) - exclude_keys
            if overlap:
                return {
                    "status": "error",
                    "message": f"Overlaps: {', '.join(overlap)}",
                    "slots": normalized_slots
                }
        return {
            "status": "success",
            "message": f"Fullfilled book + {user_key}",
            "slots": normalized_slots
        }

    # User not in DB, success for complete booking slots
    return {
        "status": "success",
        "message": f"Fullfilled book + missing user",
        "slots": normalized_slots
    }


def query_book_spa(slots, slots_to_validate, user):
    # Normalized
    normalized_slots = slot_normalization_spa(slots, slots_to_validate)

    # Validate time slot
    is_valid = validate_time_in_range(normalized_slots.get("time"))
    if not is_valid:
        return {
            "status": "error",
            "message": f"'{normalized_slots.get('time_new')}' not valid for 'spa' (allowed: {OPENING_HOURS['spa']['Mon-Sun']})",
            "slots": normalized_slots
        }

    # Check completeness
    required_fields = ["date", "time", "people_count"]
    missing_fields = [f for f in required_fields if f not in normalized_slots]
    if missing_fields:
        return {
            "status": "success",
            "message": f"Missing: {', '.join(missing_fields)}",
            "slots": normalized_slots,
        }

    # User key
    user_key = get_user_key(user.get("name"), user.get("surname"))

    # Check if user exists in DB
    existing_user = USERS_DB.get(user_key)
    if existing_user:
        # If user has booked spa, compare fields
        bookings = existing_user.get("booked_spa", [])

        for booked in bookings:
            # Check overlaps only on date
            overlap = set(booked.keys()).intersection(set(normalized_slots.keys())).intersection({"date"})
            if overlap:
                return {
                    "status": "error",
                    "message": f"Overlaps: {booked.get('date')}",
                    "slots": normalized_slots
                }
        return {
            "status": "success",
            "message": f"Fullfilled book + {user_key}",
            "slots": normalized_slots
        }

    # User not in DB, success for complete booking slots
    return {
        "status": "success",
        "message": f"Fullfilled book + missing user",
        "slots": normalized_slots
    }


def query_modify_book_course(slots, slots_to_validate, user):
    if not user:
        return {
            "status": "error",
            "message": "Missing: user"
        }

    user_key = get_user_key(user.get("name"), user.get("surname"))
    if user_key not in USERS_DB:
        return {
            "status": "error",
            "message": f"Not found user in DB: {user_key}"
        }

    bookings = USERS_DB[user_key].get("booked_courses", [])
    if not bookings:
        return {
            "status": "error",
            "message": "Not booked courses found in DB"
        }

    # Normalize old and new values
    normalized_slots = slot_normalization_course(slots, slots_to_validate)

    # Check old values against DB
    mapping_old_to_db = {
        "course_activity_old": "course_activity",
        "target_age_old": "target_age",
        "level_old": "level",
        "day_preference_old": "day_preference"
    }

    booking_to_modify, error_return = retrieve_matching_bookings(bookings, mapping_old_to_db, normalized_slots)
    if booking_to_modify is None:
        return error_return

    # Validate day_preference_new on course_activity_new
    course_new = normalized_slots.get("course_activity_new")
    day_new = normalized_slots.get("day_preference_new")
    is_valid, allowed_days = validate_day_preference_on_course(course_new, day_new)
    if not is_valid:
        return {
            "status": "error",
            "message": f"'{day_new}' is not valid for '{course_new}' (allowed: {', '.join(allowed_days)})",
            "slots": normalized_slots
        }

    # Check new values
    new_keys = ["course_activity_new", "target_age_new", "level_new", "day_preference_new"]
    missing_new = [k for k in new_keys if not normalized_slots.get(k)]
    if missing_new:
        return {
            "status": "success",
            "message": f"Missing: {', '.join(missing_new)}",
            "slots": normalized_slots,
            "matching_booking": booking_to_modify
        }

    # All new values present and valid
    return {
        "status": "success",
        "message": f"Fullfilled modification + {user_key}",
        "slots": normalized_slots,
        "matching_booking": booking_to_modify
    }


def query_modify_book_spa(slots, slots_to_validate, user):
    if not user:
        return {
            "status": "error",
            "message": "Missing: user"
        }

    user_key = get_user_key(user.get("name"), user.get("surname"))
    if user_key not in USERS_DB:
        return {
            "status": "error",
            "message": f"Not found user in DB: {user_key}"
        }

    bookings = USERS_DB[user_key].get("booked_spa", [])
    if not bookings:
        return {
            "status": "error",
            "message": f"Not booked spa found in DB"
        }

    # Normalize old and new values
    normalized_slots = slot_normalization_spa(slots, slots_to_validate)

    # Check old values against DB
    mapping_old_to_db = {
        "date_old": "date",
        "time_old": "time",
        "people_count_old": "people_count"
    }

    booking_to_modify, error_return = retrieve_matching_bookings(bookings, mapping_old_to_db, normalized_slots)
    if booking_to_modify is None:
        return error_return

    # Validate new time slot
    if normalized_slots.get("time_new"):
        is_valid = validate_time_in_range(normalized_slots.get("time_new"))
        if not is_valid:
            return {
                "status": "error",
                "message": f"'{normalized_slots.get('time_new')}' not valid for 'spa' (allowed: {OPENING_HOURS['spa']['Mon-Sun']})",
                "slots": normalized_slots
            }

    # Check new values
    new_keys = ["date_new", "time_new", "people_count_new"]
    missing_new = [k for k in new_keys if not normalized_slots.get(k)]
    if missing_new:
        return {
            "status": "success",
            "message": f"Missing: {', '.join(missing_new)}",
            "slots": normalized_slots,
            "matching_booking": booking_to_modify
        }

    # All new values present and valid
    return {
        "status": "success",
        "message": f"Fullfilled modification + {user_key}",
        "slots": normalized_slots,
        "matching_booking": booking_to_modify
    }


def query_buy_equipment(slots, slots_to_validate):
    # Normalize slots
    item = slots_to_validate.get("item").lower().strip() if slots.get("item") else None
    color = slots_to_validate.get("color").lower().strip() if slots.get("color") else None
    size = slots_to_validate.get("size").upper().strip() if slots.get("size") else None
    brand = slots_to_validate.get("brand", "").lower().strip() if slots.get("brand") else None
    normalize_slots = {
        "item": item,
        "color": color,
        "size": size,
        "brand": brand
    }

    if not item or item not in SHOP_INVENTORY:
        return {
            "status": "error",
            "message": f"Missing: item (available: {', '.join(SHOP_INVENTORY.keys())})",
            "slots": normalize_slots
        }

    product = SHOP_INVENTORY[item]

    # Brand check (if provided)
    if brand and "brand" in product and brand != product["brand"].lower():
        return {
            "status": "error",
            "message": f"Brand not available (allowed: {product['brand']})",
            "slots": normalize_slots
        }

    # Color check (if provided)
    if color:
        if "colors" not in product:
            return {
                "status": "error",
                "message": "Color options not available",
                "slots": normalize_slots
            }
        if color not in product["colors"]:
            return {
                "status": "error",
                "message": f"Color not available (allowed: {product['colors']})",
                "slots": normalize_slots
            }

    # Size check (if provided)
    if size:
        if "sizes" not in product:
            return {
                "status": "error",
                "message": "Size options not available",
                "slots": normalize_slots
            }
        if size not in product["sizes"]:
            return {
                "status": "error",
                "message": f"Size not available (allowed: {product['sizes']})",
                "slots": normalize_slots
            }

    # Success
    return {
        "status": "success",
        "message": f"Fullfilled: price €{product['price']:.2f}",
        "slots": normalize_slots
    }


def query_report_lost_item(slots, slots_to_validate, user):
    if not user:
        return {
            "status": "error",
            "message": "Missing user"
        }

    user_key = get_user_key(user.get("name"), user.get("surname"))
    if user_key not in USERS_DB:
        return {
            "status": "error",
            "message": "Not found user in DB"
        }

    # Normalize input slots
    normalized_slots = slot_normalization_lost_item(slots, slots_to_validate)

    # Required fields for a complete report
    required_keys = ["item", "item_color", "location", "date_lost"]
    missing = [k for k in required_keys if not normalized_slots.get(k)]
    if missing:
        return {
            "status": "success",
            "message": f"Missing values: {', '.join(missing)}",
            "slots": normalized_slots
        }

    lost_items = USERS_DB[user_key].get("lost_items", [])

    # Check for duplicate report
    for lost in lost_items:
        all_match = True
        for key in required_keys:
            if normalized_slots.get(key).lower() != lost.get(key, "").lower():
                all_match = False
                break

        if all_match:
            return {
                "status": "error",
                "message": "Overlap: identical report",
                "slots": normalized_slots
            }

    # New valid report
    return {
        "status": "success",
        "message": "Fullfilled report lost item",
        "slots": normalized_slots
    }


class MockDatabase:
    def __init__(self):
        pass

    def query_database(self, intent, slots, slots_to_validate, active_task, user=None):
        """
        Perform data normalization and database query / validation based on the intent and slots.

        Parameters:
            intent (str): the intent of the current task (e.g., 'book_course')
            slots (dict): all the current slots for this intent
            slots_to_validate (list): subset of slot keys that need validation
            active_task (dict): current active task details
            user (dict, optional): user profile (e.g., {'name': 'Mario', 'surname': 'Rossi'})

        Returns:
            dict: result of the database query/validation
        """
        print(f"[DB] Querying for intent: {intent} | Slots: {slots}")

        # 1. ASK OPENING HOURS
        if intent == "ask_opening_hours":
            return query_opening_hours(slots)

        # 2. ASK PRICING
        elif intent == "ask_pricing":
            return query_pricing(slots)

        # 3. ASK RULES
        elif intent == "ask_rules":
            return query_rules(slots)

        # 4. USER IDENTIFICATION
        elif intent == "user_identification":
            user_result = query_user_identification(slots)

            if user_result["status"] == "success":
                if active_task.get("intent") == "book_course":
                    return query_book_course(slots, slots_to_validate, user)
                elif active_task.get("intent") == "book_spa":
                    return query_book_spa(slots, slots_to_validate, user)
                elif active_task.get("intent") == "modify_course_booking":
                    return query_modify_book_course(slots, slots_to_validate, user)
                elif active_task.get("intent") == "modify_spa_booking":
                    return query_modify_book_spa(slots, slots_to_validate, user)
            return user_result

        # 5. BOOK COURSE
        elif intent == "book_course":
            return query_book_course(slots, slots_to_validate, user)

        # 6. BOOK SPA
        elif intent == "book_spa":
            return query_book_spa(slots, slots_to_validate, user)

        # 7. MODIFY COURSE BOOKING
        elif intent == "modify_course_booking":
            return query_modify_book_course(slots, slots_to_validate, user)

        # 8. MODIFY SPA BOOKING
        elif intent == "modify_spa_booking":
            return query_modify_book_spa(slots, slots_to_validate, user)

        # 9. BUY EQUIPMENT
        elif intent == "buy_equipment":
            return query_buy_equipment(slots, slots_to_validate)

        # 10. REPORT LOST ITEM
        elif intent == "report_lost_item":
            return query_report_lost_item(slots, slots_to_validate, user)

        # Default
        return {"status": "error", "message": "Unknown intent"}
