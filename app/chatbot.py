import logging
from typing import Any

from components.router import Router
from components.NLU import NLU
from components.DM import DM
from components.NLG import NLG
from database.db_controller import DBController
from llm.loader import load_llm
from state.dialogue_state_tracker import StateTracker
from state.history import History
from state.task_queue import TaskQueue


logger = logging.getLogger(__name__)

Task = dict[str, Any]


class Chatbot:
    """Orchestrates the full dialogue pipeline."""

    DONE_STATUSES = ("INFORM", "CONFIRMED", "ABORTED")

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

    def reset_state(self) -> None:
        """Reset the dialogue state while keeping the database unchanged."""
        self.dst = StateTracker()
        self.db_controller = DBController(self.dst)
        self.history = History()
        self.task_queue = TaskQueue()

    def reset_all(self) -> None:
        """Reset both the dialogue state and the database state."""
        self.reset_state()
        self.db_controller.reset_database()

    def _prepare_pipeline(self, nlu_result: dict[str, Any], target_dst: StateTracker, lenient: bool = False) -> tuple[dict[str, Any], dict[str, Any] | None, bool]:
        """Update the target DST and resolve the resulting state through the database."""
        dialogue_state = target_dst.update(nlu_result)
        user_profile = self.dst.get_user_profile()

        db_result = self.db_controller.resolve_state(
            dialogue_state, user_profile, lenient=lenient, target_dst=target_dst)
        is_done = bool(db_result and db_result.get("status") in self.DONE_STATUSES)

        logger.debug("DST after update: %s", dialogue_state)
        logger.debug("DB result: %s", db_result)
        logger.debug("Intent done: %s", is_done)

        return dialogue_state.copy(), db_result, is_done

    def _disambiguate_intents(self, nlu_results: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Select the main intent when the router returns two candidate segments."""
        current_intent = self.dst.ds["intent"]

        if current_intent and nlu_results[0].get("intent") == nlu_results[1].get("intent") == current_intent:
            logger.debug("Parallel instances of the same intent. Applying slot scoring.")

            def score_nlu(nlu_result: dict[str, Any], current_slots: dict[str, Any]) -> int:
                score = 0

                for slot_name, slot_value in nlu_result.get("slots", {}).items():
                    if slot_value is None:
                        continue

                    if current_slots.get(slot_name) is None:
                        score += 1
                    elif str(current_slots.get(slot_name)).lower() != str(slot_value).lower():
                        score -= 2

                return score

            score_0 = score_nlu(nlu_results[0], self.dst.ds["slots"])
            score_1 = score_nlu(nlu_results[1], self.dst.ds["slots"])

            if score_1 > score_0:
                return nlu_results[1], nlu_results[0]

            return nlu_results[0], nlu_results[1]

        if current_intent and nlu_results[1].get("intent") == current_intent:
            logger.debug("Current dialogue intent matches the second NLU result.")
            return nlu_results[1], nlu_results[0]

        logger.debug("Using the first NLU result as the main intent.")
        return nlu_results[0], nlu_results[1]

    def _process_single_intent(self, nlu_result: dict[str, Any], segment_text: str) -> tuple[list[Task], bool, bool, str | None, None, bool]:
        """Process a turn where the router identified a single intent."""
        logger.debug("Single intent detected.")

        resumed_queued_task = self.task_queue.consume_if_resumed(nlu_result)

        if resumed_queued_task:
            logger.debug("User resumed a queued task. Clearing queue.")

        main_task = {"nlu": nlu_result, "segment": segment_text}
        main_task["ds"], main_task["db_res"], main_task["is_done"] = self._prepare_pipeline(
            main_task["nlu"], self.dst, lenient=False)

        logger.debug("Main task DST: %s", main_task["ds"])
        logger.debug("Main task DB result: %s", main_task["db_res"])
        logger.debug("Main task done: %s", main_task["is_done"])

        main_task["nba"] = self.DM.predict_batch(
            [{"dialogue_state": main_task["ds"], "db_result": main_task["db_res"]}])[0]
        logger.debug("Main task NBA: %s", main_task["nba"])

        should_recover_queue = main_task["is_done"] and not resumed_queued_task

        return [main_task], main_task["is_done"], False, main_task["nlu"].get("intent"), None, should_recover_queue

    def _process_double_intent(self, nlu_results: list[dict[str, Any]], segments: list[dict[str, Any]]) -> tuple[list[Task], bool, bool, str | None, dict[str, Any] | None, bool]:
        """Process a turn where the router identified two intents."""
        logger.debug("Two intents detected. Applying disambiguation.")

        main_nlu, secondary_nlu = self._disambiguate_intents(nlu_results)

        main_segment = segments[0]["segment"] if nlu_results[0] is main_nlu else segments[1]["segment"]
        secondary_segment = segments[0]["segment"] if nlu_results[0] is secondary_nlu else segments[1]["segment"]

        main_task = {"nlu": main_nlu, "segment": main_segment}
        secondary_task = {"nlu": secondary_nlu, "segment": secondary_segment}

        main_task["ds"], main_task["db_res"], main_task["is_done"] = self._prepare_pipeline(
            main_task["nlu"], self.dst, lenient=False)

        secondary_dst = StateTracker()
        secondary_dst.user_profile = self.dst.user_profile.copy()
        secondary_task["ds"], secondary_task["db_res"], secondary_task["is_done"] = self._prepare_pipeline(
            secondary_task["nlu"], secondary_dst, lenient=True)

        self.dst.user_profile.update(secondary_dst.user_profile)

        nbas = self.DM.predict_batch([
            {"dialogue_state": main_task["ds"], "db_result": main_task["db_res"]},
            {"dialogue_state": secondary_task["ds"], "db_result": secondary_task["db_res"]},
        ])

        main_task["nba"] = nbas[0]
        secondary_task["nba"] = nbas[1]

        tasks_to_execute = self._select_tasks_to_execute(main_task, secondary_task)

        return tasks_to_execute, main_task["is_done"], secondary_task["is_done"], main_task["nlu"].get("intent"), secondary_task["ds"], False

    def _select_tasks_to_execute(self, main_task: Task, secondary_task: Task) -> list[Task]:
        """Decide response order and queue unfinished secondary tasks."""
        main_done = main_task["is_done"]
        secondary_done = secondary_task["is_done"]

        if main_done and secondary_done:
            if secondary_task["nlu"].get("intent") == "user_identification":
                logger.debug("Both intents done. Prioritizing user identification.")
                return [secondary_task, main_task]

            logger.debug("Both intents done. Keeping main-first order.")
            return [main_task, secondary_task]

        if not main_done and secondary_done:
            logger.debug("Secondary intent is done while main intent is incomplete.")
            return [secondary_task, main_task]

        if not main_done and not secondary_done:
            logger.debug("Both intents incomplete. Queuing secondary intent.")

            self.task_queue.store(
                nlu_result=secondary_task["nlu"], segment=secondary_task["segment"], dialogue_state=secondary_task["ds"])
            main_task["nba"]["step_by_step_mode"] = True

            return [main_task]

        logger.debug("Main intent is prioritized.")
        return [main_task, secondary_task]

    def _update_dst_and_queue(self, main_is_done: bool, secondary_is_done: bool, main_intent_name: str | None, secondary_dialogue_state: dict[str, Any] | None, should_recover_queue: bool, nba_list: list[dict[str, Any]]) -> None:
        """Update the global DST after task execution and recover queued tasks when needed."""
        if main_is_done:
            logger.debug("Main intent is done.")
            self.dst.complete_task()
            logger.debug("Completed task for main intent: %s", main_intent_name)

            if should_recover_queue and self.task_queue.is_active():
                queued_intent = self.task_queue.pop_intent()
                logger.debug("Recovering queued intent into DST: %s", queued_intent)

                self.dst.ds["intent"] = queued_intent

                if nba_list:
                    nba_list[0]["queue_recovery"] = True
                    nba_list[0]["recovered_intent"] = queued_intent

        if secondary_dialogue_state is not None and main_is_done and not secondary_is_done:
            logger.debug("Preserving unfinished secondary intent after main completion.")
            self.dst.ds = secondary_dialogue_state.copy()

    def reply(self, user_input: str) -> str:
        """Generate a chatbot response for a single user turn."""
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

        logger.debug("====== Router and NLU processing ======")

        excluded_segments = self.task_queue.get_excluded_segment()
        active_intent = self.dst.ds.get("intent")
        router_output = self.router.predict(
            self.history, excluded_segments=excluded_segments, active_intent=active_intent)

        logger.debug("Router output: %s", router_output)

        if isinstance(router_output, dict):
            segments = router_output.get("segments", [])
            step_by_step_mode = router_output.get("step_by_step_mode", False)
        else:
            segments = router_output[:2]
            step_by_step_mode = len(router_output) > 2

        logger.debug("Parsed router segments: %s", segments)
        logger.debug("Step-by-step mode: %s", step_by_step_mode)

        nlu_results = self.NLU.predict_batch(segments, self.history)
        logger.debug("NLU batch results: %s", nlu_results)

        logger.debug("====== Intent processing ======")

        if len(nlu_results) == 1:
            tasks_to_execute, main_is_done, secondary_is_done, main_intent_name, secondary_dialogue_state, should_recover = self._process_single_intent(
                nlu_results[0], segments[0]["segment"])
        elif len(nlu_results) == 2:
            tasks_to_execute, main_is_done, secondary_is_done, main_intent_name, secondary_dialogue_state, should_recover = self._process_double_intent(
                nlu_results, segments)
        else:
            return "I could not understand the request."

        nba_list = [task["nba"] for task in tasks_to_execute]
        dialogue_state_list = [task["ds"] for task in tasks_to_execute]
        active_segments = [task["segment"] for task in tasks_to_execute]

        logger.debug("Tasks to execute: %s", len(tasks_to_execute))
        logger.debug("Main intent done: %s", main_is_done)
        logger.debug("Secondary intent done: %s", secondary_is_done)

        logger.debug("====== DST update and queue management ======")

        self._update_dst_and_queue(main_is_done, secondary_is_done, main_intent_name,
                                   secondary_dialogue_state, should_recover, nba_list)

        combined_response = self.NLG.generate_multi_response(
            nba_list=nba_list,
            ds_list=dialogue_state_list,
            active_segments=active_segments,
            global_history=self.history,
            step_by_step_mode=step_by_step_mode,
        )

        logger.debug("Bot response: %s", combined_response)

        self.history.add_message("assistant", combined_response)

        return combined_response

    def chat_loop(self) -> None:
        """Run an interactive terminal chat loop."""
        print("Chatbot is ready! Type 'exit' to quit.")

        while True:
            logger.debug("-------------------- New turn --------------------")

            user_input = input("You: ")
            command = user_input.strip().lower()

            response = self.reply(user_input)
            print(f"Bot: {response}")

            if command in ["exit", "quit", "stop"]:
                break
