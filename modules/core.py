import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import subprocess
import concurrent.futures
import re

from utils import progress_bar
from pyrogram import Client
from pyrogram.types import Message
from pytube import Playlist
from yt_dlp import YoutubeDL

failed_counter = 0
logging.basicConfig(level=logging.INFO)

async def download_video(url, cmd, name):
    """Fixed version - no more PDF and no more interrupted"""
    global failed_counter

    # FIX 1: aria2c hata diya. Bahut site aria2c ko block karti hain. 
    # FIX 2: --no-part --continue add kiya taaki beech me na toote
    download_cmd = (
        f'{cmd} '
        f'-R 10 '  # retry kam rakha
        f'--fragment-retries 10 '
        f'--no-part '  # .part file nahi banega
        f'--continue '  # ruka hua dobara start hoga
        f'--socket-timeout 30 ' # timeout badhaya
    )
    
    logging.info(f"RUNNING: {download_cmd}")

    process = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    out = stdout.decode(errors="ignore")
    err = stderr.decode(errors="ignore")
    if out: logging.info(out)
    if err: logging.error(err)

    # Retry logic
    if process.returncode!= 0 and failed_counter <= 3:
        failed_counter += 1
        logging.warning(f"Retrying... Attempt {failed_counter}")
        await asyncio.sleep(5)
        return await download_video(url, cmd, name)

    failed_counter = 0

    # FIX 3: File dhoondne ka tareeka sahi kiya
    # yt-dlp kabhi kabhi name ke aage title jod deta hai
    for f in os.listdir('.'):
        if f.startswith(name) and f.endswith(('.mp4', '.mkv', '.webm', '.m4a')):
            logging.info(f"File found: {f}")
            return f

    logging.error("Downloaded file not found")
    return None

# Baaki sab function same rahenge upar wale
def duration(filename):
    try:
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return float(result.stdout.decode().strip())
    except: return 0

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB': break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    reply = await m.reply_text(f"Uploading » {name}")
    await asyncio.sleep(1)
    start_time = time.time()
    await m.reply_document(ka, caption=cc1, progress=progress_bar, progress_args=(reply, start_time))
    count += 1
    await reply.delete()
    await asyncio.sleep(1)
    if os.path.exists(ka): os.remove(ka)
    return count

async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    thumb_path = f"{filename}.jpg"
    if thumb == "no":
        subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:01 -vframes 1 "{thumb_path}" -y', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        thumbnail = thumb_path if os.path.exists(thumb_path) else None
    else: thumbnail = thumb
    try: await prog.delete()
    except: pass
    reply = await m.reply_text(f"⥣ Uploading » {name}")
    dur = int(duration(filename)) if os.path.exists(filename) else 0
    start_time = time.time()
    try:
        await m.reply_video(video=filename, caption=cc, supports_streaming=True, thumb=thumbnail, duration=dur, progress=progress_bar, progress_args=(reply, start_time))
    except Exception:
        await m.reply_document(document=filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time))
    for f in [filename, thumb_path]:
        if os.path.exists(f): os.remove(f)
    await reply.delete()
