import asyncio
import os
from discord import File

async def sendBotMessage(ctx, botmessage, delay=30):
    try:
        botmessage = await ctx.send(botmessage)
        if delay > 0:
            asyncio.create_task(deleteBotMessage(botmessage, delay))
    except Exception as e:
        print(f"Couldn't send message: {e}")

async def deleteBotMessage(botmessage, delay):
    await asyncio.sleep(delay)
    try:
        await botmessage.delete()
    except:
        pass

async def sendPlayingMessage(ctx, ttsuser, ttsvoice, stabstr, botmessage, credits_used, audiofile_path):
    try:
        stability = float(stabstr)
        infomessage = (
            f"Author: {ttsuser}\n"
            f"Voice: {ttsvoice.capitalize()}\n"
            f"Stability: {int(stability * 100)}%\n"
            f"Message: {botmessage}\n"
            f"Credits used: {credits_used}"
        )
        audio = File(audiofile_path, filename=os.path.basename(audiofile_path))
        botmessage = await ctx.send(content=infomessage, file=audio)
    except Exception as e:
        print(f"Couldn't send message: {e}")

async def sendUploadMessage(ctx, audiofile_path):
    try:
        infomessage = ""
        audio = File(audiofile_path, filename=os.path.basename(audiofile_path))
        await ctx.send(content=infomessage, file=audio)
    except Exception as e:
        print(f"Couldn't send message: {e}")

async def sendVoiceNotFoundMessage(voicename, ctx):
    try:
        infomessage = f"Couldn't find a voice named {voicename}"
        botmessage = await ctx.send(infomessage)
        await asyncio.sleep(30)
        await botmessage.delete()
    except Exception as e:
        print(f"Couldn't send message: {e}")