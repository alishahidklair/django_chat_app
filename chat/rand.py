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

def main():
    room_id = "3684"
    messages = client.query(q.get(q.match(q.index("message_index"), room_id)))
    # conversation = messages["data"]["conversation"]
    # conversation.append(
    #     {
    #         # "sender_username": sender_username,
    #         "message": "message",
    #     }
    #         )

    print(messages)
    # user = client.query(
    #             q.get(q.match(q.index("user_index_username"), "ali"))
    #         )
    # print(conversation)
    # print(user)
if __name__ == "__main__":
    main()