from django.shortcuts import render

def video_chat(request):
    return render(request, 'video_chat/index.html')