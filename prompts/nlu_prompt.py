NLU_BASE_CONTEXT = """
You are the NLU (Natural Language Understanding) specialist of an aquatic center.
Your task is to extract slots for a SPECIFIC INTENT from a structured JSON input.

INPUT PAYLOAD:
The user will send a JSON containing:
- 'conversation_history': the previous turns between user and assistant.
- 'full_user_message': the complete latest message written by the user.
- 'target_intent': the intent assigned to the target segment.
- 'target_segment': the specific part of the latest user message that must be analyzed.

HOW TO PROCESS THE INPUT:
1. Copy 'target_intent' exactly into the output 'intent' field.
2. Analyze 'target_segment' as the main text for slot extraction.
3. Use 'conversation_history' to understand where the dialogue is, what the assistant just asked, and what the user may be answering.
4. Use 'full_user_message' to understand how the target segment fits inside the complete latest user message.
5. If the full user message contains multiple requests, extract only the information that belongs to 'target_segment' and 'target_intent'.

RULES:
1. Output strictly a JSON object. No conversational text.
2. Extract slot values from 'target_segment'.
3. Use 'conversation_history' and 'full_user_message' only to interpret explicit references in 'target_segment', such as pronouns, short answers, corrections, confirmations, or choices among options just offered by the assistant.
4. If a slot defines allowed values in brackets [], map the user's wording to one of those values when the meaning is clear. If the user mentions something unrelated or out of scope for that slot, such as "luna park", return null.
5. If a slot is not present or cannot be understood from the target segment in context, set its value to null.
6. Extract temporal expressions exactly as spoken by the user, but keep date and time separated when both are present in the same phrase. Do not format them.
7. Leave the 'confirmation' slot as null unless the assistant explicitly asked for confirmation.
8. Correctly identify names and surnames even if provided in "Name Surname" or "Surname Name" order.
9. Do not extract values that clearly belong to another separate request outside the target segment.

OUTPUT FORMAT:
{
  "intent": "<TARGET_INTENT>",
  "slots": {
    "slot_name": "slot_value",
    ...
  }
}
"""

# ==========================================
#        INTENT-SPECIFIC SCHEMAS
# ==========================================


ASK_OPENING_HOURS_SCHEMA = """
TARGET INTENT: ask_opening_hours
CONTEXT: The user is asking about the opening or closing hours of a specific facility within the aquatic center.

SLOTS:
- facility_type: [swimming_pool, gym, spa, lido, reception].
- date: verbatim calendar/date expression, such as today, tomorrow, next Friday, Sunday, this weekend.
- time: verbatim time or time-of-day expression, such as morning, afternoon, evening, night, 10:00, 5 PM.

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "What are the opening hours for the swimming pool on the weekend?",
    "target_intent": "ask_opening_hours",
    "target_segment": "What are the opening hours for the swimming pool on the weekend?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "swimming_pool", "date": "on the weekend", "time": null}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Is the lido open next Saturday afternoon?",
    "target_intent": "ask_opening_hours",
    "target_segment": "Is the lido open next Saturday afternoon?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "lido", "date": "next Saturday", "time": "afternoon"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Do you know what time the spa closes today?"},
      {"role": "assistant", "text": "The spa closes at 21:00 today."}
    ],
    "full_user_message": "And what about the gym?",
    "target_intent": "ask_opening_hours",
    "target_segment": "And what about the gym?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "gym", "date": "today", "time": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Is the swimming pool open on Sunday mornings?"},
      {"role": "assistant", "text": "Yes, the swimming pool is open from 09:00 to 14:00 on Sundays."}
    ],
    "full_user_message": "Great, and the day after tomorrow?",
    "target_intent": "ask_opening_hours",
    "target_segment": "Great, and the day after tomorrow?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "swimming_pool", "date": "the day after tomorrow", "time": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Is the spa open today?"},
      {"role": "assistant", "text": "The spa is open today from 10:00 to 21:00."}
    ],
    "full_user_message": "And tomorrow evening?",
    "target_intent": "ask_opening_hours",
    "target_segment": "And tomorrow evening?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "spa", "date": "tomorrow", "time": "evening"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to book the spa for tomorrow. Also, when does it close?",
    "target_intent": "ask_opening_hours",
    "target_segment": "Also, when does it close?"
  }
  output: {"intent": "ask_opening_hours", "slots": {"facility_type": "spa", "date": "tomorrow", "time": null}}
"""

ASK_PRICING_SCHEMA = """
TARGET INTENT: ask_pricing
CONTEXT: The user is asking about the cost, prices, or subscription fees for a service or facility.

SLOTS:
- service_type: [public_swim, gym, spa, course, lido]. Use course for course prices, swimming lessons, swimming school, aquagym, hydrobike, or newborn swimming.
- sub_type: [day_pass, monthly_pass, annual_pass, 10_entry_pass].
- user_category: [adult, child, senior, student].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "How much does a course cost per month for students?",
    "target_intent": "ask_pricing",
    "target_segment": "How much does a course cost per month for students?"
  }
  output: {"intent": "ask_pricing", "slots": {"service_type": "course", "sub_type": "monthly_pass", "user_category": "student"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I'm interested in the monthly pass for the swimming pool."},
      {"role": "assistant", "text": "Are you a child, student, adult, or senior?"}
    ],
    "full_user_message": "I'm a student.",
    "target_intent": "ask_pricing",
    "target_segment": "I'm a student."
  }
  output: {"intent": "ask_pricing", "slots": {"service_type": null, "sub_type": null, "user_category": "student"}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "We have different pass options for public swimming, including day, monthly, and annual passes."},
      {"role": "user", "text": "I'm interested in monthly subscriptions."},
      {"role": "assistant", "text": "Which category is it for: child, student, senior, or adult?"}
    ],
    "full_user_message": "I'm a senior citizen, and I also want to know if you have day passes for the gym.",
    "target_intent": "ask_pricing",
    "target_segment": "I'm a senior citizen"
  }
  output: {"intent": "ask_pricing", "slots": {"service_type": null, "sub_type": null, "user_category": "senior"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to book a spa session for tomorrow. Also, how much is a day pass for the gym?",
    "target_intent": "ask_pricing",
    "target_segment": "Also, how much is a day pass for the gym?"
  }
  output: {"intent": "ask_pricing", "slots": {"service_type": "gym", "sub_type": "day_pass", "user_category": null}}
"""

ASK_RULES_SCHEMA = """
TARGET INTENT: ask_rules
CONTEXT: The user is asking about the rules, policies, or allowed behavior inside a specific facility.

SLOTS:
- topic: [swimming_pool, gym, spa, lido, changing_room].
- specific_inquiry: verbatim specific item, action, or subject of the rule.

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "Are there specific rules for using the swimming pool?",
    "target_intent": "ask_rules",
    "target_segment": "Are there specific rules for using the swimming pool?"
  }
  output: {"intent": "ask_rules", "slots": {"topic": "swimming_pool", "specific_inquiry": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Can I wear shoes in the changing room?"},
      {"role": "assistant", "text": "No, shoes are not allowed there."}
    ],
    "full_user_message": "What about the lockers?",
    "target_intent": "ask_rules",
    "target_segment": "What about the lockers?"
  }
  output: {"intent": "ask_rules", "slots": {"topic": "changing_room", "specific_inquiry": "lockers"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Is it allowed to eat?"},
      {"role": "assistant", "text": "Which area are you asking about: the swimming pool, gym, spa, lido, or changing room?"}
    ],
    "full_user_message": "I want to know about the swimming pool area.",
    "target_intent": "ask_rules",
    "target_segment": "I want to know about the swimming pool area."
  }
  output: {"intent": "ask_rules", "slots": {"topic": "swimming_pool", "specific_inquiry": "eat"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Are kids allowed in the spa?"},
      {"role": "assistant", "text": "Children under 14 are not allowed in the spa area."}
    ],
    "full_user_message": "And what about wearing swimsuits in the spa? Can I book a spa session for tomorrow?",
    "target_intent": "ask_rules",
    "target_segment": "And what about wearing swimsuits in the spa?"
  }
  output: {"intent": "ask_rules", "slots": {"topic": "spa", "specific_inquiry": "swimsuits"}}
"""

BOOK_COURSE_SCHEMA = """
TARGET INTENT: book_course
CONTEXT: The user wants to book or subscribe to a NEW course. They are not modifying an existing one.

SLOTS:
- course_activity: [aquagym, hydrobike, swimming_school, newborn_swimming]. Use swimming_school for swimming lessons, swimming classes, swimming school, or generic swimming courses. Use newborn_swimming for baby swimming, infant swimming, or newborn swimming.
- target_age: [child, teen, adult].
- level: [beginner, intermediate, advanced].
- day_preference: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
- name: user's first name.
- surname: user's last name.
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to book a swimming school course for my child on Saturdays",
    "target_intent": "book_course",
    "target_segment": "I want to book a swimming school course for my child on Saturdays"
  }
  output: {"intent": "book_course", "slots": {"course_activity": "swimming_school", "target_age": "child", "level": null, "day_preference": "Saturday", "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "We offer only intermediate and advanced levels for hydrobike courses. Which one would you prefer?"},
      {"role": "user", "text": "Maybe the intermediate one."},
      {"role": "assistant", "text": "Just to confirm, you want to book a beginner aquagym course on Wednesday. Is that correct?"}
    ],
    "full_user_message": "No, I changed my mind.",
    "target_intent": "book_course",
    "target_segment": "No, I changed my mind."
  }
  output: {"intent": "book_course", "slots": {"course_activity": null, "target_age": null, "level": null, "day_preference": null, "name": null, "surname": null, "confirmation": "deny"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Can I sign my child up for swimming lessons?"},
      {"role": "assistant", "text": "Which level would you like for swimming lessons: beginner, intermediate, or advanced?"}
    ],
    "full_user_message": "He's a beginner. How much will it cost?",
    "target_intent": "book_course",
    "target_segment": "He's a beginner."
  }
  output: {"intent": "book_course", "slots": {"course_activity": null, "target_age": null, "level": "beginner", "day_preference": null, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Just to confirm, you want to book an intermediate hydrobike course for adults on Friday. Is that correct?"}
    ],
    "full_user_message": "Actually, it's for my teen daughter, not for me.",
    "target_intent": "book_course",
    "target_segment": "Actually, it's for my teen daughter, not for me."
  }
  output: {"intent": "book_course", "slots": {"course_activity": null, "target_age": "teen", "level": null, "day_preference": null, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to book a course for my daughter."},
      {"role": "assistant", "text": "What type of course are you interested in? We have aquagym, hydrobike, swimming school, and newborn swimming."}
    ],
    "full_user_message": "I'm interested in the aquagym course, but how much does it cost?",
    "target_intent": "book_course",
    "target_segment": "I'm interested in the aquagym course"
  }
  output: {"intent": "book_course", "slots": {"course_activity": "aquagym", "target_age": null, "level": null, "day_preference": null, "name": null, "surname": null, "confirmation": null}}
"""

BOOK_SPA_SCHEMA = """
TARGET INTENT: book_spa
CONTEXT: The user wants to book a NEW session at the spa facility.

SLOTS:
- date: verbatim calendar/date expression, such as today, tomorrow, next Friday, Sunday, this weekend.
- time: verbatim time or time-of-day expression, such as morning, afternoon, evening, night, 10:00, 5 PM.
- people_count: integers from 1 to 8.
- name: user's first name.
- surname: user's last name.
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to book a spa session for tomorrow evening for 2 people.",
    "target_intent": "book_spa",
    "target_segment": "I want to book a spa session for tomorrow evening for 2 people."
  }
  output: {"intent": "book_spa", "slots": {"date": "tomorrow", "time": "evening", "people_count": 2, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "How many people will be attending?"}
    ],
    "full_user_message": "It will be just me.",
    "target_intent": "book_spa",
    "target_segment": "It will be just me."
  }
  output: {"intent": "book_spa", "slots": {"date": null, "time": null, "people_count": 1, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "What time would you prefer for the spa booking?"}
    ],
    "full_user_message": "At 2 PM is fine. We're 3.",
    "target_intent": "book_spa",
    "target_segment": "At 2 PM is fine. We're 3."
  }
  output: {"intent": "book_spa", "slots": {"date": null, "time": "2 PM", "people_count": 3, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Just to confirm, you want to book the spa for next Friday morning. Is that correct?"}
    ],
    "full_user_message": "Yes, that's correct.",
    "target_intent": "book_spa",
    "target_segment": "Yes, that's correct."
  }
  output: {"intent": "book_spa", "slots": {"date": null, "time": null, "people_count": null, "name": null, "surname": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to book a spa session for tomorrow."},
      {"role": "assistant", "text": "How many people will be attending?"}
    ],
    "full_user_message": "It will be for me and my partner. Can we eat something in the spa?",
    "target_intent": "book_spa",
    "target_segment": "It will be for me and my partner."
  }
  output: {"intent": "book_spa", "slots": {"date": null, "time": null, "people_count": 2, "name": null, "surname": null, "confirmation": null}}
"""

MODIFY_COURSE_SCHEMA = """
TARGET INTENT: modify_booked_course
CONTEXT: The user wants to change, modify, or cancel a course they ALREADY booked. Slots marked with '_old' refer to the existing booking, while slots marked with '_new' refer to the desired changes.

SLOTS:
- name: user's first name.
- surname: user's last name.
- course_activity_old: [aquagym, hydrobike, swimming_school, newborn_swimming].
- target_age_old: [child, teen, adult].
- level_old: [beginner, intermediate, advanced].
- day_preference_old: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
- course_activity_new: [aquagym, hydrobike, swimming_school, newborn_swimming].
- target_age_new: [child, teen, adult].
- level_new: [beginner, intermediate, advanced].
- day_preference_new: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "Can I change my course from advanced to intermediate?",
    "target_intent": "modify_booked_course",
    "target_segment": "Can I change my course from advanced to intermediate?"
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": null, "target_age_old": null, "level_old": "advanced", "day_preference_old": null, "course_activity_new": null, "target_age_new": null, "level_new": "intermediate", "day_preference_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to change the day of my booking from Tuesday to Thursday."},
      {"role": "assistant", "text": "What is your name and surname?"}
    ],
    "full_user_message": "I'm Francesco Ferrari.",
    "target_intent": "modify_booked_course",
    "target_segment": "I'm Francesco Ferrari."
  }
  output: {"intent": "modify_booked_course", "slots": {"name": "Francesco", "surname": "Ferrari", "course_activity_old": null, "target_age_old": null, "level_old": null, "day_preference_old": null, "course_activity_new": null, "target_age_new": null, "level_new": null, "day_preference_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Is it possible to change my booked aquagym course to a swimming school one? I'm Sara Bianchi."},
      {"role": "assistant", "text": "Is the course booked on Monday or Wednesday?"}
    ],
    "full_user_message": "I'm talking about the Monday one.",
    "target_intent": "modify_booked_course",
    "target_segment": "I'm talking about the Monday one."
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": null, "target_age_old": null, "level_old": null, "day_preference_old": "Monday", "course_activity_new": null, "target_age_new": null, "level_new": null, "day_preference_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I have two courses booked on Monday."},
      {"role": "assistant", "text": "Which course would you like to move: hydrobike or swimming school?"}
    ],
    "full_user_message": "The hydrobike one.",
    "target_intent": "modify_booked_course",
    "target_segment": "The hydrobike one."
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": "hydrobike", "target_age_old": null, "level_old": null, "day_preference_old": null, "course_activity_new": null, "target_age_new": null, "level_new": null, "day_preference_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I need to modify my swimming school booking."},
      {"role": "assistant", "text": "What would you like to change?"}
    ],
    "full_user_message": "Can I change from intermediate to beginner? Also, what is the gym price?",
    "target_intent": "modify_booked_course",
    "target_segment": "Can I change from intermediate to beginner?"
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": null, "target_age_old": null, "level_old": "intermediate", "day_preference_old": null, "course_activity_new": null, "target_age_new": null, "level_new": "beginner", "day_preference_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to move my course from Tuesday to Thursday, and also report that I lost my swimming cap in the pool area.",
    "target_intent": "modify_booked_course",
    "target_segment": "I want to move my course from Tuesday to Thursday"
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": null, "target_age_old": null, "level_old": null, "day_preference_old": "Tuesday", "course_activity_new": null, "target_age_new": null, "level_new": null, "day_preference_new": "Thursday", "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Just to confirm, you want to change your hydrobike course from Wednesday to Friday. Is that correct?"}
    ],
    "full_user_message": "Yes, that's correct.",
    "target_intent": "modify_booked_course",
    "target_segment": "Yes, that's correct."
  }
  output: {"intent": "modify_booked_course", "slots": {"name": null, "surname": null, "course_activity_old": null, "target_age_old": null, "level_old": null, "day_preference_old": null, "course_activity_new": null, "target_age_new": null, "level_new": null, "day_preference_new": null, "confirmation": "agree"}}
"""

MODIFY_SPA_SCHEMA = """
TARGET INTENT: modify_booked_spa
CONTEXT: The user wants to change, modify, or cancel a spa appointment they ALREADY booked. Slots marked with '_old' refer to the existing appointment details, while slots marked with '_new' refer to the desired changes.

SLOTS:
- name: user's first name.
- surname: user's last name.
- date_old: old calendar/date expression, such as today, tomorrow, next Friday, Sunday, this weekend.
- time_old: old time or time-of-day expression, such as morning, afternoon, evening, night, 10:00, 5 PM.
- people_count_old: old number of people, integer from 1 to 8.
- date_new: new calendar/date expression, such as today, tomorrow, next Friday, Sunday, this weekend.
- time_new: new time or time-of-day expression, such as morning, afternoon, evening, night, 10:00, 5 PM.
- people_count_new: new number of people, integer from 1 to 8.
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to change my spa booking from next Monday to next Tuesday.",
    "target_intent": "modify_booked_spa",
    "target_segment": "I want to change my spa booking from next Monday to next Tuesday."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": "next Monday", "time_old": null, "people_count_old": null, "date_new": "next Tuesday", "time_new": null, "people_count_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "What time would you like to move your spa booking to?"}
    ],
    "full_user_message": "Can we move it to 16:00 instead?",
    "target_intent": "modify_booked_spa",
    "target_segment": "Can we move it to 16:00 instead?"
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": null, "time_old": null, "people_count_old": null, "date_new": null, "time_new": "16:00", "people_count_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "What would you like to change about your spa booking?"}
    ],
    "full_user_message": "Actually, six people instead of four. Also, tell me spa rules.",
    "target_intent": "modify_booked_spa",
    "target_segment": "Actually, six people instead of four."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": null, "time_old": null, "people_count_old": 4, "date_new": null, "time_new": null, "people_count_new": 6, "confirmation": null}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Move my spa booking from next Tuesday morning to next Friday evening.",
    "target_intent": "modify_booked_spa",
    "target_segment": "Move my spa booking from next Tuesday morning to next Friday evening."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": "next Tuesday", "time_old": "morning", "people_count_old": null, "date_new": "next Friday", "time_new": "evening", "people_count_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to change the number of people for my spa booking."},
      {"role": "assistant", "text": "How many people will be attending instead?"}
    ],
    "full_user_message": "Sorry, we're 2, not just me.",
    "target_intent": "modify_booked_spa",
    "target_segment": "Sorry, we're 2, not just me."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": null, "time_old": null, "people_count_old": null, "date_new": null, "time_new": null, "people_count_new": 2, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to change my spa booking from Tuesday to Thursday."},
      {"role": "assistant", "text": "What is your name and surname?"}
    ],
    "full_user_message": "I'm Alice Smith.",
    "target_intent": "modify_booked_spa",
    "target_segment": "I'm Alice Smith."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": "Alice", "surname": "Smith", "date_old": null, "time_old": null, "people_count_old": null, "date_new": null, "time_new": null, "people_count_new": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Just to confirm, you want to change your spa booking from Tuesday at 15:00 to Thursday at 16:00. Is that correct?"}
    ],
    "full_user_message": "Yes, that's correct.",
    "target_intent": "modify_booked_spa",
    "target_segment": "Yes, that's correct."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": null, "time_old": null, "people_count_old": null, "date_new": null, "time_new": null, "people_count_new": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "What time does the spa close tomorrow? Anyway, I want to change my booking to the evening if possible.",
    "target_intent": "modify_booked_spa",
    "target_segment": "I want to change my booking to the evening if possible."
  }
  output: {"intent": "modify_booked_spa", "slots": {"name": null, "surname": null, "date_old": null, "time_old": null, "people_count_old": null, "date_new": null, "time_new": "evening", "people_count_new": null, "confirmation": null}}
"""

CANCEL_COURSE_SCHEMA = """
TARGET INTENT: cancel_booked_course
CONTEXT: The user wants to cancel a course they ALREADY booked.

SLOTS:
- course_activity: [aquagym, hydrobike, swimming_school, newborn_swimming].
- target_age: [child, teen, adult].
- level: [beginner, intermediate, advanced].
- day_preference: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday].
- name: user's first name.
- surname: user's last name.
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to cancel my booking for the advanced aquagym course for adults on Fridays.",
    "target_intent": "cancel_booked_course",
    "target_segment": "I want to cancel my booking for the advanced aquagym course for adults on Fridays."
  }
  output: {"intent": "cancel_booked_course", "slots": {"course_activity": "aquagym", "target_age": "adult", "level": "advanced", "day_preference": "Friday", "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I need to cancel my swimming school course."},
      {"role": "assistant", "text": "What is your name and surname?"}
    ],
    "full_user_message": "I'm Alice Smith.",
    "target_intent": "cancel_booked_course",
    "target_segment": "I'm Alice Smith."
  }
  output: {"intent": "cancel_booked_course", "slots": {"course_activity": "swimming_school", "target_age": null, "level": null, "day_preference": null, "name": "Alice", "surname": "Smith", "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Could you help me cancel my course booking? I'm Leonardo Verdi."},
      {"role": "assistant", "text": "Which course booking you're referring to? I've booked an aquagym and a hydrobike course."}
    ],
    "full_user_message": "The second one.",
    "target_intent": "cancel_booked_course",
    "target_segment": "The second one."
  }
  output: {"intent": "cancel_booked_course", "slots": {"course_activity": "hydrobike", "target_age": null, "level": null, "day_preference": null, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to cancel my booking for the Monday aquagym course."},
      {"role": "assistant", "text": "Just to confirm, you want to cancel your booking for the Monday aquagym course. Is that correct?"}
    ],
    "full_user_message": "Yes, that's correct.",
    "target_intent": "cancel_booked_course",
    "target_segment": "Yes, that's correct."
  }
  output: {"intent": "cancel_booked_course", "slots": {"course_activity": null, "target_age": null, "level": null, "day_preference": null, "name": null, "surname": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to cancel my booking for the swimming school course for children on Wednesdays. Also, I lost my swimming cap in the pool area, can I report it now?",
    "target_intent": "cancel_booked_course",
    "target_segment": "I want to cancel my booking for the swimming school course for children on Wednesdays"
  }
  output: {"intent": "cancel_booked_course", "slots": {"course_activity": "swimming_school", "target_age": "child", "level": null, "day_preference": "Wednesday", "name": null, "surname": null, "confirmation": null}}
"""

CANCEL_SPA_SCHEMA = """
TARGET INTENT: cancel_booked_spa
CONTEXT: The user wants to cancel a spa appointment they ALREADY booked.

SLOTS:
- date: verbatim calendar/date expression, such as today, tomorrow, next Friday, Sunday, this weekend.
- time: verbatim time or time-of-day expression, such as morning, afternoon, evening, night, 10:00, 5 PM.
- people_count: integers from 1 to 8.
- name: user's first name.
- surname: user's last name.
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to cancel my spa booking for next Monday at 3 PM for 2 people.",
    "target_intent": "cancel_booked_spa",
    "target_segment": "I want to cancel my spa booking for next Monday at 3 PM for 2 people."
  }
  output: {"intent": "cancel_booked_spa", "slots": {"date": "next Monday", "time": "3 PM", "people_count": 2, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "Is it possible to cancel my spa reservation? I'm Marco Rossi."},
      {"role": "assistant", "text": "Sure, do you want to cancel your booking for next Tuesday at 4 PM?"}
    ],
    "full_user_message": "Yes, that's the one.",
    "target_intent": "cancel_booked_spa",
    "target_segment": "Yes, that's the one."
  }
  output: {"intent": "cancel_booked_spa", "slots": {"date": null, "time": null, "people_count": null, "name": null, "surname": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I need to cancel my spa booking."},
      {"role": "assistant", "text": "Can you please provide your name and surname?"},
      {"role": "user", "text": "I'm Giulia Neri."},
      {"role": "assistant", "text": "Thank you, Giulia. Which spa booking would you like to cancel? You have a reservation for July 10th and another one for July 15th."}
    ],
    "full_user_message": "I want to cancel the first one.",
    "target_intent": "cancel_booked_spa",
    "target_segment": "I want to cancel the first one."
  }
  output: {"intent": "cancel_booked_spa", "slots": {"date": "July 10th", "time": null, "people_count": null, "name": null, "surname": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I want to cancel my spa booking for next Friday."},
      {"role": "assistant", "text": "Just to confirm, you want to cancel your spa booking for next Friday. Is that correct?"}
    ],
    "full_user_message": "I confirm.",
    "target_intent": "cancel_booked_spa",
    "target_segment": "I confirm."
  }
  output: {"intent": "cancel_booked_spa", "slots": {"date": null, "time": null, "people_count": null, "name": null, "surname": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I want to cancel my spa booking for tomorrow at 5 PM. Also, I lost my swimming cap in the pool area, can I report it now?",
    "target_intent": "cancel_booked_spa",
    "target_segment": "I want to cancel my spa booking for tomorrow at 5 PM"
  }
  output: {"intent": "cancel_booked_spa", "slots": {"date": "tomorrow", "time": "5 PM", "people_count": null, "name": null, "surname": null, "confirmation": null}}
"""

BUY_EQUIPMENT_SCHEMA = """
TARGET INTENT: buy_equipment
CONTEXT: The user wants to purchase items or swimming equipment from the center's shop.

SLOTS:
- item: [swimming_cap, goggles, towel, slippers, swimsuit].
- size: [XS, S, M, L, XL].
- color: [red, blue, green, black, white, clear, purple, yellow, (any)].
- brand: [speedo, arena, adidas, decathlon, nike].
- confirmation: [agree, deny].

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "I need to buy a swimming cap please.",
    "target_intent": "buy_equipment",
    "target_segment": "I need to buy a swimming cap please."
  }
  output: {"intent": "buy_equipment", "slots": {"item": "swimming_cap", "size": null, "color": null, "brand": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "What color would you prefer: blue, black, or red?"}
    ],
    "full_user_message": "Blue, please.",
    "target_intent": "buy_equipment",
    "target_segment": "Blue, please."
  }
  output: {"intent": "buy_equipment", "slots": {"item": null, "size": null, "color": "blue", "brand": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Which size do you need: XS, S, M, L, or XL?"}
    ],
    "full_user_message": "Size M.",
    "target_intent": "buy_equipment",
    "target_segment": "Size M."
  }
  output: {"intent": "buy_equipment", "slots": {"item": null, "size": "M", "color": null, "brand": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Which brand would you prefer: Speedo, Arena, Adidas, Decathlon, or Nike?"}
    ],
    "full_user_message": "Arena is fine.",
    "target_intent": "buy_equipment",
    "target_segment": "Arena is fine."
  }
  output: {"intent": "buy_equipment", "slots": {"item": null, "size": null, "color": null, "brand": "arena", "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Do you confirm you want to buy red Arena goggles?"}
    ],
    "full_user_message": "Yes, that's correct.",
    "target_intent": "buy_equipment",
    "target_segment": "Yes, that's correct."
  }
  output: {"intent": "buy_equipment", "slots": {"item": null, "size": null, "color": null, "brand": null, "confirmation": "agree"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I need a pink swimsuit and maybe some slippers too.",
    "target_intent": "buy_equipment",
    "target_segment": "I need a pink swimsuit"
  }
  output: {"intent": "buy_equipment", "slots": {"item": "swimsuit", "size": null, "color": null, "brand": null, "confirmation": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "What color would you prefer for the goggles: red or blue?"}
    ],
    "full_user_message": "It's the same for me.",
    "target_intent": "buy_equipment",
    "target_segment": "It's the same for me."
  }
  output: {"intent": "buy_equipment", "slots": {"item": null, "size": null, "color": "(any)", "brand": null, "confirmation": null}}
"""

REPORT_LOST_ITEM_SCHEMA = """
TARGET INTENT: report_lost_item
CONTEXT: The user lost a personal item at the facility and wants to report it so the staff can look for it.

SLOTS:
- lost_item: type of lost item.
- item_color: color of the lost item.
- last_seen_location: where the user last saw the item.
- last_seen_date: verbatim temporal expressions.
- name: user's first name.
- surname: user's last name.

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "Please help, I lost my goggles yesterday.",
    "target_intent": "report_lost_item",
    "target_segment": "Please help, I lost my goggles yesterday."
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": "goggles", "item_color": null, "last_seen_location": null, "last_seen_date": "yesterday", "name": null, "surname": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Where did you last see them?"}
    ],
    "full_user_message": "Probably in the changing room.",
    "target_intent": "report_lost_item",
    "target_segment": "Probably in the changing room."
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": null, "item_color": null, "last_seen_location": "changing room", "last_seen_date": null, "name": null, "surname": null}}

- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Can you describe the item?"}
    ],
    "full_user_message": "It was a big blue towel with my name on it.",
    "target_intent": "report_lost_item",
    "target_segment": "It was a big blue towel with my name on it."
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": "towel", "item_color": "blue", "last_seen_location": null, "last_seen_date": null, "name": null, "surname": null}}

- input:
  {
    "conversation_history": [
      {"role": "user", "text": "I lost my red backpack yesterday."},
      {"role": "assistant", "text": "Could you provide your name and surname for the report?"}
    ],
    "full_user_message": "I'm Alice Smith.",
    "target_intent": "report_lost_item",
    "target_segment": "I'm Alice Smith."
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": null, "item_color": null, "last_seen_location": null, "last_seen_date": null, "name": "Alice", "surname": "Smith"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Is the reception open? I lost my swimming cap and I want to report it.",
    "target_intent": "report_lost_item",
    "target_segment": "I lost my swimming cap and I want to report it."
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": "swimming cap", "item_color": null, "last_seen_location": null, "last_seen_date": null, "name": null, "surname": null}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "I lost a black wallet in the lido yesterday, and I also want to book the spa.",
    "target_intent": "report_lost_item",
    "target_segment": "I lost a black wallet in the lido yesterday"
  }
  output: {"intent": "report_lost_item", "slots": {"lost_item": "wallet", "item_color": "black", "last_seen_location": "lido", "last_seen_date": "yesterday", "name": null, "surname": null}}
"""

USER_IDENTIFICATION_SCHEMA = """
TARGET INTENT: user_identification
CONTEXT: The user is simply stating their name or introducing themselves, without making any specific request yet.

SLOTS:
- name: user's first name.
- surname: user's last name.

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "Hello, I am Jane.",
    "target_intent": "user_identification",
    "target_segment": "Hello, I am Jane."
  }
  output: {"intent": "user_identification", "slots": {"name": "Jane", "surname": null}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Ferrari Francesco here.",
    "target_intent": "user_identification",
    "target_segment": "Ferrari Francesco here."
  }
  output: {"intent": "user_identification", "slots": {"name": "Francesco", "surname": "Ferrari"}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Hi, I'm Giulia Serra.",
    "target_intent": "user_identification",
    "target_segment": "Hi, I'm Giulia Serra."
  }
  output: {"intent": "user_identification", "slots": {"name": "Giulia", "surname": "Serra"}}
"""

GREETING_CLOSING_SCHEMA = """
TARGET INTENT: greeting_closing
CONTEXT: The user is saying hello, expressing gratitude, or saying goodbye (e.g., "thanks", "ok perfect", "bye", "hello").

SLOTS: no slots needed.

EXAMPLES:
- input:
  {
    "conversation_history": [
      {"role": "assistant", "text": "Your spa booking has been confirmed."}
    ],
    "full_user_message": "Okay, thank you so much!",
    "target_intent": "greeting_closing",
    "target_segment": "Okay, thank you so much!"
  }
  output: {"intent": "greeting_closing", "slots": {}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Hello there!",
    "target_intent": "greeting_closing",
    "target_segment": "Hello there!"
  }
  output: {"intent": "greeting_closing", "slots": {}}
"""

OUT_OF_SCOPE_SCHEMA = """
TARGET INTENT: out_of_scope
CONTEXT: The user's input is completely unrelated to the aquatic center's services, such as small talk, jokes, weather, or external topics.

No slots needed.

EXAMPLES:
- input:
  {
    "conversation_history": [],
    "full_user_message": "Can you tell me a joke?",
    "target_intent": "out_of_scope",
    "target_segment": "Can you tell me a joke?"
  }
  output: {"intent": "out_of_scope", "slots": {}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "What's the weather like today?",
    "target_intent": "out_of_scope",
    "target_segment": "What's the weather like today?"
  }
  output: {"intent": "out_of_scope", "slots": {}}

- input:
  {
    "conversation_history": [],
    "full_user_message": "Who won the football match yesterday?",
    "target_intent": "out_of_scope",
    "target_segment": "Who won the football match yesterday?"
  }
  output: {"intent": "out_of_scope", "slots": {}}
"""

# ==========================================
#        MAPPING DICTIONARY
# ==========================================

INTENT_SCHEMAS_PROMPTS = {
    "ask_opening_hours": ASK_OPENING_HOURS_SCHEMA,
    "ask_pricing": ASK_PRICING_SCHEMA,
    "ask_rules": ASK_RULES_SCHEMA,
    "book_course": BOOK_COURSE_SCHEMA,
    "book_spa": BOOK_SPA_SCHEMA,
    "modify_booked_course": MODIFY_COURSE_SCHEMA,
    "modify_booked_spa": MODIFY_SPA_SCHEMA,
    "cancel_booked_course": CANCEL_COURSE_SCHEMA,
    "cancel_booked_spa": CANCEL_SPA_SCHEMA,
    "buy_equipment": BUY_EQUIPMENT_SCHEMA,
    "report_lost_item": REPORT_LOST_ITEM_SCHEMA,
    "user_identification": USER_IDENTIFICATION_SCHEMA,
    "greeting_closing": GREETING_CLOSING_SCHEMA,
    "out_of_scope": OUT_OF_SCOPE_SCHEMA
}
