import copy
import json
import logging
from typing import Any

from prompts.nlg_prompt import (
    FLAG_RULES,
    INTENT_PROMPTS,
    NLG_COMPATIBLE_BASE_PROMPT,
    NLG_QWEN_BASE_PROMPT,
)


logger = logging.getLogger(__name__)

INTENT_TRANSLATIONS = {
    "ask_pricing": "prices and costs",
    "book_course": "booking a course",
    "book_spa": "booking the spa",
    "buy_equipment": "purchasing equipment",
    "ask_rules": "the facility rules",
    "ask_opening_hours": "the opening hours",
    "report_lost_item": "your lost item",
    "modify_booked_course": "modifying your course",
    "modify_booked_spa": "modifying your spa booking",
}


class NLG:
    """Generates final natural-language responses from DM actions and dialogue states."""

    def __init__(self, llm) -> None:
        self.llm = llm

    def _get_active_flags(self, dm_action_data: dict[str, Any]) -> list[str]:
        flags = []

        if dm_action_data.get("step_by_step_mode"):
            flags.append("step_by_step_mode")
        if dm_action_data.get("is_multitask"):
            flags.append("is_multitask")
        if dm_action_data.get("is_second_response"):
            flags.append("is_second_response")
        if dm_action_data.get("queue_recovery"):
            flags.append("queue_recovery")

        return flags

    def _get_active_flag_instructions(self, dm_action_data: dict[str, Any]) -> list[str]:
        active_flags = self._get_active_flags(dm_action_data)
        instructions = []

        for flag in active_flags:
            if flag == "is_multitask" and "is_second_response" in active_flags:
                continue

            if flag == "queue_recovery":
                raw_intent = dm_action_data.get("recovered_intent", "the previous topic")
                intent_name = INTENT_TRANSLATIONS.get(raw_intent, "your previous request")
                instructions.append(FLAG_RULES[flag].format(recovered_intent=intent_name))
            else:
                instructions.append(FLAG_RULES[flag])

        return instructions

    def _get_base_prompt(self) -> str:
        if self._uses_qwen_chat_format():
            return NLG_QWEN_BASE_PROMPT

        return NLG_COMPATIBLE_BASE_PROMPT

    def _build_system_content(self, dialogue_state: dict[str, Any]) -> str:
        prompt_parts = [self._get_base_prompt()]
        current_intent = dialogue_state.get("intent", "default")
        intent_dict = INTENT_PROMPTS.get(current_intent, {})

        if "rules" in intent_dict:
            prompt_parts.append(intent_dict["rules"].strip())

        prompt_parts.append("\nEXAMPLES:")

        if "examples" in intent_dict and "default" in intent_dict["examples"]:
            prompt_parts.append("- SPECIFIC DOMAIN EXAMPLE:")
            prompt_parts.append(intent_dict["examples"]["default"].strip())

        prompt_parts.append("\n--- END OF GENERAL INSTRUCTIONS & EXAMPLES ---")

        system_content = "\n".join(prompt_parts).strip()

        if not self._uses_qwen_chat_format():
            system_content = system_content.replace("FINAL SYSTEM COMMAND:", "FINAL INSTRUCTION BLOCK:")

        return system_content

    def _build_final_command(self, dm_action_data: dict[str, Any], dialogue_state: dict[str, Any]) -> str:
        current_intent = dialogue_state.get("intent", "default")
        flag_instructions = self._get_active_flag_instructions(dm_action_data)

        if current_intent == "user_identification" and dm_action_data.get("is_multitask"):
            flag_instructions = [flag for flag in flag_instructions if "MULTITASK (FIRST PART)" not in flag]
            flag_instructions.append(
                "- MULTITASK (FIRST PART): You are just acknowledging the user's name before answering their actual question in the next step. "
                "You MUST ONLY greet the user briefly, for example 'Hi Mario.', and STOP. Do NOT ask 'How can I help you?' or add any other text."
            )

        command_parts = [
            "CURRENT DIALOGUE STATE:",
            json.dumps(dialogue_state, indent=2),
            "",
            "CURRENT DM INSTRUCTION:",
            json.dumps(dm_action_data, indent=2),
        ]

        if flag_instructions:
            command_parts.extend(["", "CRITICAL ACTIVE FLAGS:", *flag_instructions])

        return "\n".join(command_parts).strip()

    def _get_model_name(self) -> str:
        return str(getattr(self.llm, "model_name", "")).lower()

    def _uses_qwen_chat_format(self) -> bool:
        return "qwen" in self._get_model_name()

    def _format_history_as_text(self, history_messages: list[dict[str, str]]) -> str:
        if not history_messages:
            return "No recent conversation history."

        lines = []

        for message in history_messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            lines.append(f"{role.upper()}: {content}")

        return "\n".join(lines)

    def _build_qwen_messages(
        self,
        system_content: str,
        final_command: str,
        history_messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": system_content}]

        if history_messages:
            messages.extend(history_messages)

        messages.append({"role": "system", "content": final_command})
        return messages

    def _build_compatible_messages(
        self,
        system_content: str,
        final_command: str,
        history_messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        history_text = self._format_history_as_text(history_messages)

        user_content = "\n\n".join([
            "RECENT CONVERSATION HISTORY:",
            history_text,
            "",
            "CRITICAL INSTRUCTIONS FOR THE NEXT ANSWER:",
            final_command,
            "",
            "Generate only the next assistant response.",
        ])

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    def _build_messages(
        self,
        system_content: str,
        final_command: str,
        history_messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if self._uses_qwen_chat_format():
            return self._build_qwen_messages(system_content, final_command, history_messages)

        return self._build_compatible_messages(system_content, final_command, history_messages)

    def predict(self, dm_action_data: dict[str, Any], dialogue_state: dict[str, Any], history) -> str:
        system_content = self._build_system_content(dialogue_state)
        final_command = self._build_final_command(dm_action_data, dialogue_state)
        history_messages = history.get_last_n_messages(4)

        messages = self._build_messages(system_content, final_command, history_messages)

        logger.debug("NLG model-specific format for %s", self._get_model_name() or "unknown_model")
        return self.llm.generate(messages=messages, max_new_tokens=256).strip()

    def _apply_response_flags(self, nba_list: list[dict[str, Any]], step_by_step_mode: bool) -> None:
        """Inject response-level flags before generating one or more answers."""
        if step_by_step_mode and nba_list:
            logger.debug("NLG: setting step-by-step mode on the main NBA.")
            nba_list[0]["step_by_step_mode"] = True

        if len(nba_list) > 1:
            logger.debug("NLG: setting multitask mode on all NBAs.")
            for nba in nba_list:
                nba["is_multitask"] = True

    def _build_masked_history(self, global_history, active_segments: list[str], current_index: int, final_responses: list[str]):
        """Hide unrelated target segments while generating each partial response."""
        from state.history import History

        temp_history = History()
        temp_history.messages = copy.deepcopy(global_history.messages)

        if active_segments and len(active_segments) > 1:
            last_message = temp_history.messages[-1]["content"]
            other_segments = [segment for index, segment in enumerate(active_segments) if index != current_index]

            for segment in other_segments:
                last_message = last_message.replace(segment, "").strip()

            temp_history.messages[-1]["content"] = last_message

        if final_responses:
            temp_history.add_message("assistant", " ".join(final_responses))

        return temp_history

    def generate_multi_response(self, nba_list: list[dict[str, Any]], ds_list: list[dict[str, Any]], active_segments: list[str], global_history, step_by_step_mode: bool = False) -> str:
        final_responses = []

        self._apply_response_flags(nba_list, step_by_step_mode)

        for index, nba in enumerate(nba_list):
            if index > 0:
                nba["is_second_response"] = True

            temp_history = self._build_masked_history(global_history, active_segments, index, final_responses)
            response = self.predict(nba, ds_list[index], temp_history)

            logger.debug("NLG response for intent %s: %s", index, response)
            final_responses.append(response)

        return " ".join(final_responses)
