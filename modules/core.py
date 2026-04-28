import os
import asyncio
import time
import logging

# -------------------- ASYNC CMD RUNNER --------------------

async def run_cmd(cmd: str):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        logging.error(stderr.decode())
        return False

    return True

# -------------------- ULTRA FAST DOWNLOAD --------------------

async def download_video(url, name):

    cmd = f'''yt-dlp "{url}"
    -o "{name}.%(ext)s"
    --no-warnings
    --external-downloader aria2c
    --downloader-args "aria2c:
        -x 32
        -s 32
        -k 1M
        --min-split-size=1M
        --max-connection-per-server=16
        --file-allocation=none"
    --concurrent-fragments 16
    --buffer-size 16K
    --http-chunk-size 1M
    '''

    ok = await run_cmd(cmd)

    if not ok:
        return None

    # detect file
    for ext in ["mp4", "mkv", "webm"]:
        file = f"{name}.{ext}"
        if os.path.exists(file):
            return file

    return None

# -------------------- THUMBNAIL --------------------

async def generate_thumbnail(file):
    thumb = f"{file}.jpg"
    cmd = f'ffmpeg -i "{file}" -ss 00:00:10 -vframes 1 "{thumb}"'
    await run_cmd(cmd)
    return thumb if os.path.exists(thumb) else None

# -------------------- SEND VIDEO --------------------

async def send_video(bot, message, file, caption):

    msg = await message.reply("📤 Uploading...")

    start = time.time()

    try:
        thumb = await generate_thumbnail(file)

        await message.reply_video(
            file,
            caption=caption,
            supports_streaming=True,
            thumb=thumb if thumb else None
        )

    except Exception:
        await message.reply_document(file, caption=caption)

    await msg.delete()

    # cleanup
    try:
        os.remove(file)
        if thumb:
            os.remove(thumb)
    except:
        pass

# -------------------- MAIN HANDLER --------------------

async def process_video(bot, message, url):

    name = str(int(time.time()))

    status = await message.reply("📥 Downloading...")

    file = await download_video(url, name)

    if not file:
        await status.edit("❌ Download Failed")
        return

    await status.edit("⚙️ Processing...")

    await asyncio.sleep(1)

    await status.edit("📤 Uploading...")

    await send_video(bot, message, file, f"✅ Done: {file}")

# -------------------- NON-BLOCKING ENTRY --------------------

async def start_process(bot, message, url):
    asyncio.create_task(process_video(bot, message, url))
