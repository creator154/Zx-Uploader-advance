import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures
import re

from utils import progress_bar

from pyrogram import Client, filters
from pyrogram.types import Message

from pytube import Playlist
from yt_dlp import YoutubeDL
import yt_dlp as youtube_dl


failed_counter = 0


def duration(filename):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filename
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    return float(result.stdout)


def exec(cmd):
    process = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output = process.stdout.decode()
    print(output)

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
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()

    return k


async def download(url, name):
    ka = f"{name}.pdf"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()

    return ka


def parse_vid_info(info):
    info = info.strip().split("\n")

    new_info = []
    temp = []

    for i in info:
        i = str(i)

        if "[" not in i and "---" not in i:

            while "  " in i:
                i = i.replace("  ", " ")

            i = i.split("|")[0].split(" ", 2)

            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))

            except:
                pass

    return new_info


def vid_info(info):
    info = info.strip().split("\n")

    new_info = dict()
    temp = []

    for i in info:
        i = str(i)

        if "[" not in i and "---" not in i:

            while "  " in i:
                i = i.replace("  ", " ")

            i = i.split("|")[0].split(" ", 3)

            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])

                    new_info.update({
                        f"{i[2]}": f"{i[0]}"
                    })

            except:
                pass

    return new_info


async def run(cmd):

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    print(f"[{cmd!r} exited with {proc.returncode}]")

    if proc.returncode == 1:
        return False

    if stdout:
        return f"[stdout]\n{stdout.decode()}"

    if stderr:
        return f"[stderr]\n{stderr.decode()}"


def old_download(url, file_name, chunk_size=1024 * 1024):

    if os.path.exists(file_name):
        os.remove(file_name)

    r = requests.get(
        url,
        allow_redirects=True,
        stream=True
    )

    with open(file_name, 'wb') as fd:

        for chunk in r.iter_content(chunk_size=chunk_size):

            if chunk:
                fd.write(chunk)

    return file_name


def old_download(url, file_name, chunk_size=1024 * 1024):
    ...
    return file_name


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0

    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()

    current_time = now.strftime("%H%M%S")

    return f"{date} {current_time}.mp4"


def get_playlist_videos(playlist_url):

    try:
        playlist = Playlist(playlist_url)

        playlist_title = playlist.title

        videos = {}

        for video in playlist.videos:

            try:
                video_title = video.title
                video_url = video.watch_url

                videos[video_title] = video_url

            except Exception as e:
                logging.error(f"Could not retrieve video details: {e}")

        return playlist_title, videos

    except Exception as e:
        logging.error(f"An error occurred: {e}")

        return None, None


def get_all_videos(channel_url):

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True
    }

    all_videos = []

    with YoutubeDL(ydl_opts) as ydl:

        result = ydl.extract_info(
            channel_url,
            download=False
        )

        if "entries" in result:

            channel_name = result["title"]

            all_videos.extend(result["entries"])

            video_links = {
                index + 1: (
                    video["title"],
                    video["url"]
                )
                for index, video in enumerate(all_videos)
            }

            return video_links, channel_name

        else:
            return None, None


def save_to_file(video_links, channel_name):

    sanitized_channel_name = re.sub(
        r"[^\w\s-]",
        "",
        channel_name
    ).strip().replace(" ", "_")

    filename = f"{sanitized_channel_name}.txt"

    with open(filename, "w", encoding="utf-8") as file:

        for number, (title, url) in video_links.items():

            if url.startswith("https://"):
                formatted_url = url

            elif "shorts" in url:
                formatted_url = f"https://www.youtube.com{url}"

            else:
                formatted_url = f"https://www.youtube.com/watch?v={url}"

            file.write(
                f"{number}. {title}: {formatted_url}\n"
            )

    return filename


async def download_video(url, cmd, name):

    global failed_counter

    download_cmd = (
        f'{cmd} '
        f'-R 25 '
        f'--fragment-retries 25 '
        f'--concurrent-fragments 8 '
        f'--external-downloader aria2c '
        f'--downloader-args "aria2c: -x 8 -s 8 -k 1M"'
    )

    print(download_cmd)

    logging.info(download_cmd)

    process = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if stdout:
        logging.info(stdout.decode())

    if stderr:
        logging.error(stderr.decode())

    if (
        "visionias" in cmd
        and process.returncode != 0
        and failed_counter <= 10
    ):

        failed_counter += 1

        await asyncio.sleep(5)

        return await download_video(
            url,
            cmd,
            name
        )

    failed_counter = 0

    try:

        if os.path.isfile(name):
            return name

        elif os.path.isfile(f"{name}.webm"):
            return f"{name}.webm"

        name = name.split(".")[0]

        if os.path.isfile(f"{name}.mkv"):
            return f"{name}.mkv"

        elif os.path.isfile(f"{name}.mp4"):
            return f"{name}.mp4"

        elif os.path.isfile(f"{name}.mp4.webm"):
            return f"{name}.mp4.webm"

        return name

    except FileNotFoundError:

        return name + ".mp4"


async def send_doc(
    bot: Client,
    m: Message,
    cc,
    ka,
    cc1,
    prog,
    count,
    name
):

    reply = await m.reply_text(
        f"Uploading » {name}"
    )

    await asyncio.sleep(1)

    start_time = time.time()

    await m.reply_document(
        ka,
        caption=cc1,
        progress=progress_bar,
        progress_args=(reply, start_time)
    )

    count += 1

    await reply.delete(True)

    await asyncio.sleep(1)

    os.remove(ka)


async def send_vid(
    bot: Client,
    m: Message,
    cc,
    filename,
    thumb,
    name,
    prog
):

    subprocess.run(
        f'ffmpeg -i "{filename}" -ss 00:00:10 -vframes 1 "{filename}.jpg"',
        shell=True
    )

    try:
        await prog.delete(True)
    except:
        pass

    reply = await m.reply_text(
        f"⥣ Uploading » {name}"
    )

    try:

        if thumb == "no":
            thumbnail = f"{filename}.jpg"

        else:
            thumbnail = thumb

    except Exception as e:

        await m.reply_text(str(e))

        thumbnail = None

    dur = int(duration(filename))

    start_time = time.time()

    try:

        await m.reply_video(
            video=filename,
            caption=cc,
            supports_streaming=True,
            thumb=thumbnail,
            duration=dur,
            progress=progress_bar,
            progress_args=(reply, start_time)
        )

    except Exception:

        await m.reply_document(
            document=filename,
            caption=cc,
            progress=progress_bar,
            progress_args=(reply, start_time)
        )

    if os.path.exists(filename):
        os.remove(filename)

    if os.path.exists(f"{filename}.jpg"):
        os.remove(f"{filename}.jpg")

    await reply.delete(True)
