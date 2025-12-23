import asyncio
import random
import glob
import json
import os
import traceback
import discord
import requests
import functions.getBotResponse as getBotResponse
import functions.sendErrorMessage as sendErrorMessage
import functions.getFilePath as getFilePath
import functions.sendBotMessage as sendBotMessage
import functions.connectToVoice as connectToVoice
import functions.getBotVoice as getBotVoice
import functions.sendRequest as sendRequest
import functions.joinLeaveSounds as joinLeaveSounds
import functions.playVoice as playVoice

from discord.ext import commands
from discord.ext.commands import CommandNotFound

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    botdata_path = os.path.join(script_dir, 'botdata.json')
    with open(botdata_path, 'r') as jsonbotdata:
        botdata = json.load(jsonbotdata)
    SOUNDFILEDIR = 'soundfiles/'
    SOUNDBOARD_FILE ='soundboard.json'
    TOKEN = botdata['discord_token']
    PREFIX = botdata['command_prefix']
    SERVERID = botdata['discord_server_id']
    ROLEID = botdata['role_id']
    LEAVEJOINTTS = botdata.get('leave_join_sounds', False) == 'True'
    LEAVEJOINSTABILITY = round(random.uniform(0.01, 0.2), 2) if botdata['leave_join_stability'] == "random" else botdata['leave_join_stability']
    intents = discord.Intents.all()
    intents.members = True
    HELPDESCRIPTION = "These are the currently available commands!"
    TTSMODEL = 'eleven_multilingual_v2'
except Exception as e:
    print(f"There was an issue whilst reading the botdata file: {e}")

try:
    voicedata = json.loads(requests.get("https://api.elevenlabs.io/v1/voices?show_legacy=true").content)['voices']
except Exception as e:
    print(f"Something went wrong when getting available voices from elevenlabs: {e}")

try:
    bot = commands.Bot(command_prefix=PREFIX,
                    intents=intents,
                    case_insensitive=True,
                    help_command=commands.DefaultHelpCommand(no_category = 'Commands'),
                    description=HELPDESCRIPTION)
except Exception as e:
    print(f"Could not create the bot: {e}")

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!")
    statusmessage = "Type " + PREFIX + "help"
    activity = discord.Game(statusmessage)
    await bot.change_presence(status=discord.Status.online, activity=activity)

async def process_tts_request(ctx, name, stability, message: str):
    if (voice := await connectToVoice.connectToVoice(ctx, bot)) is not None:
        try:
            botmessage = message

            if ctx.command.name == "tts":
                    ttsvoice, voiceid = await getBotVoice.getSelectedVoice(name, voicedata, ctx)
                    stability = await getBotVoice.setStability(stability)
            elif ctx.command.name == "unstable":
                    ttsvoice, voiceid = await getBotVoice.getSelectedVoice(name, voicedata, ctx)
                    stability = await getBotVoice.setStability(0)
            elif ctx.command.name == "random":
                    ttsvoice, voiceid = await getBotVoice.getRandomVoice(voicedata)
                    stability = await getBotVoice.getRandomStability()
            elif ctx.command.name == "custom":
                    ttsvoice, voiceid = await getBotVoice.getCustomVoice(name)
                    if ttsvoice == "" or voiceid == "":
                        raise ValueError("Couldn't find a custom voice with the requested name. Please make sure the voice has been added to the customvoices.json file and the VoiceLabs library on your Elevenlabs profile.")
                    stability = await getBotVoice.setStability(stability)
            
            if name.lower() == "random":
                ttsvoice, voiceid = await getBotVoice.getRandomVoice(voicedata)

            if not ttsvoice or not voiceid:
                return

            response = await sendRequest.getSoundclip(voiceid, botmessage, TTSMODEL, stability)
            # Check for errors in the response
            # Specifically for quota exception, but handles others too
            try:
                data = response.json()
                if "detail" in data:
                    error = data['detail']
                    error_message = data['detail'].get('message', f"Unknown error from ElevenLabs: {data['detail']}")
                    await sendErrorMessage.sendErrorMessage(error_message, ctx, error)
                    return
            except Exception:
                pass    # No JSON response, likely a valid audio response

            credits_used = len(botmessage)
            audio_obj, audio_path = await getFilePath.getFilePath(ctx.message.author.name, response)

            await playVoice.playVoice(ttsvoice, botmessage, ctx.message.author.name, voice, audio_obj)
            await sendBotMessage.sendPlayingMessage(ctx, ctx.author.mention, ttsvoice, str(stability), botmessage, credits_used, audio_path)
        
        except (ValueError, UnboundLocalError) as error:
            botresponse = "valerror"
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendValueErrorMessage(errormessage, ctx, error)
        except Exception as error:
            botresponse = ""
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendValueErrorMessage(errormessage, ctx, error)

async def load_soundboard():
    try:
        if not os.path.exists(SOUNDBOARD_FILE):
            with open(SOUNDBOARD_FILE, 'w') as f:
                json.dump({"aliases": {}}, f, indent=4, sort_keys=True)
    except Exception as e:
        print(f"Could not create soundboard file: {e}")
    
    try:
        with open(SOUNDBOARD_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load soundboard file: {e}")
        return {}

async def save_soundboard(soundboard):
    try:
        with open(SOUNDBOARD_FILE, 'w') as f:
            json.dump(soundboard, f, indent=4, sort_keys=True)
    except Exception as e:
        print(f"Could not save soundboard file: {e}")

async def add_alias(ctx, label, *filename):
    try:
        label = label.lower()

        filename = " ".join(filename[:])
        filename = filename.replace(" ", "")
        if not filename.endswith(".mp3"):
            filename = filename + ".mp3"
        audiofile_path = SOUNDFILEDIR + filename
        if not os.path.isfile(audiofile_path):
            await sendBotMessage.sendBotMessage(ctx, f"File not found: {filename}")
            return
        soundboard = await load_soundboard()
        if label in soundboard["aliases"] and ctx.command.name == "alias":
            await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' already exists. Please run `{PREFIX}aliasw {label} {filename}` to overwrite it.")
            return
        elif label in soundboard["aliases"] and ctx.command.name == "aliasw":
            await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' already exists and will be overwritten.")
            soundboard["aliases"][label] = filename
            await save_soundboard(soundboard)
            await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' created for file '{filename}'")
        else:
            soundboard["aliases"][label] = filename
            await save_soundboard(soundboard)
            await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' created for file '{filename}'")
    
    except Exception as error:
        botresponse = ""
        errormessage = await getBotResponse.getBotResponse(botresponse)
        await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)

async def delete_alias(ctx, label):
    try:
        label = label.lower()
        soundboard = await load_soundboard()
        if label not in soundboard["aliases"]:
            await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' does not exist.")
            return
        del soundboard["aliases"][label]
        await save_soundboard(soundboard)
        await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' has been removed.")

    except Exception as error:
        botresponse = ""
        errormessage = await getBotResponse.getBotResponse(botresponse)
        await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)

async def list_aliases(ctx):
    try:
        soundboard = await load_soundboard()

        aliases = list(soundboard.get("aliases", {}).keys())
        if not aliases:
            await sendBotMessage.sendBotMessage(ctx, "No aliases found in the soundboard.")
            return

        count = len(aliases)
        header = f"{count} Soundboard Aliases:\n"
        max_length = 2000

        current_message = header

        for alias in aliases:
            # Add comma and space if this isn't the first alias in the message
            alias_text = ("" if current_message.endswith("\n") else ", ") + alias

            # If adding this alias would exceed Discord's limit, send current message
            if len(current_message) + len(alias_text) > max_length:
                await sendBotMessage.sendBotMessage(ctx, current_message, -1)

                # Start a new message without the header
                current_message = alias
            else:
                current_message += alias_text

        # Send any remaining aliases
        if current_message.strip():
            await sendBotMessage.sendBotMessage(ctx, current_message, -1)

    except Exception as error:
        botresponse = ""
        errormessage = await getBotResponse.getBotResponse(botresponse)
        await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)


async def play_file(ctx, *filename):
    if (voice := await connectToVoice.connectToVoice(ctx, bot)) is not None:
        try:
            filename = " ".join(filename[:])
            filename = filename.replace(" ", "")
            if not filename.endswith(".mp3"):
                filename = filename + ".mp3"
            audiofile_path = SOUNDFILEDIR + filename

            if not os.path.isfile(audiofile_path):
                await sendBotMessage.sendBotMessage(ctx, f"File not found: {filename}")
                return
            await playVoice.playAudiofile(voice, audiofile_path)
            await sendBotMessage.sendBotMessage(ctx, f"Playing audio file: {filename}")
        
        except (ValueError, UnboundLocalError) as error:
            botresponse = "valerror"
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendValueErrorMessage(errormessage, ctx, error)
        except Exception as error:
            botresponse = ""
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)

async def play_rand_file(ctx):
    if (voice := await connectToVoice.connectToVoice(ctx, bot)) is not None:
        try:
            list = glob.glob(SOUNDFILEDIR + "*.mp3")
            if not list:
                await sendBotMessage.sendBotMessage(ctx, "No audio files found in the soundfiles directory.")
                return
            audiofile_path = str(random.choice(list))
            filename = os.path.basename(audiofile_path)

            await playVoice.playAudiofile(voice, audiofile_path)
            await sendBotMessage.sendBotMessage(ctx, f"Playing audio file: {filename}")
        
        except (ValueError, UnboundLocalError) as error:
            botresponse = "valerror"
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendValueErrorMessage(errormessage, ctx, error)
        except Exception as error:
            botresponse = ""
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)

async def play_alias(ctx, label):
    label = label.lower()
    soundboard = await load_soundboard()
    if label not in soundboard["aliases"]:
        await sendBotMessage.sendBotMessage(ctx, f"Alias '{label}' does not exist.")
        return
    filename = soundboard["aliases"][label]
    await play_file(ctx, filename)

async def upload_file(ctx, *filename):
    if (voice := await connectToVoice.connectToVoice(ctx, bot)) is not None:
        try:
            filename = " ".join(filename[:])
            filename = filename.replace(" ", "")
            if not filename.endswith(".mp3"):
                filename = filename + ".mp3"
            audiofile_path = SOUNDFILEDIR + filename

            if not os.path.isfile(audiofile_path):
                await sendBotMessage.sendBotMessage(ctx, f"File not found: {filename}")
                return
            
            await sendBotMessage.sendUploadMessage(ctx, audiofile_path)

        except Exception as error:
            botresponse = ""
            errormessage = await getBotResponse.getBotResponse(botresponse)
            await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)

@bot.command(pass_context=True, name="tts", help=f"Use tts Voice message. `{PREFIX}tts Adam 50 Hello World` param: <Voice or random> <Stability 1-100> <Message>")
async def _tts(ctx, 
               name: str = commands.parameter(description="The name of the voice you want to use"), 
               stability: str = commands.parameter(description="The stability of the voice, a number between 0-100"), 
               *,
               message: str):
    await process_tts_request(ctx, name, stability, message)

@bot.command(pass_context=True, name="unstable", help=f"TTS with 0 stability, for making crazy stuff! `{PREFIX}tts Adam Hello World` param: <Voice or random> <Message>")
async def _unstable(ctx, 
                    name: str = commands.parameter(description="The name of the voice you want to use. Or put Random."), 
                    *,
                    message: str):
    await process_tts_request(ctx, name, 0, message)

@bot.command(pass_context=True, name="random", help=f"Takes a random voice and stability. `{PREFIX}random Hello World` param: <Message>")
async def _random(ctx, *, message: str):
    await process_tts_request(ctx, "random", 0, message)

@bot.command(pass_context=True, name="custom", help=f"Custom voice tts. `{PREFIX}custom Adam 50 Hello World` param: <Voice or random> <Stability 1-100> <Message>")
async def _custom(ctx, 
               name: str = commands.parameter(description="The name of the voice you want to use"), 
               stability: str = commands.parameter(description="The stability of the voice, a number between 0-100"), 
               *,
               message: str):
    await process_tts_request(ctx, name, stability, message)

@bot.command(pass_context=True, name="play", help=f"Play a specific audio file from the audio folder. `{PREFIX}play username123` param: <Filename>")
async def _play(ctx, *filename):
    await play_file(ctx, *filename)

@bot.command(pass_context=True, name="playrand", help=f"Play a random audio file from the audio folder. `{PREFIX}playrand`")
async def _playrand(ctx):
    await play_rand_file(ctx)

@bot.command(pass_context=True, name="alias", help=f"Creates a label for a sound file in the soundboard. Lowercase, no spaces allowed.`{PREFIX}alias label username123` param: <Label> <Filename>")
async def _alias(ctx,
                 label: str = commands.parameter(description="The label you want to assign to the sound file"),
                 *filename):
    await add_alias(ctx, label, *filename)

@bot.command(pass_context=True, name="aliasw", help=f"Creates a label for a sound file in the soundboard. Lowercase, no spaces allowed, overwrites by default. `{PREFIX}alias label username123` param: <Label> <Filename>")
async def _aliasw(ctx,
                  label: str = commands.parameter(description="The label you want to assign to the sound file"),
                  *filename):
    await add_alias(ctx, label, *filename)

@bot.command(pass_context=True, name="unalias", help=f"Removes a name from the soundboard. `{PREFIX}unalias label` param: <Label>")
async def _unalias(ctx,
                   label: str = commands.parameter(description="The label of the sound file to remove")):
    await delete_alias(ctx, label)

@bot.command(pass_context=True, name="list", help=f"Lists all soundboard aliases. `{PREFIX}list`")
async def _list(ctx):
    await list_aliases(ctx)

@bot.command(pass_context=True, name="soundboard", aliases=["sb"], help=f"Plays a sound from the soundboard by its label. `{PREFIX}soundboard label` param: <Label>")
async def _soundboard(ctx,
                      label: str = commands.parameter(description="The label of the sound file to play")):
    await play_alias(ctx, label)

@bot.command(pass_context=True, name="voices", help="Displays the available voices for use")
async def _voices(ctx):
    await sendRequest.getAvailableVoices(ctx, voicedata)

@bot.command(pass_context=True, name="upload", aliases=["up"], help=f"Uploads an audio file from the soundfiles directory. `{PREFIX}upload filename` param: <Filename>")
async def _upload(ctx, *filename):
    await upload_file(ctx, *filename)

@bot.command(pass_context=True, name="quota", help="Displays the remaining quota for use")
async def _quota(ctx):
    await sendRequest.getQuota(ctx)

@bot.command(pass_context=True, name="stop", help="Stops the current sound clip or loop")
async def _stop(ctx):
    await playVoice.stopVoice(ctx, bot)

@bot.command(pass_context=True, name="join", help="Joins the voice channel")
async def _join(ctx):
    await connectToVoice.connectToVoice(ctx, bot, "joincommand")

@bot.command(pass_context=True, name="leave", help="Leaves the voice channel")
async def _leave(ctx):
    await connectToVoice.leaveVoice(ctx)

@bot.event
async def on_voice_state_update(member, before, after):
    '''For sending TTS messages when users join and leave the voice channel'''
    if ROLEID in [y.id for y in member.roles] and LEAVEJOINTTS is True :
        try:
            voice = discord.utils.get(
                bot.voice_clients, guild=member.guild
            )
            if after.channel is not None:
                channel = member.voice.channel
                if voice is None:
                    voice = await channel.connect()
            #leaving sounds
            if after.channel is None and before.channel == voice.channel:
                audiofile = await joinLeaveSounds.checkEasterEgg("leave")
                if audiofile == "":
                    username = await joinLeaveSounds.getUsername(member)
                    botmessage = await joinLeaveSounds.getLeaveMessage(username)
                    ttsvoice, voiceid = await getBotVoice.getRandomVoice(voicedata)
                    response = await sendRequest.getSoundclip(voiceid, botmessage, TTSMODEL, LEAVEJOINSTABILITY)
                    audiofile = await getFilePath.getFilePath(member.name + "_leave", response)
                
                await playVoice.playLeaveVoice(ttsvoice, botmessage, member.name, voice, audiofile)
            #joining sounds
            elif before.channel is None and after.channel is voice.channel or before.channel is not voice.channel and after.channel is voice.channel:
                
                audiofile = await joinLeaveSounds.checkEasterEgg("join")
                if audiofile == "":
                    username = await joinLeaveSounds.getUsername(member)
                    botmessage = await joinLeaveSounds.getJoinMessage(username)
                    ttsvoice, voiceid = await getBotVoice.getRandomVoice(voicedata)
                    response = await sendRequest.getSoundclip(voiceid, botmessage, TTSMODEL, LEAVEJOINSTABILITY)
                    audiofile = await getFilePath.getFilePath(member.name + "_join", response)

                await playVoice.playJoinVoice(ttsvoice, botmessage, member.name, voice, audiofile)
        except (ValueError, UnboundLocalError, AttributeError, TypeError, Exception) as e:
            print(f"There was an error with leave/join sounds: {e}")

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.content.startswith(PREFIX):
        asyncio.create_task(delete_message(message))

async def delete_message(message):
    await asyncio.sleep(30)
    try:
        await message.delete()
    except:
        pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        botresponse = "missingarg"
        errormessage = await getBotResponse.getBotResponse(botresponse)
        await sendErrorMessage.sendErrorMessage(errormessage, ctx, error)
    elif isinstance(error, commands.BadArgument):
        botresponse = "valerror"
        errormessage = await getBotResponse.getBotResponse(botresponse)
        await sendErrorMessage.sendValueErrorMessage(errormessage, ctx, error)
    traceback.print_exception(type(error), error, error.__traceback__)
    
try:
    bot.run(TOKEN)
except Exception as e:
    print("Bot couldn't run: {e}")
finally:
    print("Bot has stopped running. Leaving...")