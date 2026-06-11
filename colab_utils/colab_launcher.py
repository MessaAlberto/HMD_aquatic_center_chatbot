import os
import sys
import logging
import importlib
from IPython.display import HTML, display
from google.colab import output, userdata


def setup_project(project_dir: str, debug: bool = False) -> None:
    os.chdir(project_dir)

    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    open("app/__init__.py", "a").close()

    importlib.invalidate_caches()

    for module_name in ["app", "app.chatbot"]:
        if module_name in sys.modules:
            del sys.modules[module_name]

    try:
        hf_token = userdata.get("HF_TOKEN")
    except Exception:
        hf_token = None

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
    else:
        print("HF_TOKEN not found. If model loading fails, add HF_TOKEN to Colab Secrets.")

    os.environ["APP_DEBUG"] = str(debug).lower()

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(levelname)s:%(message)s",
        force=True,
    )


def load_bot(model_name: str = "qwen3"):
    from app.chatbot import Chatbot

    bot = Chatbot(model_name=model_name)
    print("Bot loaded.")
    return bot


def start_chat(bot, ui_path: str = "colab_utils/colab_ui.html") -> None:
    def send_message_to_bot(user_message):
        try:
            response = bot.reply(user_message)
            return {"ok": True, "response": response}
        except Exception as e:
            return {"ok": False, "response": f"Error: {e}"}

    def reset_bot_state():
        try:
            bot.reset_state()
            return {"ok": True, "response": "Conversation reset."}
        except Exception as e:
            return {"ok": False, "response": f"Error: {e}"}

    output.register_callback("notebook.send_message_to_bot", send_message_to_bot)
    output.register_callback("notebook.reset_bot_state", reset_bot_state)

    with open(ui_path, "r", encoding="utf-8") as f:
        display(HTML(f.read()))