import os
import asyncio
import logging
import aiohttp
from pyrogram import Client, filters
from pyrogram.types import Message


# =========================
# CONFIG
# =========================
MAX_CONCURRENT = 3

logging.basicConfig(level=logging.INFO)


# =========================
# GLOBALS (SAFE INIT)
# =========================
session = None
queue = asyncio.Queue()
semaphore = asyncio.Semaphore(MAX_CONCURRENT)


# =========================
# INIT SESSION (FIX FOR ERROR)
# =========================
async def init_session():
    global session
    session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=100, limit_per_host=20)
    )


# =========================
# START WORKERS
# =========================
async def start_workers():
    for _ in range(MAX_CONCURRENT):
        asyncio.create_task(worker())


async def worker():
    while True:
        bot, url, cmd, name, message = await queue.get()

        async with semaphore:
            try:
                file_path = await download_video(cmd, name)

                if file_path and os.path.exists(file_path):
                    await message.reply_document(file_path)
                    os.remove(file_path)

            except Exception as e:
                await message.reply_text(f"❌ Error: {e}")

        queue.task_done()


# =========================
# FAST YT-DLP + ARIA2C
# =========================
async def download_video(cmd: str, name: str):
    download_cmd = (
        f'{cmd} '
        f'-R 25 --fragment-retries 25 '
        f'--external-downloader aria2c '
        f'--downloader-args "aria2c: -x 32 -s 32 -k 1M --file-allocation=none"'
    )

    proc = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    await proc.communicate()

    for ext in [".mp4", ".mkv", ".webm"]:
        if os.path.exists(name + ext):
            return name + ext

    if os.path.exists(name):
        return name

    return None


# =========================
# QUEUE HANDLER
# =========================
async def add_task(bot, url, cmd, name, message: Message):
    await queue.put((bot, url, cmd, name, message))
    await message.reply_text("📥 Added to queue...")


# =========================
# BOT APP
# =========================
app = Client("bot")


# =========================
# COMMAND
# =========================
@app.on_message(filters.command("dl"))
async def dl_handler(bot, message: Message):
    try:
        url = message.text.split(None, 1)[1]

        name = url.split("=")[-1] if "=" in url else "video"

        cmd = f'yt-dlp -o "{name}.%(ext)s" {url}'

        await add_task(bot, url, cmd, name, message)

    except Exception as e:
        await message.reply_text(f"Usage: /dl <url>\n\nError: {e}")


# =========================
# STARTUP (IMPORTANT FIX)
# =========================
async def main():
    await init_session()      # 🔥 FIX: event loop ready now
    await start_workers()
    await app.start()
    print("🚀 Bot Started Successfully")
    await idle()


if __name__ == "__main__":
    asyncio.run(main())
