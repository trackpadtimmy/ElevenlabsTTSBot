import requests
import json
import os
import functions.sendBotMessage as sendBotMessage

try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    botdata_path = os.path.join(script_dir, '..', 'botdata.json')

    with open(botdata_path, 'r') as jsonbotdata:
        botdata = json.load(jsonbotdata)
    APIKEY = botdata['elevenlabs_api_key']
except Exception as e:
    print(f"Could not get API Key from botdata.json, make sure it's added properly: {e}")

headers = {
  "Accept": "audio/mpeg",
  "Content-Type": "application/json",
  "xi-api-key": APIKEY
}

async def getSoundclip(voiceid, botmessage, TTSMODEL, stability):
    try:
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + voiceid
        data = {
            "text": botmessage,
            "model_id": TTSMODEL,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": stability
            }
        }
        response = requests.post(url, json=data, headers=headers, timeout=10)
    except Exception as e:
        print(f"There was a problem sending the request to Elevenlabs: {e}")
    return response

async def getAvailableVoices(ctx, voicedata):
    try:
        # Extract first word of each voice name
        names = {
            voice["name"].split(" - ", 1)[0].strip().capitalize()
            for voice in voicedata
        }

        namelist = sorted(names)
        message = ", ".join(namelist)

        botmessage = f"These are the available TTS voices:\n{message}"
        await sendBotMessage.sendBotMessage(ctx, botmessage, -1)

    except Exception as e:
        print(f"Could not fetch available voices: {e}")

async def getQuota(ctx):
    try:
        url = "https://api.elevenlabs.io/v1/user"
        apiheaders = {
        "Accept": "application/json",
        "xi-api-key": APIKEY
        }
        response = requests.get(url, headers=apiheaders, timeout=10)
        data = response.json()
        listtest = json.loads(response.text)
        remainingquota = int(listtest["subscription"]["character_limit"]) - int(listtest["subscription"]["character_count"])
        botmessage =("Your remaining quota for this month is: " + str(remainingquota) + " characters.")
        await sendBotMessage.sendBotMessage(ctx, botmessage)
    except:
        print(f"Error fetching quota information: {data.get('detail', data)}")
        botmessage = (f"Error fetching quota information: {data.get('detail', data)}")
        await sendBotMessage.sendBotMessage(ctx, botmessage, 15)