from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from django.shortcuts import render

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


# Create your views here.

# need to check if user has already been when adding rooms. and render a seperate apology.
# currently shows user added even if the room with both the usernames already exists.

# differentiate between sender and receiver messages when sending using channels/ sockets / when live messaging. 
# it works fine when reloaded and the message history is rendered from FaunaDB

# add notification using django


# clean and delete not needed code and files
# push to github
# deploy on heroku
# convert into a desktop app
# deploy on other free services
# submit for CS50 final project


def index(request):
    register()
    return render(request, "chat/index.html")

# auto registers all users from django admin to fauna users table

def register():
    user_admin = get_user_model().objects.all().values()
    user_exists = False
    # list = []
    # list_success = []
    # list_fail = []
    for row in user_admin:
        username = str(row["username"]) 
        # list.append(username)
        try:
            user = client.query(
                q.get(q.match(q.index("user_index_username"), username))
            )
            # list_success.append(user)
        except:
            user = client.query(
                q.create(
                    q.collection("users"),
                    {
                        "data": {
                            "username": username,
                            "date": datetime.now(pytz.UTC),
                        }
                    },
                )
            )
            # Create a new chat list for newly registered user
            chat = client.query(
                q.create(
                    q.collection("chats"),
                    {
                        "data": {
                            "user_id": user["ref"].id(),
                            "chat_list": [],
                        }
                    },
                )
            )
            # list_fail.append(chat)
    
    # return render(request, "chat/index.html", {
    #     "a": list,
    #     # "b": list_success,
        # "c": list_fail
    # })



def login_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("chat"), {})

    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("chat"), {})
        else:
            return render(request, "chat/login.html", {
                "message": "Invalid credentials."
            })
    else:
        return render(request, "chat/login.html")

@login_required(login_url='login')
def logout_view(request):
    user = request.user
    logout(request)
    return render(request, "chat/login.html", {
        "message": f"You are Logged out"
    })



def chat_view(request):
    if request.method == "POST":
        user = str(request.user)
        new_chat = request.POST.get("username").strip().lower()

        # If user is trying to add their self, do nothing

        if new_chat == user:
            return render(request, "chat/chat.html", {
            "user_message": "Own username provided"
        })


        try:
            # If user tries to add a chat that has not registerd, do nothing
            user_id = client.query(
                q.get(q.match(q.index("user_index_username"), user))
            )
            new_chat_id = client.query(
                q.get(q.match(q.index("user_index_username"), new_chat))
            )
        except:
            return render(request, "chat/chat.html", {
            "user_message": "Username does not exist"
        })

        # Get the chats related to both user
        chats = client.query(q.get(q.match(q.index("chat_index"), user_id["ref"].id())))
        recepient_chats = client.query(
            q.get(q.match(q.index("chat_index"), new_chat_id["ref"].id()))
        )
        # Check if the chat the users is trying to add has not been added before
        try:
            chat_list = [list(i.values())[0] for i in chats["data"]["chat_list"]]
        except:
            chat_list = []


        if new_chat_id["ref"].id() not in chat_list:
            # Append the new chat to the chat list of the user
            room_id = str(int(new_chat_id["ref"].id()) + int(user_id["ref"].id()))[-4:]
            chats["data"]["chat_list"].append(
                {"user_id": new_chat_id["ref"].id(), "room_id": room_id}
            )
            recepient_chats["data"]["chat_list"].append(
                {"user_id": user_id["ref"].id(), "room_id": room_id}
            )

            # Update chat list for both users
            client.query(
                q.update(
                    q.ref(q.collection("chats"), chats["ref"].id()),
                    {"data": {"chat_list": chats["data"]["chat_list"]}},
                )
            )
            client.query(
                q.update(
                    q.ref(q.collection("chats"), recepient_chats["ref"].id()),
                    {"data": {"chat_list": recepient_chats["data"]["chat_list"]}},
                )
            )
            client.query(
                q.create(
                    q.collection("messages"),
                    {"data": {"room_id": room_id, "conversation": []}},
                )
            )

        return render(request, "chat/chat.html", {
            "user_message": "User added please reload"
        })

    else:

        # Get the room id in the url or set to None
        # room_id = request.args.get("rid", None)
        room_id = None
        # Initialize context that contains information about the chat room
        data = []

        user = str(request.user)
        try:
            # If user tries to add a chat that has not registerd, do nothing
            user_id = client.query(
                q.get(q.match(q.index("user_index_username"), user))
            )
        except:
            return render(request, "chat/chat.html", {
                "a": "Error cannot get user_id"
            })

        try:
            # Get the chat list for the user in the room i.e all of the people they have a chat history with on the application
            chat_list = client.query(
                q.get(q.match(q.index("chat_index"), user_id["ref"].id()))
            )["data"]["chat_list"]
        except:
            chat_list = []

        for i in chat_list:
            # Query the database to get the user name of users in a user's chat list
            username = client.query(q.get(q.ref(q.collection("users"), i["user_id"])))[
                "data"
            ]["username"]
            is_active = False
            # If the room id in the url is the same with any of the room id in a user's chat list, that room is currently the active room
            if room_id == i["room_id"]:
                is_active = True
            try:
                # Get the last message for each chat room
                last_message = client.query(
                    q.get(q.match(q.index("message_index"), i["room_id"]))
                )["data"]["conversation"][-1]["message"]
            except:
                # Set variable to this when no messages have been sent to the room
                last_message = "This place is empty. No messages ..."
            data.append(
                {
                    "username": username,
                    "room_id": i["room_id"],
                    "is_active": is_active,
                    "last_message": last_message,
                }
            )
    
        # Get all the message history in a certian room
        messages = []
        if room_id != None:
            messages = client.query(q.get(q.match(q.index("message_index"), room_id)))[
                "data"
            ]["conversation"]

        return render(request, "chat/chat.html", {
            "user_data_username": user,
            "room_id": room_id,
            "data": data,
            "messages": messages,
            # username and last message from data
            # "a": user,
            # "b": room_id,
            "c": data,
            # "d": messages,
        })

@login_required(login_url='login')
def room(request, room_name):
    user_name = str(request.user)

    messages = []
    if room_name != None:
        messages = client.query(q.get(q.match(q.index("message_index"), room_name)))[
            "data"
        ]["conversation"]
    return render(request, "chat/room.html", {
        "room_name": room_name,
        "user_name": user_name,
        "messages": messages,
        
        })





