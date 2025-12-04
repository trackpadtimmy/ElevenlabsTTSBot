import asyncio
import os
from discord import File

async def sendBotMessage(ctx, botmessage):
    try:
        botmessage = await ctx.send(botmessage)
        await asyncio.sleep(15)
        await botmessage.delete()
    except Exception as e:
        print(f"Couldn't send message: {e}")

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

        '''
        await asyncio.sleep(15)
        await botmessage.delete()
        '''
    except Exception as e:
        print(f"Couldn't send message: {e}")

async def sendVoiceNotFoundMessage(voicename, ctx):
    try:
        infomessage = f"Couldn't find a voice named {voicename}"
        botmessage = await ctx.send(infomessage)
        await asyncio.sleep(15)
        await botmessage.delete()
    except Exception as e:
        print(f"Couldn't send message: {e}")