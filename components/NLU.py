import json
import re

from prompts.nlu_prompt import (
    NLU_BASE_CONTEXT,
    INTENT_SCHEMAS_PROMPTS
)
import logging
logger = logging.getLogger(__name__)


class NLU:
    def __init__(self, llm):
        self.llm = llm

    def parse_llm_json(self, text: str, fallback_intent: str) -> dict:
        try:
            parsed = json.loads(text)
            return parsed
        except Exception:
            pattern = r"```json\s*(.*?)\s*```"
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            return {"intent": fallback_intent, "slots": {}}

    def predict_batch(self, segments: list, history) -> list:
        messages_batch = []

        for seg in segments:
            target_intent = seg.get("intent", "out_of_scope")
            segment_text = seg.get("segment", "")

            schema_and_examples = INTENT_SCHEMAS_PROMPTS.get(
                target_intent,
                INTENT_SCHEMAS_PROMPTS["out_of_scope"]
            )

            system_prompt = f"{NLU_BASE_CONTEXT}\n\n{schema_and_examples}"
            messages = [{"role": "system", "content": system_prompt.strip()}]

            # Otteniamo la history strutturata (ignoriamo last_utt perché usiamo il segment_text)
            conv_history, last_utterance = history.get_json_history_and_last_utterance(n=4)

            # Costruiamo il payload specifico per il NLU
            payload = {
                "conversation_history": conv_history,
                "full_user_message": last_utterance,
                "target_intent": target_intent,
                "target_segment": segment_text
            }

            messages.append({"role": "user", "content": json.dumps(payload, indent=2)})

            # final_command = (
            #     "CRITICAL: You must extract slot values EXCLUSIVELY from the 'target_segment'. "
            #     "Use the 'conversation_history' ONLY as background context to resolve pronouns.\n\n"
            #     "INPUT DATA:\n"
            #     f"{json.dumps(payload, indent=2)}"
            # )
            
            # messages.append({"role": "user", "content": final_command})

            messages_batch.append(messages)

        nlu_outputs = self.llm.generate_batch(
            messages_batch=messages_batch,
            max_new_tokens=256
        )

        results = []
        for i, out in enumerate(nlu_outputs):
            target_intent = segments[i].get("intent", "out_of_scope")

            parsed_data = self.parse_llm_json(out, target_intent)
            parsed_data["intent"] = target_intent

            logger.debug("NLU Segment %s Raw Output: %s", i, out)
            logger.debug("NLU Segment %s Parsed: %s", i, parsed_data)

            results.append(parsed_data)

        return results
