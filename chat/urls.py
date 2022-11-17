from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("chat/<str:room_name>/", views.room, name="room"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("chat", views.chat_view, name="chat"),
    
]