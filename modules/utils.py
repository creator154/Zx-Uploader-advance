import time 
import asyncio 
 
from datetime import timedelta 
from pyrogram.errors import FloodWait 
from vars import CREDIT 
 
 
class Timer: 
 
    def init(self, time_between=3): 
 
        self.start_time = time.time() 
        self.time_between = time_between 
 
    def can_send(self): 
 
        if time.time() > ( 
            self.start_time + self.time_between 
        ): 
 
            self.start_time = time.time() 
 
            return True 
 
        return False 
 
 
timer = Timer() 
 
 
def hrb(value, digits=2): 
 
    if value is None: 
        return None 
 
    units = ["B", "KB", "MB", "GB", "TB"] 
 
    for unit in units: 
 
        if value < 1024: 
            return f"{value:.{digits}f} {unit}" 
 
        value /= 1024 
 
    return f"{value:.{digits}f} PB" 
 
 
def hrt(seconds): 
 
    seconds = int(seconds) 
 
    periods = [ 
 
        ('d', 86400), 
        ('h', 3600), 
        ('m', 60), 
        ('s', 1) 
 
    ] 
 
    result = [] 
 
    for suffix, length in periods: 
 
        value = seconds // length 
 
        if value > 0: 
 
            seconds = seconds % length 
 
            result.append(f"{value}{suffix}") 
 
    return " ".join(result[:2]) 
 
 
async def progress_bar(current, total, reply, start): 
 
    if not timer.can_send(): 
        return 
 
    now = time.time() 
 
    elapsed = now - start 
 
    if elapsed < 1: 
        return 
 
    speed = current / elapsed 
 
    percentage = current * 100 / total 
 
    eta = ( 
        (total - current) / speed 
        if speed > 0 else 0 
    ) 
 
    completed = int(percentage / 10) 
 
    bar = ( 
        "▓" * completed 
        + "░" * (10 - completed) 
    ) 
 
    msg = ( 
        f"╭━━〔 ⚡ 𝐔𝐋𝐓𝐑𝐀 𝐔𝐏𝐋𝐎𝐀𝐃 ⚡ 〕━━╮\n\n" 
        f"┃ [{bar}] {percentage:.1f}%\n\n" 
        f"┣ 🚀 Speed » {hrb(speed)}/s\n" 
        f"┣ 📦 Uploaded » {hrb(current)}\n" 
        f"┣ 💾 Size » {hrb(total)}\n" 
        f"┣ ⏳ ETA » {hrt(eta)}\n" 
        f"┣ 🕒 Elapsed » {hrt(elapsed)}\n\n" 
        f"╰━━〔 ✦ {CREDIT} ✦ 〕━━╯" 
    ) 
 
    try: 
 
        await reply.edit(msg) 
 
    except FloodWait as e: 
 
        await asyncio.sleep(e.value) 
 
    except: 
        pass
