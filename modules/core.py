import os
import asyncio
import aiohttp
import aiofiles
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from yt_dlp import YoutubeDL


# =========================
# CONFIG
# =========================
MAX_CONCURRENT_DOWNLOADS = 3

logging.basicConfig(level=logging.INFO)


# =========================
# GLOBAL SESSION (FAST)
# =========================
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(limit=200, force_close=False)
)


# =========================
# QUEUE SYSTEM
# =========================
queue = asyncio.Queue()
semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)


# =========================
# YT-DLP OPTIONS (FAST)
# =========================
ydl_opts = {
    "quiet": True,
    "concurrent_fragment_downloads": 10,
    "retries": 10,
    "fragment_retries": 10,
    "buffersize": 1024 * 1024,
}


# =========================
# START WORKERS
# =========================
async def start_workers():
    for _ in range(MAX_CONCURRENT_DOWNLOADS):
        asyncio.create_task(worker())


async def worker():
    while True:
        bot, url, cmd, name, message = await queue.get()

        async with semaphore:
            try:
                file_path = await download_video(cmd, name)

                if file_path:
                    await message.reply_document(file_path)
                    os.remove(file_path)

            except Exception as e:
                await message.reply_text(f"❌ Error: {e}")

        queue.task_done()


# =========================
# FAST DOWNLOAD ENGINE
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
# ADD TO QUEUE
# =========================
async def add_task(bot, url, cmd, name, message: Message):
    await queue.put((bot, url, cmd, name, message))
    await message.reply_text("📥 Added to queue...")


# =========================
# COMMAND HANDLER
# =========================
app = Client("bot")


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
# START BOT
# =========================
async def main():
    await start_workers()
    await app.start()
    print("🚀 Bot Started")
    await idle()


if __name__ == "__main__":
    asyncio.run(main())
