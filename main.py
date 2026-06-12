import argparse

from app.chatbot import Chatbot
from utils.logger import setup_logging


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3_4b", help="The name of the model to use: qwen3, qwen2, or gpt4o")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    chatbot = Chatbot(args.model)
    chatbot.chat_loop()


if __name__ == "__main__":
    main()