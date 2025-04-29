import json
import hashlib
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from redis.asyncio import Redis

REDIS_URL = "redis://red-d08eujp5pdvs739o9tq0:6379/0"
WAITING_LIST = "video_waiting_list"


class VideoChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = None
        self.room_name = None
        self.role = None

    async def connect(self):
        await self.accept()
        self.redis = await Redis.from_url(REDIS_URL)

        # Add to waiting list
        await self.redis.rpush(WAITING_LIST, self.channel_name)
        print(f"User {self.channel_name} added to waiting list")

        # Check for pairs
        await self.check_for_pairs()

    async def check_for_pairs(self):
        length = await self.redis.llen(WAITING_LIST)
        if length >= 2:
            peer1 = await self.redis.lpop(WAITING_LIST)
            peer2 = await self.redis.lpop(WAITING_LIST)

            peer1 = peer1.decode()
            peer2 = peer2.decode()

            # Create room name
            room_name = f"room_{hashlib.sha256((peer1 + peer2).encode()).hexdigest()[:10]}"

            # Add to group
            await self.channel_layer.group_add(room_name, peer1)
            await self.channel_layer.group_add(room_name, peer2)

            # Send pairing info
            await self.channel_layer.send(peer1, {
                "type": "pairing.info",
                "room": room_name,
                "role": "caller"
            })
            await self.channel_layer.send(peer2, {
                "type": "pairing.info",
                "room": room_name,
                "role": "callee"
            })

    async def disconnect(self, close_code):
        if self.redis:
            await self.redis.lrem(WAITING_LIST, 0, self.channel_name)
            if self.room_name:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)
            await self.redis.close()

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get("type") == "signal":
            await self.channel_layer.group_send(
                self.room_name,
                {
                    "type": "signal.message",
                    "data": data["data"],
                    "sender_channel": self.channel_name
                }
            )

    async def pairing_info(self, event):
        self.room_name = event["room"]
        self.role = event["role"]
        await self.send(text_data=json.dumps({
            "type": "paired",
            "room": self.room_name,
            "role": self.role
        }))

    async def signal_message(self, event):
        # Don't send the signal back to the sender
        if event["sender_channel"] != self.channel_name:
            await self.send(text_data=json.dumps({
                "type": "signal",
                "data": event["data"]
            }))
