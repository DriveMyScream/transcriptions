import requests

headers = {
    'x-gladia-key': 'f73673b2-2809-4232-9142-9b210bae0231',
}

files = {
    'audio_url': (None, 'https://github.com/DriveMyScream/sample/raw/main/Swahili_Language.wav'),
    'toggle_diarization': (None, 'true'),
}

response = requests.post('https://api.gladia.io/audio/text/audio-transcription/', headers=headers, files=files)
print(response.json())