from models.chatbot import Chatbot

def main() -> None:

    # Initialize model and components
    model_name = "qwen3"
    model = Chatbot(model_name)

    # Start chat loop
    model.chat_loop()

if __name__ == "__main__":
    main()
