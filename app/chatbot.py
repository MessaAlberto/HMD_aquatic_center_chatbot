from components.router import Router
from components.NLU import NLU
from components.DM import DM
from components.NLG import NLG
from state.dialogue_state_tracker import StateTracker
from state.history import History
from database.db_controller import DBController
from state.task_queue import TaskQueue
from llm.loader import load_llm
import logging
logger = logging.getLogger(__name__)


class Chatbot:
    def __init__(self, model_name: str) -> None:
        self.llm = load_llm(model_name)

        self.router = Router(self.llm)
        self.NLU = NLU(self.llm)
        self.DM = DM(self.llm)
        self.NLG = NLG(self.llm)

        self.dst = StateTracker()
        self.db_controller = DBController(self.dst)
        self.history = History()
        self.task_queue = TaskQueue()

        self.DONE_STATUSES = ["INFORM", "CONFIRMED", "ABORTED"]

    def reset_state(self) -> None:
        self.dst = StateTracker()
        self.db_controller = DBController(self.dst)
        self.history = History()
        self.task_queue = TaskQueue()

    def reset_all(self) -> None:
        self.reset_state()
        # Add DB reset here only if DBController has a specific method for it.
        # Example:
        # self.db_controller.reset()

    def _prepare_pipeline(self, nlu_result, target_dst, lenient=False):
        ds = target_dst.update(nlu_result)
        user_prof = self.dst.get_user_profile()

        db_res = self.db_controller.resolve_state(ds, user_prof, lenient=lenient, target_dst=target_dst)
        is_done = db_res and db_res.get("status") in self.DONE_STATUSES

        logger.debug("DST after update: {ds}")
        logger.debug("DB Result: {db_res}")
        logger.debug("Is intent done? {'Yes' if is_done else 'No'}\n")

        return ds.copy(), db_res, is_done

    def _disambiguate_intents(self, nlu_results):
        curr_intent = self.dst.ds["intent"]

        if curr_intent and nlu_results[0].get("intent") == nlu_results[1].get("intent") == curr_intent:
            logger.debug("Parallel instances of the same intent! Using slot-scoring to disambiguate.")

            def score_nlu(nlu_res, current_slots):
                score = 0
                for k, v in nlu_res.get("slots", {}).items():
                    if v is not None:
                        if current_slots.get(k) is None:
                            score += 1
                        elif str(current_slots.get(k)).lower() != str(v).lower():
                            score -= 2
                return score

            score0 = score_nlu(nlu_results[0], self.dst.ds["slots"])
            score1 = score_nlu(nlu_results[1], self.dst.ds["slots"])

            if score1 > score0:
                return nlu_results[1], nlu_results[0]
            return nlu_results[0], nlu_results[1]

        elif curr_intent and nlu_results[1].get("intent") == curr_intent:
            logger.debug("Current dialogue state intent '{curr_intent}' matches second NLU result intent.")
            return nlu_results[1], nlu_results[0]

        logger.debug("Treating first NLU result {nlu_results[0].get('intent')} as main intent.")
        return nlu_results[0], nlu_results[1]

    # =========================================================================
    # METODI DI SUPPORTO (Estratti dal chat_loop per pulizia del codice)
    # =========================================================================

    def _process_single_intent(self, nlu_result, segment_text):
        logger.debug("Single intent detected. Processing normally.")
        resumed_queued_task = self.task_queue.consume_if_resumed(nlu_result)
        
        if resumed_queued_task:
            logger.debug("User resumed queued task. Clearing queue.")

        main_task = {"nlu": nlu_result, "segment": segment_text}
        main_task["ds"], main_task["db_res"], main_task["is_done"] = self._prepare_pipeline(
            main_task["nlu"], self.dst, lenient=False)

        logger.debug("DST after update: {main_task['ds']}")
        logger.debug("DB Result: {main_task['db_res']}")
        logger.debug("Main intent done: {main_task['is_done']}\n")

        main_task["nba"] = self.DM.predict_batch(
            [{"dialogue_state": main_task["ds"], "db_result": main_task["db_res"]}])[0]
        
        logger.debug("DM NBA: {main_task['nba']}")

        should_recover_queue = main_task["is_done"] and not resumed_queued_task
        
        return [main_task], main_task["is_done"], False, main_task["nlu"].get("intent"), None, should_recover_queue

    def _process_double_intent(self, nlu_results, segments):
        logger.debug("Two intents detected. Applying disambiguation heuristic.")
        main_nlu, sec_nlu = self._disambiguate_intents(nlu_results)

        main_segment = segments[0]["segment"] if nlu_results[0] is main_nlu else segments[1]["segment"]
        sec_segment = segments[0]["segment"] if nlu_results[0] is sec_nlu else segments[1]["segment"]

        main_task = {"nlu": main_nlu, "segment": main_segment}
        sec_task = {"nlu": sec_nlu, "segment": sec_segment}

        main_task["ds"], main_task["db_res"], main_task["is_done"] = self._prepare_pipeline(
            main_task["nlu"], self.dst, lenient=False)

        sec_dst = StateTracker()
        sec_dst.user_profile = self.dst.user_profile.copy()
        sec_task["ds"], sec_task["db_res"], sec_task["is_done"] = self._prepare_pipeline(
            sec_task["nlu"], sec_dst, lenient=True)
        self.dst.user_profile.update(sec_dst.user_profile)

        nbas = self.DM.predict_batch([
            {"dialogue_state": main_task["ds"], "db_result": main_task["db_res"]},
            {"dialogue_state": sec_task["ds"], "db_result": sec_task["db_res"]}
        ])
        main_task["nba"], sec_task["nba"] = nbas[0], nbas[1]

        tasks_to_execute = []
        
        # NUOVO BLOCCO: Se entrambi sono done, diamo la precedenza assoluta al saluto
        if main_task["is_done"] and sec_task["is_done"]:
            if sec_task["nlu"].get("intent") == "user_identification":
                logger.debug("Both intents done. Forcing 'user_identification' to be the first response.")
                tasks_to_execute = [sec_task, main_task]
            else:
                logger.debug("Both intents done. Maintaining original order.")
                tasks_to_execute = [main_task, sec_task]
                
        elif not main_task["is_done"] and sec_task["is_done"]:
            logger.debug("Secondary intent is done but main is not. Prioritizing secondary.")
            tasks_to_execute = [sec_task, main_task]
            
        elif not main_task["is_done"] and not sec_task["is_done"]:
            logger.debug("Neither intent is done. Prioritizing main intent and queuing secondary.")
            self.task_queue.store(
                nlu_result=sec_task["nlu"],
                segment=sec_task["segment"],
                dialogue_state=sec_task["ds"]
            )
            main_task["nba"]["step_by_step_mode"] = True
            tasks_to_execute = [main_task]
            
        else:
            logger.debug("Main intent prioritized in response.")
            tasks_to_execute = [main_task, sec_task]

        return tasks_to_execute, main_task["is_done"], sec_task["is_done"], main_task["nlu"].get("intent"), sec_task["ds"], False

    def _update_dst_and_queue(self, main_is_done, sec_is_done, main_intent_name, sec_ds, should_recover_queue, nba_list):
        if main_is_done:
            logger.debug("Main intent is done.")
            self.dst.complete_task()
            logger.debug("Completed task for main intent: {main_intent_name}")
            
            if should_recover_queue and self.task_queue.is_active():
                queued_intent = self.task_queue.pop_intent()
                logger.debug("Recovering queued intent '{queued_intent}' into dialogue state.")
                self.dst.ds["intent"] = queued_intent
                if nba_list:
                    nba_list[0]["queue_recovery"] = True
                    nba_list[0]["recovered_intent"] = queued_intent

        if sec_ds is not None and main_is_done and not sec_is_done:
            logger.debug("Main intent is done but secondary is not. Updating DST to reflect completion of main intent while preserving secondary intent.")
            self.dst.ds = sec_ds.copy()

    def reply(self, user_input: str) -> str:
        command = user_input.strip().lower()

        if command in ["exit", "quit", "stop"]:
            return "Goodbye!"

        if command == "reset_state":
            self.reset_state()
            return "Conversation state reset."

        if command == "reset":
            self.reset_all()
            return "Conversation state and database state reset."

        self.history.add_message("user", user_input)

        logger.debug("====== Router & NLU Processing ======")
        excluded_segments = self.task_queue.get_excluded_segment()
        active_intent = self.dst.ds.get("intent")

        router_output = self.router.predict(
            self.history,
            excluded_segments=excluded_segments,
            active_intent=active_intent,
        )

        logger.debug("Router Output: %s", router_output)

        if isinstance(router_output, dict):
            segments = router_output.get("segments", [])
            step_by_step_mode = router_output.get("step_by_step_mode", False)
        else:
            segments = router_output[:2]
            step_by_step_mode = len(router_output) > 2

        logger.debug(
            "Parsed Router Segments: %s, Discarded Info Flag: %s",
            segments,
            step_by_step_mode,
        )

        nlu_results = self.NLU.predict_batch(segments, self.history)
        logger.debug("NLU Batch Results: %s", nlu_results)

        logger.debug("====== Intent Processing ======")

        if len(nlu_results) == 1:
            tasks_to_execute, main_is_done, sec_is_done, main_intent_name, sec_ds, should_recover = (
                self._process_single_intent(nlu_results[0], segments[0]["segment"])
            )
        elif len(nlu_results) == 2:
            tasks_to_execute, main_is_done, sec_is_done, main_intent_name, sec_ds, should_recover = (
                self._process_double_intent(nlu_results, segments)
            )
        else:
            return "I could not understand the request."

        nba_list = [task["nba"] for task in tasks_to_execute]
        ds_list = [task["ds"] for task in tasks_to_execute]
        active_segments_list = [task["segment"] for task in tasks_to_execute]

        logger.debug(
            "Tasks to Execute: %s, Main Intent Done: %s, Secondary Intent Done: %s",
            len(tasks_to_execute),
            main_is_done,
            sec_is_done,
        )

        logger.debug("====== DST Update and Queue Management ======")

        self._update_dst_and_queue(
            main_is_done,
            sec_is_done,
            main_intent_name,
            sec_ds,
            should_recover,
            nba_list,
        )

        combined_response = self.NLG.generate_multi_response(
            nba_list=nba_list,
            ds_list=ds_list,
            active_segments=active_segments_list,
            global_history=self.history,
            step_by_step_mode=step_by_step_mode,
        )

        logger.debug("Bot: %s", combined_response)

        self.history.add_message("assistant", combined_response)

        return combined_response

    # =========================================================================
    # CORE LOOP
    # =========================================================================

    def chat_loop(self):
        print("Chatbot is ready! Type 'exit' to quit.")

        while True:
            logger.debug("\n-------------------- new turn -------------------------")
            user_input = input("You: ")
            command = user_input.strip().lower()

            response = self.reply(user_input)

            print(f"Bot: {response}")

            if command in ["exit", "quit", "stop"]:
                break