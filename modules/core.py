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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def duration(filename):
    """Get video duration in seconds"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return float(result.stdout.decode().strip())
    except:
        return 0

def exec(cmd):
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output = process.stdout.decode(errors="ignore")
    if output: print(output)
    return output

def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        executor.map(exec, cmds)

async def aio(url, name):
    k = f"{name}.pdf"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(k, mode='wb') as f:
                    await f.write(await resp.read())
    return k

async def download(url, name):
    return await aio(url, name)

def parse_vid_info(info):
    info = info.strip().split("\n")
    new_info, temp = [], []
    for i in info:
        i = str(i)
        if "[" not in i and "---" not in i:
            i = " ".join(i.split())
            parts = i.split("|")[0].split(" ", 2)
            try:
                if "RESOLUTION" not in parts[2] and parts[2] not in temp and "audio" not in parts[2]:
                    temp.append(parts[2])
                    new_info.append((parts[0], parts[2]))
            except: pass
    return new_info

def vid_info(info):
    info = info.strip().split("\n")
    new_info, temp = dict(), []
    for i in info:
        i = str(i)
        if "[" not in i and "---" not in i:
            i = " ".join(i.split())
            parts = i.split("|")[0].split(" ", 3)
            try:
                if "RESOLUTION" not in parts[2] and parts[2] not in temp and "audio" not in parts[2]:
                    temp.append(parts[2])
                    new_info[f"{parts[2]}"] = f"{parts[0]}"
            except: pass
    return new_info

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    logging.info(f"[{cmd!r} exited with {proc.returncode}]")
    if proc.returncode!= 0: return False
    if stdout: return stdout.decode(errors='ignore')
    if stderr: return stderr.decode(errors='ignore')
    return True

def old_download(url, file_name, chunk_size=1024 * 1024):
    if os.path.exists(file_name): os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk: fd.write(chunk)
    return file_name

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB': break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def time_name():
    now = datetime.datetime.now()
    return f"{datetime.date.today()} {now.strftime('%H%M%S')}.mp4"

def get_playlist_videos(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        videos = {video.title: video.watch_url for video in playlist.videos if video.title}
        return playlist.title, videos
    except Exception as e:
        logging.error(f"Playlist Error: {e}")
        return None, None

def get_all_videos(channel_url):
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(channel_url, download=False)
        if "entries" in result:
            video_links = {index + 1: (video["title"], video["url"]) for index, video in enumerate(result["entries"])}
            return video_links, result["title"]
        else: return None, None

def save_to_file(video_links, channel_name):
    sanitized_channel_name = re.sub(r"[^\w\s-]", "", channel_name).strip().replace(" ", "_")
    filename = f"{sanitized_channel_name}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        for number, (title, url) in video_links.items():
            if not url.startswith("https://"):
                url = f"https://www.youtube.com/watch?v={url}" if "shorts" not in url else f"https://www.youtube.com{url}"
            file.write(f"{number}. {title}: {url}\n")
    return filename

async def download_video(url, cmd, name):
    """Download video with yt-dlp + aria2c + auto retry"""
    global failed_counter

    # aria2c check - agar nahi hai to normal download
    use_aria = subprocess.run("which aria2c", shell=True).returncode == 0
    aria_args = '--external-downloader aria2c --downloader-args "aria2c: -x 16 -s 16 -k 1M"' if use_aria else ""

    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --concurrent-fragments 16 {aria_args}'
    logging.info(f"RUNNING: {download_cmd}")

    process = await asyncio.create_subprocess_shell(
        download_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
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
        await asyncio.sleep(3)
        return await download_video(url, cmd, name)

    failed_counter = 0

    # Find file
    for ext in ["", ".webm", ".mkv", ".mp4", ".m4a"]:
        filepath = f"{name}{ext}"
        if os.path.isfile(filepath):
            logging.info(f"File found: {filepath}")
            return filepath

    # yt-dlp sometimes adds title to filename
    for f in os.listdir():
        if f.startswith(name):
            return f

    logging.error("Downloaded file not found")
    return None

async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name):
    reply = await m.reply_text(f"Uploading » {name}")
    await asyncio.sleep(1)
    start_time = time.time()
    await m.reply_document(
        ka, caption=cc1, progress=progress_bar, progress_args=(reply, start_time)
    )
    count += 1
    await reply.delete()
    await asyncio.sleep(1)
    if os.path.exists(ka): os.remove(ka)
    return count

async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog):
    # Thumbnail
    thumb_path = f"{filename}.jpg"
    if thumb == "no":
        subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:01 -vframes 1 "{thumb_path}" -y', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        thumbnail = thumb_path if os.path.exists(thumb_path) else None
    else:
        thumbnail = thumb

    try: await prog.delete()
    except: pass

    reply = await m.reply_text(f"⥣ Uploading » {name}")
    dur = int(duration(filename)) if os.path.exists(filename) else 0
    start_time = time.time()

    try:
        await m.reply_video(
            video=filename, caption=cc, supports_streaming=True, thumb=thumbnail,
            duration=dur, progress=progress_bar, progress_args=(reply, start_time)
        )
    except Exception:
        await m.reply_document(document=filename, caption=cc, progress=progress_bar, progress_args=(reply, start_time))

    # Cleanup
    for f in [filename, thumb_path]:
        if os.path.exists(f): os.remove(f)
    await reply.delete()
