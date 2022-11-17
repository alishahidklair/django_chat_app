
# chat_app clone imports
import hashlib, os, time
from functools import wraps
from datetime import datetime
import pytz

from faunadb import query as q
from faunadb.objects import Ref
from faunadb.client import FaunaClient
from dotenv import load_dotenv

load_dotenv()
# Initialize client connection to database
client = FaunaClient(secret=os.getenv("FAUNA_KEY"))


# chat/consumers.py
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name, self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        room_id = text_data_json["roomName"]
        user_name = text_data_json["userName"]

        # saving messages to faunaDB 
        messages = client.query(q.get(q.match(q.index("message_index"), room_id)))
        conversation = messages["data"]["conversation"]
        conversation.append(
            {
                # "sender_username": sender_username,
                "message": message,
                "sender_username": user_name
            }
        )
        
        # Updated the database with the new message
        client.query(
            q.update(
                q.ref(q.collection("messages"), messages["ref"].id()),
                {"data": {"conversation": conversation}},
            )
        )

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        self.send(text_data=json.dumps({"message": message}))



