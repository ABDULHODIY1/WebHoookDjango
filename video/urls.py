from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_chat, name='video_chat'),
]