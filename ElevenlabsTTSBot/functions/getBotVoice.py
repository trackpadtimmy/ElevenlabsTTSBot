import random
import json
import functions.sendBotMessage as sendBotMessage

class CustomVoice:
    def __init__(self, name, id):
        self.name = name
        self.id = id

f = open('customvoices.json')
data = json.load(f)

customVoices = []
for voice in data:
    customVoice = CustomVoice(voice["name"], voice["id"])
    customVoices.append(customVoice)

async def getRandomVoice(voicedata):
    randommax = len(voicedata)
    voicenum = random.randrange(0, randommax)
    voiceid = voicedata[voicenum]['voice_id']
    ttsvoice = voicedata[voicenum]['name'].capitalize()
    print(f"Random voice: {ttsvoice}")
    return ttsvoice, voiceid
'''
async def checkRandomVoice(name, voicedata, ctx):
    ttsvoice = name.capitalize()
    if ttsvoice == "Random":
        ttsvoice, voiceid = await getRandomVoice(voicedata)
    else:
        ttsvoice, voiceid = await getSelectedVoice(ttsvoice, voicedata, ctx)
    return ttsvoice, voiceid
'''
async def getSelectedVoice(voicename, voicedata, ctx):
    voiceid = None
    requested = voicename.casefold()

    for voice in voicedata:
        fullname = voice["name"]
        firstword = fullname.split(" - ", 1)[0].strip()

        if requested == firstword.casefold():
            voiceid = voice["voice_id"]
            return firstword, voiceid

    await sendBotMessage.sendVoiceNotFoundMessage(voicename, ctx)
    return None, None


async def setStability(stability):
    try:
        stablecheck = int(stability)
    except ValueError:
        print("Invalid stability value.")

    if stablecheck > 100:
        print("Stability cannot exceed 100. Defaulting to '50'.")
        stablecheck = 50
    elif stablecheck < 0:
        print("Stability cannot be less than 0. Defaulting to '50'.")
        stablecheck = 50
    return str(stablecheck / 100)

async def getCustomVoice(name):
    foundMatch = False
    for customVoice in customVoices:
        if name.capitalize() == customVoice.name.capitalize():
            foundMatch = True
            return customVoice.name.capitalize(), customVoice.id
    if foundMatch == False:
        return "", ""
        
async def getRandomStability():
    stability = round(random.uniform(0.01, 1.00),2)
    print(f"Random stability: {stability}")
    return stability