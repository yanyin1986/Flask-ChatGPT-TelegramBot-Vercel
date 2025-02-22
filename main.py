# -*- coding: utf-8 -*-

import logging

import telegram, os
from flask import Flask, request
from telegram.ext import Dispatcher, MessageHandler, Filters

#################
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

MSG_LIST_LIMIT = int(os.getenv("MSG_LIST_LIMIT", default=20))
LANGUAGE_TABLE = {
    "zh": "哈囉！",
    "en": "Hello!",
    "jp": "こんにちは"
}


class Prompts:
    def __init__(self):
        self.msg_list = []

    def add_msg(self, new_msg):
        if len(self.msg_list) >= MSG_LIST_LIMIT:
            self.remove_msg()
        self.msg_list.append(new_msg)

    def remove_msg(self):
        self.msg_list.pop(0)

    def generate_prompt(self):
        return '\n'.join(self.msg_list)


class Messages:
    def __init__(self):
        self.msg_list = []

    def add_msg(self, new_msg):
        if len(self.msg_list) >= MSG_LIST_LIMIT:
            self.msg_list.pop(0)
        self.msg_list.append({"role": "user", "content": new_msg})

    def add_assistant_msg(self, new_msg):
        if len(self.msg_list) >= MSG_LIST_LIMIT:
            self.msg_list.pop(0)
        self.msg_list.append({"role": "assistant", "content": new_msg})

    def generate_messages(self):
        return self.msg_list


class ChatGPT:
    def __init__(self):
        # self.prompt = Prompts()
        self.messages = Messages()
        self.model = os.getenv("OPENAI_MODEL", default="text-davinci-003")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", default=0))
        self.frequency_penalty = float(os.getenv("OPENAI_FREQUENCY_PENALTY", default=0))
        self.presence_penalty = float(os.getenv("OPENAI_PRESENCE_PENALTY", default=0.6))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS",
                                        default=240))  # You can change here to decide the characer number AI gave you.

    def get_response(self):
        # openai.ChatCompletion.create(
        #     model=self.model
        # )
        generate_messages = self.messages.generate_messages()
        print("messages -> ")
        print(generate_messages)
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=generate_messages,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
            max_tokens=self.max_tokens,
            stream=True
        )

        print(response)
        print("AI回答內容(The direct answer that AI gave you)：")
        result = ''
        for resp in response:
            print(resp)
            delta = resp['choices'][0]['delta']
            if 'content' in delta:
                result += delta['content']
        print("AI原始回覆資料內容(The original answer that AI gave you)：")
        print(result)

        self.messages.add_assistant_msg(result)
        return result.lstrip()

    def add_msg(self, text):
        self.messages.add_msg(text)


#####################

telegram_bot_token = str(os.getenv("TELEGRAM_BOT_TOKEN"))

# Load data from config.ini file
# config = configparser.ConfigParser()
# config.read('config.ini')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial Flask app
app = Flask(__name__)

# Initial bot by Telegram access token
bot = telegram.Bot(token=telegram_bot_token)

chatgpt = ChatGPT()


@app.route('/callback', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        # Update dispatcher process that handler to process this message
        dispatcher.process_update(update)
    return 'ok'


@app.route('/health_check', methods=['GET'])
def health_check():
    """health check"""
    return 'ok'


@app.route('/reply', methods=['GET'])
def reply():
    msg = request.args.get('prompt', default='', type=str)
    if msg == '':
        return 'error'

    if msg == '::new':
        chatgpt.messages.msg_list.clear()
        return 'cleared'

    chatgpt.messages.add_msg(msg)
    ai_reply_response = chatgpt.get_response()
    return ai_reply_response


def reply_handler(bot, update):
    """Reply message."""
    # text = update.message.text
    # update.message.reply_text(text)
    text = update.message.text
    print('meg is %s' % text)
    if text == '::new':
        update.message.reply_text('new chat.')
        chatgpt.messages.msg_list.clear()
    else:
        chatgpt.messages.add_msg(text)  # 人類的問題 the question humans asked
        ai_reply_response = chatgpt.get_response()  # ChatGPT產生的回答 the answers that ChatGPT gave
        update.message.reply_text(ai_reply_response)  # 用AI的文字回傳 reply the text that AI made


# New a dispatcher for bot
dispatcher = Dispatcher(bot, None)

# Add handler for handling message, there are many kinds of message. For this handler, it particular handle text
# message.
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))

if __name__ == "__main__":
    # Running server
    app.run(debug=True)
