import json
import copy
from prompts.nlg_prompt import (
    NLG_BASE_PROMPT,
    INTENT_PROMPTS,
    FLAG_RULES,
    GLOBAL_SCENARIO_EXAMPLES
)
import logging
logger = logging.getLogger(__name__)


class NLG:
    def __init__(self, llm):
        self.llm = llm

    def _get_active_flag_instructions(self, dm_action_data: dict) -> list:
        active_flags = []

        if dm_action_data.get("step_by_step_mode"):
            active_flags.append("step_by_step_mode")
        if dm_action_data.get("is_multitask"):
            active_flags.append("is_multitask")
        if dm_action_data.get("is_second_response"):
            active_flags.append("is_second_response")
        if dm_action_data.get("queue_recovery"):
            active_flags.append("queue_recovery")

        flag_instructions = []

        for flag in active_flags:
            if flag == "is_multitask" and "is_second_response" in active_flags:
                continue

            if flag == "queue_recovery":
                intent_translations = {
                    "ask_pricing": "prices and costs",
                    "book_course": "booking a course",
                    "book_spa": "booking the spa",
                    "buy_equipment": "purchasing equipment",
                    "ask_rules": "the facility rules",
                    "ask_opening_hours": "the opening hours",
                    "report_lost_item": "your lost item",
                    "modify_booked_course": "modifying your course",
                    "modify_booked_spa": "modifying your spa booking"
                }

                raw_intent = dm_action_data.get("recovered_intent", "the previous topic")
                intent_name = intent_translations.get(raw_intent, "your previous request")
                flag_instructions.append(FLAG_RULES[flag].format(recovered_intent=intent_name))
            else:
                flag_instructions.append(FLAG_RULES[flag])

        return flag_instructions

    def predict(self, dm_action_data: dict, dialogue_state: dict, history) -> str:
        # ... [IL CODICE ESISTENTE RIMANE UGUALE] ...
        prompt_parts = [NLG_BASE_PROMPT]

        current_intent = dialogue_state.get("intent", "default")
        intent_dict = INTENT_PROMPTS.get(current_intent, {})

        if "rules" in intent_dict:
            prompt_parts.append(intent_dict["rules"].strip())

        prompt_parts.append("\nEXAMPLES:")

        if "examples" in intent_dict and "default" in intent_dict["examples"]:
            prompt_parts.append("- SPECIFIC DOMAIN EXAMPLE:")
            prompt_parts.append(intent_dict["examples"]["default"].strip())

        prompt_parts.append("\n--- END OF GENERAL INSTRUCTIONS & EXAMPLES ---")

        system_content = "\n".join(prompt_parts)

        dm_str = json.dumps(dm_action_data, indent=2)
        ds_str = json.dumps(dialogue_state, indent=2)

        flag_instructions = self._get_active_flag_instructions(dm_action_data)

        final_command_parts = [
            "CURRENT DIALOGUE STATE:",
            ds_str,
            "",
            "CURRENT DM INSTRUCTION:",
            dm_str
        ]

        # Special case for user_identification on multitask
        if current_intent == "user_identification" and dm_action_data.get("is_multitask"):
            # Rimuoviamo la regola standard del multitask (che cerca l'enriched_data) per evitare conflitti
            flag_instructions = [flag for flag in flag_instructions if "MULTITASK (FIRST PART)" not in flag]
            
            # Aggiungiamo un override perentorio
            flag_instructions.append(
                "- MULTITASK (FIRST PART): You are just acknowledging the user's name before answering their actual question in the next step. You MUST ONLY greet the user briefly (e.g., 'Hi Mario.') and STOP. Do NOT ask 'How can I help you?' or add any other text."
            )

        if flag_instructions:
            final_command_parts.extend([
                "",
                "CRITICAL ACTIVE FLAGS:",
                *[f"{instruction}" for instruction in flag_instructions]
            ])

        final_command = "\n".join(final_command_parts)
        messages = [{"role": "system", "content": system_content.strip()}]

        hist_msgs = history.get_last_n_messages(4)
        if hist_msgs:
            messages.extend(hist_msgs)

        messages.append({"role": "system", "content": final_command.strip()})

        return self.llm.generate(
            messages=messages,
            max_new_tokens=256
        ).strip()

    # ==========================================================
    # NUOVO METODO: Gestisce tutto il batch e il mascheramento
    # ==========================================================
    def generate_multi_response(self, nba_list: list, ds_list: list, active_segments: list, global_history, step_by_step_mode: bool = False) -> str:
        from state.history import History
        final_responses = []

        # --- INIEZIONE FLAG (Gestita internamente dall'NLG) ---
        if step_by_step_mode and len(nba_list) > 0:
            logger.debug("NLG: Router indicated discarded info. Setting 'step_by_step_mode' flag in main NBA.")
            nba_list[0]["step_by_step_mode"] = True

        if len(nba_list) > 1:
            logger.debug("NLG: Multiple NBAs present. Setting 'is_multitask' flag to adjust response style.")
            for nba in nba_list:
                nba["is_multitask"] = True
        # ------------------------------------------------------

        for i in range(len(nba_list)):
            if i > 0:
                nba_list[i]["is_second_response"] = True

            # Creiamo una copia della history
            temp_history = History()
            # Usiamo deepcopy per non alterare i dizionari originali quando modifichiamo il testo
            temp_history.messages = copy.deepcopy(global_history.messages)

            # MASKING: Nascondiamo i segmenti degli altri intenti
            if active_segments and len(active_segments) > 1:
                other_segments_text = [seg for j, seg in enumerate(active_segments) if j != i]
                last_msg = temp_history.messages[-1]["content"]
                for other_seg in other_segments_text:
                    last_msg = last_msg.replace(other_seg, "").strip()
                temp_history.messages[-1]["content"] = last_msg

            # Aggiungiamo la risposta precedente se stiamo processando il secondo intento
            if final_responses:
                temp_history.add_message("assistant", " ".join(final_responses))

            # Chiamata al predict singolo
            resp = self.predict(nba_list[i], ds_list[i], temp_history)
            logger.debug("NLG Response for intent %s: %s", i, resp)
            final_responses.append(resp)

        return " ".join(final_responses)