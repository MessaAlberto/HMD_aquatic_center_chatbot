# utils/prompts.py

# System context
SYSTEM_PROMPT = "You are a helpful and precise university assistant."

# NLU Prompt: Enforce strictly JSON output
NLU_INTENT_PROMPT = """
Analyze the user input and conversation history.
Identify the intent and extract relevant entities (slots).
Output EXCLUSIVELY in JSON format.

Supported Intents: [find_classroom, lecture_schedule, professor_contacts, out_of_scope]

Example Output:
{{"intent": "find_classroom", "slots": {{"day": "Monday", "time": "14:00"}}}}

History: {history}
User Input: {input}
JSON Output:
"""

# NLG Prompt: Generates the final natural language response
NLG_RESPONSE_PROMPT = """
You are a polite assistant.
Required Action: {action}
Database Data (if any): {db_data}

Generate a natural response for the user in English.
Response:
"""