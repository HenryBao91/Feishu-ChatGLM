import json
import os
import time
import attr
import uuid
from larksuiteoapi.api import Request, set_timeout
from larksuiteoapi import Config, ACCESS_TOKEN_TYPE_TENANT, DOMAIN_FEISHU
from util.app_config import app_config
from store.chat_history import ChatEvent, append_chat_event
from util.logger import app_logger
from feishu.command_card import COMMAND_CARD
from larksuiteoapi.service.im.v1 import MessageService

@attr.s
class Message(object):
    """
    Usage: easy to define class
        msg = Message(message_id="12345")
        msg.message_id
    """
    message_id = attr.ib(type=str)  # type: ignore


class MessageSender:
    def __init__(self, conf: Config):
        if not conf:
            raise Exception("conf is required")
        self.conf = conf

    def send_text_message(self, receive_id, msg, receive_id_type="chat_id", append=True):
        body = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({
                "text": msg
            }),
            "uuid": str(uuid.uuid4())
        }

        req = Request(
            f'/open-apis/im/v1/messages?receive_id_type={receive_id_type}',
            'POST',
            ACCESS_TOKEN_TYPE_TENANT,
            body,
            output_class=Message,
            request_opts=[set_timeout(3)]
        )
        resp = req.do(self.conf)
        app_logger.debug("send_text_message:%s", msg)

        if resp.code == 0:
            # store the message in the chat history
            if append:
                new_chat_event = ChatEvent(**{
                    "user_id": receive_id,
                    "chat_id": "",
                    "chat_type": "",
                    "message_id": resp.data.message_id,
                    "message_type": "",
                    "content": json.dumps({"text": msg}),
                    "sender_user_id": "assistant",
                    "create_time": int(time.time() * 1000)
                })
                append_chat_event(new_chat_event)
            return True
        else:
            app_logger.error(
                "send message failed, code:%s, msg:%s, error:%s", resp.code, resp.msg, resp.error)
            return False


    def reply_to_message(self, message_id, msg, msg_type="text", reply_in_thread=False):
        body = {
            "content": json.dumps({
                "text": msg
            }),
            "msg_type": msg_type,
            "uuid": str(uuid.uuid4()),
            "reply_in_thread": reply_in_thread
        }

        req = Request(
            f'/open-apis/im/v1/messages/{message_id}/reply',
            'POST',
            ACCESS_TOKEN_TYPE_TENANT,
            body,
            output_class=Message,
            request_opts=[set_timeout(3)]
        )
        resp = req.do(self.conf)
        app_logger.debug("reply_to_message:%s", msg)

        if resp.code != 0:
            app_logger.error("Failed to reply to message: %s", resp.msg)
            return None

        return resp.data.message_id

    def send_command_card(self, user_id):
        body = {
            "user_id": user_id,
            "msg_type": "interactive",
            "card": COMMAND_CARD
        }
        req = Request('/open-apis/message/v4/send', 'POST', ACCESS_TOKEN_TYPE_TENANT, body,
                      output_class=Message, request_opts=[set_timeout(3)])
        resp = req.do(self.conf)
        app_logger.debug("send_command_card to %s", user_id)
        if resp.code == 0:
            return True
        else:
            app_logger.error(
                "send message failed, code:%s, msg:%s, error:%s", resp.code, resp.msg, resp.error)
            return False


if __name__ == '__main__':
    try:
        app_config.validate()
        try:
            app_settings = Config.new_internal_app_settings_from_env()
            app_logger.debug("Using environment variables for configuration")
        except RuntimeError as e:
            app_logger.warning("Environment variables not found, using app_config: %s", str(e))
            app_settings = {
                "app_id": app_config.APP_ID,
                "app_secret": app_config.APP_SECRET,
                "app_encryption_key": app_config.APP_ENCRYPT_KEY,
                "app_verification_token": app_config.APP_VERIFICATION_TOKEN
            }
            app_settings = Config.new_internal_app_settings(app_settings)

        conf = Config(DOMAIN_FEISHU, app_settings)
        message_sender = MessageSender(conf)
        # new API
        message_id = message_sender.send_text_message("chat_id", "Hello BoBo Group", "chat_id")
        # reply API
        reply_message_id = message_sender.reply_to_message(message_id, "This is a reply", "text", reply_in_thread=True)

    except Exception as e:
        app_logger.error("Exception occurred in main: %s", str(e))