import os
import asyncio
import subprocess
from pyrogram.errors import FloodWait

# ==============================
# DOWNLOAD VIDEO USING YT-DLP
# ==============================

async def download_video(url, cmd, name):
    try:
        print(f"\n📥 Downloading: {url}")
        print(f"⚙️ CMD: {cmd}")

        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            print("❌ Download Error:", stderr.decode())
            return None

        # Find downloaded file
        for file in os.listdir():
            if file.startswith(name):
                print(f"✅ Downloaded: {file}")
                return file

        return None

    except Exception as e:
        print(f"❌ Exception in download_video: {e}")
        return None


# ==============================
# DOWNLOAD FILE (DRIVE / DIRECT)
# ==============================

async def download(url, name):
    try:
        cmd = f'yt-dlp "{url}" -o "{name}.%(ext)s"'
        return await download_video(url, cmd, name)
    except Exception as e:
        print(f"❌ Error in download(): {e}")
        return None


# ==============================
# SEND VIDEO TO TELEGRAM
# ==============================

async def send_vid(bot, m, caption, filename, thumb, name, prog):
    try:
        if not filename or not os.path.exists(filename):
            await m.reply_text(f"❌ File not found: {name}")
            return

        await m.reply_video(
            video=filename,
            caption=caption,
            thumb=thumb if os.path.exists(thumb) else None,
            supports_streaming=True
        )

        os.remove(filename)

    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_vid(bot, m, caption, filename, thumb, name, prog)

    except Exception as e:
        await m.reply_text(f"❌ Upload Failed:\n{e}")


# ==============================
# PROGRESS BAR (OPTIONAL)
# ==============================

async def progress_bar(current, total):
    percent = current * 100 / total
    bar = "█" * int(percent // 10) + "░" * (10 - int(percent // 10))
    return f"[{bar}] {round(percent, 2)}%"
