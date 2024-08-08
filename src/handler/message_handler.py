import json

from larksuiteoapi import Config

from feishu.message_sender import MessageSender

from store.chat_history import ChatEvent, get_chat_context_by_user_id
from store.user_prompt import user_prompt
from util.app_config import AppConfig, app_config
from util.logger import app_logger

if app_config.LLM == 'chatGLM':
    from llm.chatglm import get_chat_response
else:
    from llm.chatgpt import get_chat_response


def get_text_message(chat_event: ChatEvent):
    try:
        content = json.loads(chat_event.content)
        if "text" in content:
            return content["text"]
    except json.JSONDecodeError:
        return chat_event.content

class MessageEventHandlerBase:
    def __init__(self, app_config: AppConfig, conf: Config):
        if not app_config:
            raise Exception("app_config is required")
        if not conf:
            raise Exception("conf is required")
        self.conf = conf
        self.app_config = app_config
        self.message_sender = MessageSender(self.conf)

    def handle_message(self, chat_event: ChatEvent):
        raise NotImplementedError("Subclasses should implement this method")

class OpenaiMessageEventHandler(MessageEventHandlerBase):
    def handle_message(self, chat_event: ChatEvent):
        content = json.loads(chat_event.content)
        # check if the message is already handled
        if "text" in content:
            # get history
            db_history = get_chat_context_by_user_id(chat_event.user_id)
            prompt = user_prompt.read_prompt(chat_event.user_id)
            extra_args = {"prompt": prompt} if prompt else {}
            if len(db_history) == 0:
                return self.message_sender.send_text_message(
                    chat_event.sender_user_id, get_chat_response([{"role": "user", "content": content["text"]}], **extra_args))
            else:
                gpt_history = [{"role": "assistant", "content": get_text_message(x)} if x.sender_user_id == "assistant" else {
                    "role": "user", "content": get_text_message(x)} for x in db_history]
                response = get_chat_response(gpt_history,**extra_args)
                return self.message_sender.send_text_message(
                    chat_event.sender_user_id, response)
        return True

class ChatglmMessageEventHandler(MessageEventHandlerBase):
    def handle_message(self, chat_event: ChatEvent):
        content = json.loads(chat_event.content)
        chat_type = chat_event.chat_type

        if "text" in content and chat_type in ["group", "p2p"]:
            db_history = get_chat_context_by_user_id(chat_event.user_id)
            prompt = user_prompt.read_prompt(chat_event.user_id)
            extra_args = {"prompt": prompt} if prompt else {}
            if len(db_history) == 0:
                if chat_type == "group":
                    return self.message_sender.reply_to_message(
                        chat_event.message_id, get_chat_response(content["text"]))
                else:
                    return self.message_sender.send_text_message(
                        chat_event.chat_id, get_chat_response(content["text"]),
                        # receive_id_type="user_id"
                    )

            else:
                # 这里注意，消息会先落库，再调聊天模型，所以要把当前的提问先分离出来
                user_history = [get_text_message(x) for x in db_history if x.sender_user_id != "assistant"]
                current_question = user_history[-1]
                user_history = user_history[:-1]
                ai_history = [get_text_message(x) for x in db_history if x.sender_user_id == "assistant"]
                gpt_history = list(zip(user_history, ai_history))

                response = get_chat_response(current_question, history=gpt_history)

                if chat_type == "group":
                    return self.message_sender.reply_to_message(chat_event.message_id, response)
                else:
                    return self.message_sender.send_text_message(
                        chat_event.chat_id, response,
                        # receive_id_type="user_id"
                    )

        return True