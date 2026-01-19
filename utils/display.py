from IPython.display import display, Markdown

def dispaly_conversation(messages, user_msg, bot_msg):
    md = (
        "### Conversation\n\n"
        f"**System:** {messages[0]['content']}\n\n"
        f"**User:** {user_msg}\n\n"
        f"**Assistant:** {bot_msg}\n"
    )
    display(Markdown(md))