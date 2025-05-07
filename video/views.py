from django.shortcuts import render

import json
import asyncio
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from aiogram import types
from .bot.main import dp, bot  # Bot va dispatcher import qilinadi


@csrf_exempt
def index(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            update = types.Update(**payload)
            asyncio.create_task(dp.feed_update(bot, update))
            return HttpResponse("OK", status=200)
        except Exception as e:
            return HttpResponse(f"Xatolik: {e}", status=400)

    # GET bo‘lsa, oddiy HTML ko‘rsatamiz
    return render(request, "index.html")
