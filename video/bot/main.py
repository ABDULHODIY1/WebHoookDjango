from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

BOT_TOKEN = "8006332215:AAH-xXrm8fmPBEC9GcdWiVErnt3Fr1TL_DU"


bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton(
            text="🎥 Random Video Chat",
            web_app=WebAppInfo(url="https://webhoookdjango0.onrender.com")
        )
    )
    await message.answer("🎬 Chatni boshlash uchun quyidagi tugmani bosing:", reply_markup=keyboard)



if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp)