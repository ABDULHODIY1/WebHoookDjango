import json
import hashlib
from channels.generic.websocket import AsyncWebsocketConsumer
from redis.asyncio import Redis
from channels.layers import get_channel_layer

REDIS_URL = "redis://red-d08eujp5pdvs739o9tq0:6379/0"
WAITING_LIST = "video_waiting_list"
ACTIVE_USERS = "active_users"


class VideoChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = None
        self.room_name = None
        self.role = None

    async def connect(self):
        await self.accept()
        self.redis = await Redis.from_url(REDIS_URL)

        # Aktiv foydalanuvchilar sonini yangilash
        await self.redis.hincrby(ACTIVE_USERS, 'count', 1)
        await self.send_user_count()

        await self.redis.rpush(WAITING_LIST, self.channel_name)
        print(f"User {self.channel_name} connected")
        await self.check_for_pairs()

    async def disconnect(self, close_code):
        if self.redis:
            # Waiting listdan o'chirish
            await self.redis.lrem(WAITING_LIST, 0, self.channel_name)

            # Aktiv foydalanuvchilar sonini yangilash
            await self.redis.hincrby(ACTIVE_USERS, 'count', -1)
            await self.send_user_count()

            if self.room_name:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)
            await self.redis.close()

    async def check_for_pairs(self):
        async with self.redis.pipeline() as pipe:
            while True:
                try:
                    # Atomik operatsiyalar
                    await pipe.watch(WAITING_LIST)
                    length = await pipe.llen(WAITING_LIST)
                    if length >= 2:
                        # Bir vaqtda 2 user olish
                        peers = await pipe.lrange(WAITING_LIST, 0, 1)
                        await pipe.multi()
                        await pipe.ltrim(WAITING_LIST, 2, -1)
                        await pipe.execute()

                        peer1 = peers[0].decode()
                        peer2 = peers[1].decode()

                        room_name = f"room_{hashlib.sha256((peer1 + peer2).encode()).hexdigest()[:10]}"

                        # Grouplarga qo'shish
                        await self.channel_layer.group_add(room_name, peer1)
                        await self.channel_layer.group_add(room_name, peer2)

                        # Pairing xabarlar
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
                    break
                except Exception as e:
                    print("Pairing error:", e)
                    continue

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
        if event["sender_channel"] != self.channel_name:
            await self.send(text_data=json.dumps({
                "type": "signal",
                "data": event["data"]
            }))

    async def send_user_count(self):
        count = await self.redis.hget(ACTIVE_USERS, 'count')
        count = int(count) if count else 0
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "all_users",
            {
                "type": "user.count",
                "count": count
            }
        )

    async def user_count(self, event):
        await self.send(text_data=json.dumps({
            "type": "users",
            "count": event["count"]
        }))