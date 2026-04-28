# NLU_CONTEXT = """
# You are the official AI assistant of an aquatic center.
# You are the NLU (Natural Language Understanding) module in a conversational system.

# GOAL: Extract the user's intent and relevant slots from their input.

# INPUT:
#   - You will receive a user input and the conversation history.
#   - User input format:
#     {"role": "user", "content": "..."}
#   - Conversation history format:
#     [
#       {"role": "system", "content": "..."},
#       {"role": "user", "content": "..."},
#       {"role": "system", "content": "..."},
#     ]

# OUTPUT:
#   - A JSON object:
#     {
#       "intent": "extracted_intent",
#       "slots": {
#         "slot_name": "slot_value",
#         ...
#       }
#     }

# RULES:
# 1. Do not invent intents or slots.
# 2. If a slot value is not provided, return it as null.
# 3. Return only the JSON object.
# 4. Use the conversation history to resolve any ambiguities in the user input.
# 5. Extract temporal expressions (dates and times) verbatim from the user input exactly as spoken (e.g., "tomorrow", "next Monday", "in the evening"). Do not convert or format them.
# 6. Extract slot values EXCLUSIVELY from the current user input. Use the conversation history ONLY to understand context and resolve intents, but NEVER copy slot values from the history into the output JSON.
# """

NLU_CONTEXT = """
You are the official AI assistant of an aquatic center.
You are the NLU (Natural Language Understanding) module in a conversational system.

GOAL: Extract the user's intent and relevant slots from their latest input.

INPUT:
  - You are participating in a multi-turn chat.
  - You will read the conversation history to understand the context.
  - Your extraction task applies ONLY to the LAST user message in the conversation.

OUTPUT:
  - A JSON object:
    {
      "intent": "extracted_intent",
      "slots": {
        "slot_name": "slot_value",
        ...
      }
    }

RULES:
1. Output strictly the JSON object, without any additional text.
2. Do not hallucinate or invent intents, slots, or values.
3. If a slot defines allowed values in brackets [], you MUST use exactly one of those terms.
4. If a slot value is not explicitly provided in the current user input, return it as null.
5. Use the conversation history ONLY to understand context and resolve the intent. NEVER extract or copy slot values from the history.
6. Extract temporal expressions (dates and times) verbatim exactly as spoken. Do not convert or format them.
7. Leave the "confirmation" slot as null unless the user explicitly agrees or denies in the current input.
"""

# relative_time NOT CONVERTED, allowed/description everywhere
NLU_PROMPT_V1 = """
SUPPORTED INTENTS AND SLOTS:
1. "ask_opening_hours":
  - Description: User is asking about the opening hours.
  - Slots:
    - facility_type: types of facilities. Allowed values: [swimming_pool, gym, spa, lido, reception].
    - date: verbatim temporal expressions related to dates. Examples: "tomorrow", "next Monday", "on 12th June".
    - time: verbatim temporal expressions related to times. Examples: "in the morning", "at night".

2. "ask_pricing":
  - Description: User is asking about the pricing.
  - Slots:
    - facility_type: types of facilities. Allowed values: [swimming_pool, gym, spa, course, lido].
    - sub_type: specific type of subscription. Allowed values: [day_pass, monthly_pass, annual_pass, 10_entry_pass].
    - user_category: category of user. Allowed values: [adult, child, senior, student].

3. "ask_rules":
  - Description: User is asking about the rules or specific policies of the aquatic center.
  - Slots:
    - topic: specific topic of rules. Allowed values: [swimming_pool, gym, spa, lido, changing_room]
    - specific_inquiry: specific item, action, or subject of the rule. Examples: "shoes", "changing room".

4. "book_course":
  - Description: User wants to book a course.
  - Slots:
    - course_activity: type of course. Allowed values: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age: target age group for the course. Allowed values: [children, teens, adults].
    - level: skill level for the course. Allowed values: [beginner, intermediate, advanced].
    - day_preference: preferred day of the week. Allowed values: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - name: user's first name.
    - surname: user's last name.
    - confirmation: whether the user confirms the booking details. Allowed values: [agree, deny].

5. "book_spa":
  - Description: User wants to book a spa session.
  - Slots:
    - date: verbatim temporal expressions related to dates. Examples: "tomorrow", "next Monday", "on 12th June".
    - time: verbatim temporal expressions related to times. Examples: "in the morning", "at night".
    - people_count: number of people for the spa session. Allowed values: integers from 1 to 4.
    - name: user's first name.
    - surname: user's last name.
    - confirmation: whether the user confirms the booking details. Allowed values: [agree, deny].

6. "modify_booked_course":
  - Description: User wants to modify an already booked course.
  - Slots:
    - name: user's first name.
    - surname: user's last name.
    - course_activity_old: current type of course. Allowed values: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age_old: current target age group for the course. Allowed values: [children, teens, adults].
    - level_old: current skill level for the course. Allowed values: [beginner, intermediate, advanced].
    - day_preference_old: current preferred day of the week. Allowed values: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - course_activity_new: new type of course. Allowed values: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age_new: new target age group for the course. Allowed values: [children, teens, adults].
    - level_new: new skill level for the course. Allowed values: [beginner, intermediate, advanced].
    - day_preference_new: new preferred day of the week. Allowed values: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - confirmation: whether the user confirms the modification details. Allowed values: [agree, deny].

7. "modify_booked_spa":
  - Description: User wants to modify an already booked spa session.
  - Slots:
    - name: user's first name.
    - surname: user's last name.
    - date_old: current date of the spa session. Verbatim temporal expressions related to dates.
    - time_old: current time of the spa session. Verbatim temporal expressions related to times.
    - people_count_old: current number of people for the spa session. Allowed values: integers from 1 to 4.
    - date_new: new date of the spa session. Verbatim temporal expressions related to dates.
    - time_new: new time of the spa session. Verbatim temporal expressions related to times.
    - people_count_new: new number of people for the spa session. Allowed values: integers from 1 to 4.
    - confirmation: whether the user confirms the modification details. Allowed values: [agree, deny].

8. "buy_equipment":
  - Description: User wants to buy equipment from the aquatic center.
  - Slots:
    - item: type of equipment. Allowed values: [swimming_cap, goggles, towel, slippers, swimsuit].
    - size: size of the equipment if relevant. Allowed values: [XS, S, M, L, XL].
    - color: color of the equipment if relevant. Allowed values: [red, blue, green, black, white, clear, purple, yellow].
    - brand: brand of the equipment if relevant. Allowed values: [speedo, arena, adidas, decathlon, nike].
    - confirmation: whether the user confirms the purchase details. Allowed values: [agree, deny].

9. "report_lost_item":
  - Description: User wants to report a lost item.
  - Slots:
    - item: type of lost item.
    - item_color: color of the lost item if relevant.
    - last_seen_location: where the user last saw the item.
    - last_seen_date: when the user last saw the item.
    - name: user's first name.
    - surname: user's last name.

10. "user_identification":
  - Description: User provides their identity information.
  - Slots:
    - name: user's first name.
    - surname: user's last name.

11. "out_of_scope":
  - Description: User input does not fit any of the above intents.
  - No slots.
"""


# removed descr, relative_time NOT CONVERTED, allowed everywhere
NLU_PROMPT_V2 = """
SUPPORTED INTENTS AND SLOTS:
1. "ask_opening_hours":
  - Slots:
    - facility_type: [swimming_pool, gym, spa, lido, reception].
    - date: verbatim temporal expressions.
    - time: verbatim temporal expressions.

2. "ask_pricing":
  - Slots:
    - facility_type: [swimming_pool, gym, spa, course, lido].
    - sub_type: [day_pass, monthly_pass, annual_pass, 10_entry_pass].
    - user_category: [adult, child, senior, student].

3. "ask_rules":
  - Slots:
    - topic: [swimming_pool, gym, spa, lido, changing_room]
    - specific_inquiry: verbatim specific item, action, or subject of the rule.

4. "book_course":
  - Slots:
    - course_activity: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age: [children, teens, adults].
    - level: [beginner, intermediate, advanced].
    - day_preference: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - name: user's first name.
    - surname: user's last name.
    - confirmation: [agree, deny].

5. "book_spa":
  - Slots:
    - date: verbatim temporal expressions.
    - time: verbatim temporal expressions.
    - people_count: integers from 1 to 4.
    - name: user's first name.
    - surname: user's last name.
    - confirmation: [agree, deny].

6. "modify_booked_course":
  - Slots:
    - name: user's first name.
    - surname: user's last name.
    - course_activity_old: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age_old: [children, teens, adults].
    - level_old: [beginner, intermediate, advanced].
    - day_preference_old: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - course_activity_new: [aquagym, hydrobike, swimming_school, newborn_swimming].
    - target_age_new: [children, teens, adults].
    - level_new: [beginner, intermediate, advanced].
    - day_preference_new: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
    - confirmation: [agree, deny].

7. "modify_booked_spa":
  - Slots:
    - name: user's first name.
    - surname: user's last name.
    - date_old: Verbatim temporal expressions.
    - time_old: Verbatim temporal expressions.
    - people_count_old: integers from 1 to 4.
    - date_new: Verbatim temporal expressions.
    - time_new: Verbatim temporal expressions.
    - people_count_new: integers from 1 to 4.
    - confirmation: [agree, deny].

8. "buy_equipment":
  - Slots:
    - item: [swimming_cap, goggles, towel, slippers, swimsuit].
    - size: [XS, S, M, L, XL].
    - color: [red, blue, green, black, white, clear, purple, yellow].
    - brand: [speedo, arena, adidas, decathlon, nike].
    - confirmation: [agree, deny].

9. "report_lost_item":
  - Slots:
    - item: type of lost item.
    - item_color: color of the lost item.
    - last_seen_location: where the user last saw the item.
    - last_seen_date: verbatim temporal expressions.
    - name: user's first name.
    - surname: user's last name.

10. "user_identification":
  - Slots:
    - name: user's first name.
    - surname: user's last name.

11. "out_of_scope":
  - No slots.
"""

ONE_SHOT_EXAMPLE = """
EXAMPLE:
- input: "What time does the spa open in the morning?"
  output:
  {
    "intent": "ask_opening_hours",
    "slots": {
      "facility_type": "spa",
      "date": null,
      "time": "morning"
    }
  }

- history:
  [
    {"role": "user", "content": "I'm interested in the monthly pass for the swimming pool"},
    {"role": "system", "content": "Are you a student, adult, senior?"}
  ]
  input: "I'm a student"
  output:
  {
    "intent": "ask_pricing",
    "slots": {
      "facility_type": null,
      "sub_type": null,
      "user_category": "student"
    }
  }

- history:
  [
    {"role": "user", "content": "Can I wear shoes in the changing room?"},
    {"role": "system", "content": "No, wearing shoes in the changing room is not allowed."}
  ]
  input: "What about the swimming pool area?"
  output:
  {
    "intent": "ask_rules",
    "slots": {
      "topic": "swimming_pool",
      "specific_inquiry": null,
    }
  }

- input: "I want to book a swimming school course for my child on Saturdays"
  output:
  {
    "intent": "book_course",
    "slots": {
      "course_activity": "swimming_school",
      "target_age": "children",
      "level": null,
      "day_preference": "Saturday",
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- input: "I want to book a spa session for tomorrow evening for 2 people"
  output:
  {
    "intent": "book_spa",
    "slots": {
      "date": "tomorrow",
      "time": "evening",
      "people_count": 2,
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I want to book a spa session for tomorrow evening for 2 people."},
    {"role": "system", "content": "Great, do you want to confirm the booking details: a spa session for tomorrow evening for 2 people?"}
  ]
  input: "Yes, please confirm the booking."
  output:
  {
    "intent": "book_spa",
    "slots": {
      "date": null,
      "time": null,
      "people_count": null,
      "name": null,
      "surname": null,
      "confirmation": "agree"
    }
  }

- history:
  [
    {"role": "user", "content": "I want to modify day of my booked course"},
    {"role": "system", "content": "Sure, can you please provide your name and surname?"}
  ]
  input: "My name is John Doe"
  output:
  {
    "intent": "modify_booked_course",
    "slots": {
      "name": "John",
      "surname": "Doe",
      "course_activity_old": null,
      "target_age_old": null,
      "level_old": null,
      "day_preference_old": null,
      "course_activity_new": null,
      "target_age_new": null,
      "level_new": null,
      "day_preference_new": null,
      "confirmation": null
    }
  }

- input: "Change my Tuesday aquagym course to Thursday, please"
  output:
  {
    "intent": "modify_booked_course",
    "slots": {
      "name": null,
      "surname": null,
      "course_activity_old": "aquagym",
      "target_age_old": null,
      "level_old": null,
      "day_preference_old": "Tuesday",
      "course_activity_new": null,
      "target_age_new": null,
      "level_new": null,
      "day_preference_new": "Thursday",
      "confirmation": null
    }
  }

- input: "I want change my spa booking from next Monday to next Tuesday"
  output:
  {
    "intent": "modify_booked_spa",
    "slots": {
      "name": null,
      "surname": null,
      "date_old": "next Monday",
      "time_old": null,
      "people_count_old": null,
      "date_new": "next Tuesday",
      "time_new": null,
      "people_count_new": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I need to buy a swimming cap please."},
    {"role": "system", "content": "Sure, which size do you need? We have S, M, L, XL."}
  ]
  input: "I need a size M."
  output:
  {
    "intent": "buy_equipment",
    "slots": {
      "item": null,
      "size": "M",
      "color": null,
      "brand": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "Please help, I lost my shoes in the gym this morning."},
    {"role": "system", "content": "I'm sorry to hear that. Do you remember the color of the shoes?"}
  ]
  input: "I think they were black."
  output:
  {
    "intent": "report_lost_item",
    "slots": {
      "item": null,
      "item_color": "black",
      "last_seen_location": null,
      "last_seen_date": null,
      "name": null,
      "surname": null
    }
  }

- input: "Hello, I am Jane"
  output:
  {
    "intent": "user_identification",
    "slots": {
      "name": "Jane",
      "surname": null
    }
  }

- input: "Can you tell me a joke?"
  output:
  {
    "intent": "out_of_scope",
    "slots": {}
  }
"""


FEW_SHOT_EXAMPLE = """
EXAMPLE:
- input: "What are the opening hours for the swimming pool in the weekend?"
  output:
  {
    "intent": "ask_opening_hours",
    "slots": {
      "facility_type": "swimming_pool",
      "date": "in the weekend",
      "time": null
    }
  }

- input: "What time does the spa open in the morning?"
  output:
  {
    "intent": "ask_opening_hours",
    "slots": {
      "facility_type": "spa",
      "date": null,
      "time": "morning"
    }
  }

- history:
  [
    {"role": "user", "content": "What are the opening hours for the swimming pool?"},
    {"role": "system", "content": "The swimming pool is open from 6am to 10pm every day."}
  ]
  input: "And the gym?"
  output:
  {
    "intent": "ask_opening_hours",
    "slots": {
      "facility_type": "gym",
      "date": null,
      "time": null
    }
  }

- input: "How much does a single entry for the swimming pool cost?"
  output:
  {
    "intent": "ask_pricing",
    "slots": {
      "facility_type": "swimming_pool",
      "sub_type": "day_pass",
      "user_category": null
    }
  }

- input: "How much does a course cost per month for students?"
  output:
  {
    "intent": "ask_pricing",
    "slots": {
      "facility_type": null,
      "sub_type": "monthly_pass",
      "user_category": "student"
    }
  }

- history:
  [
    {"role": "user", "content": "I'm interested in the monthly pass for the swimming pool"},
    {"role": "system", "content": "Are you a student, adult, senior?"}
  ]
  input: "I'm a student"
  output:
  {
    "intent": "ask_pricing",
    "slots": {
      "facility_type": null,
      "sub_type": null,
      "user_category": "student"
    }
  }

- input: "Are there specific rules for using the swimming pool?"
  output:
  {
    "intent": "ask_rules",
    "slots": {
      "topic": "swimming_pool",
      "specific_inquiry": null
    }
  }

- input: "Can I wear shoes in the changing room?"
  output:
  {
    "intent": "ask_rules",
    "slots": {
      "topic": "changing_room",
      "specific_inquiry": "shoes"
    }
  }

- input: "Is it allowed to smoke in the lido area?"
  output:
  {
    "intent": "ask_rules",
    "slots": {
      "topic": "lido",
      "specific_inquiry": "smoke"
    }
  }

- history:
  [
    {"role": "user", "content": "Can I wear shoes in the changing room?"},
    {"role": "system", "content": "No, wearing shoes in the changing room is not allowed."}
  ]
  input: "What about the swimming pool area?"
  output:
  {
    "intent": "ask_rules",
    "slots": {
      "topic": "swimming_pool",
      "specific_inquiry": null,
    }
  }

- input: "I want to book a swimming school course for my child on Saturdays"
  output:
  {
    "intent": "book_course",
    "slots": {
      "course_activity": "swimming_school",
      "target_age": "children",
      "level": null,
      "day_preference": "Saturday",
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I want to attend the hydrobike course on Wednesdays."},
    {"role": "system", "content": "Great choice! Can you please provide your preferred day of the week for the course?"}
  ]
  input: "On Wednesdays it would be better for me."
  output:
  {
    "intent": "book_course",
    "slots": {
      "course_activity": null,
      "target_age": null,
      "level": null,
      "day_preference": "Wednesday",
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I'm a beginner"},
    {"role": "system", "content": "Thanks for the info! Do you confirm that you want to book a beginner aquagym course for adults on Wednesdays?"}
  ]
  input: "No, I change my mind"
  output:
  {
    "intent": "book_course",
    "slots": {
      "course_activity": null,
      "target_age": null,
      "level": null,
      "day_preference": null,
      "name": null,
      "surname": null,
      "confirmation": "deny"
    }
  }

- history:
  [
    {"role": "user", "content": "On Fridays it would be better for me"},
    {"role": "system", "content": "Got it, let's recap the details: you want to book a swimming school course for your (adult), level advanced on Fridays. Can you please confirm?"}
  ]
  input: "Actually, it's for my teen daughter, not for me."
  output:
  {
    "intent": "book_course",
    "slots": {
      "course_activity": null,
      "target_age": "teen",
      "level": null,
      "day_preference": null,
      "name": null,
      "surname": null,
      "confirmation": "deny"
    }
  }

- input: "I want to book a spa session for tomorrow evening for 2 people"
  output:
  {
    "intent": "book_spa",
    "slots": {
      "date": "tomorrow",
      "time": "evening",
      "people_count": 2,
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "At 10am, please."},
    {"role": "system", "content": "Great, how many people will be attending the spa session?"}
  ]
  input: "It will be just me."
  output:
  {
    "intent": "book_spa",
    "slots": {
      "date": null,
      "time": null,
      "people_count": 1,
      "name": null,
      "surname": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I want to book a spa session for tomorrow evening for 2 people."},
    {"role": "system", "content": "Great, do you want to confirm the booking details: a spa session for tomorrow evening for 2 people?"}
  ]
  input: "Yes, please confirm the booking."
  output:
  {
    "intent": "book_spa",
    "slots": {
      "date": null,
      "time": null,
      "people_count": null,
      "name": null,
      "surname": null,
      "confirmation": "agree"
    }
  }

- input: "It's too difficult for me to attend the advanced course, can I change to a lower level?"
  output:
  {
    "intent": "modify_booked_course",
    "slots": {
      "name": null,
      "surname": null,
      "course_activity_old": null,
      "target_age_old": null,
      "level_old": "advanced",
      "day_preference_old": null,
      "course_activity_new": null,
      "target_age_new": null,
      "level_new": "intermediate",
      "day_preference_new": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I want to modify day of my booked course"},
    {"role": "system", "content": "Sure, can you please provide your name and surname?"}
  ]
  input: "My name is John Doe"
  output:
  {
    "intent": "modify_booked_course",
    "slots": {
      "name": "John",
      "surname": "Doe",
      "course_activity_old": null,
      "target_age_old": null,
      "level_old": null,
      "day_preference_old": null,
      "course_activity_new": null,
      "target_age_new": null,
      "level_new": null,
      "day_preference_new": null,
      "confirmation": null
    }
  }

- input: "Change my Tuesday aquagym course to Thursday, please"
  output:
  {
    "intent": "modify_booked_course",
    "slots": {
      "name": null,
      "surname": null,
      "course_activity_old": "aquagym",
      "target_age_old": null,
      "level_old": null,
      "day_preference_old": "Tuesday",
      "course_activity_new": null,
      "target_age_new": null,
      "level_new": null,
      "day_preference_new": "Thursday",
      "confirmation": null
    }
  }

- input: "I want change my spa booking from next Monday to next Tuesday"
  output:
  {
    "intent": "modify_booked_spa",
    "slots": {
      "name": null,
      "surname": null,
      "date_old": "next Monday",
      "time_old": null,
      "people_count_old": null,
      "date_new": "next Tuesday",
      "time_new": null,
      "people_count_new": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I want change my spa booking from next Monday to next Tuesday."},
    {"role": "system", "content": "Sure, can you please provide your name and surname?"},
    {"role": "user", "content": "My name is Jane Smith"},
    {"role": "system", "content": "Thank you, Jane. Can you please confirm that you want to change your spa booking from next Monday to next Tuesday?"}
  ]
  input: "Yes, that's correct."
  output:
  {
    "intent": "modify_booked_spa",
    "slots": {
      "name": null,
      "surname": null,
      "date_old": null,
      "time_old": null,
      "people_count_old": null,
      "date_new": null,
      "time_new": null,
      "people_count_new": null,
      "confirmation": "agree"
    }
  }

- input: "I need to buy a swimming cap please"
  output:
  {
    "intent": "buy_equipment",
    "slots": {
      "item": "swimming_cap",
      "size": null,
      "color": null,
      "brand": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "I need to buy a swimming cap please."},
    {"role": "system", "content": "Sure, which size do you need? We have S, M, L, XL."}
  ]
  input: "I need a size M."
  output:
  {
    "intent": "buy_equipment",
    "slots": {
      "item": null,
      "size": "M",
      "color": null,
      "brand": null,
      "confirmation": null
    }
  }

- history:
  [
    {"role": "user", "content": "Red goggles, please."},
    {"role": "system", "content": "Sure, do you confirm that you want to buy red Arena goggles?"}
  ]
  input: "Yes, that's correct."
  output:
  {
    "intent": "buy_equipment",
    "slots": {
      "item": null,
      "size": null,
      "color": null,
      "brand": null,
      "confirmation": "agree"
    }
  }

- input: "Please help, I lost my goggles yesterday"
  output:
  {
    "intent": "report_lost_item",
    "slots": {
      "item": "goggles",
      "item_color": null,
      "last_seen_location": null,
      "last_seen_date": "yesterday",
      "name": null,
      "surname": null
    }
  }

- history:
  [
    {"role": "user", "content": "Please help, I lost my shoes in the gym this morning."},
    {"role": "system", "content": "I'm sorry to hear that. Do you remember the color of the shoes?"}
  ]
  input: "I think they were black."
  output:
  {
    "intent": "report_lost_item",
    "slots": {
      "item": null,
      "item_color": "black",
      "last_seen_location": null,
      "last_seen_date": null,
      "name": null,
      "surname": null
    }
  }

- input: "Hello, I am Jane"
  output:
  {
    "intent": "user_identification",
    "slots": {
      "name": "Jane",
      "surname": null
    }
  }

- input: "John Doe here"
  output:
  {
    "intent": "user_identification",
    "slots": {
      "name": "John",
      "surname": "Doe"
    }
  }

- input: "Can you tell me a joke?"
  output:
  {
    "intent": "out_of_scope",
    "slots": {}
  }

- input: "Do you sell ice cream at the reception?"
  output:
  {
    "intent": "out_of_scope",
    "slots": {}
  }
"""