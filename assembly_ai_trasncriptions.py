import boto3
import requests
import time
import uuid
import os
from pathlib import Path
from urllib.parse import unquote, urlparse, quote
import moviepy.editor as mp
from fastapi import FastAPI, Body
from pydantic import BaseModel, HttpUrl
from pathlib import Path


BUCKET_NAME = "meetminutes-audio"
FOLDER_NAME = "audio_transcript"
s3 = boto3.client('s3',
                 aws_access_key_id='AKIA3KSMPS5ZLO5FLU6I',
                 aws_secret_access_key='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')

ASSEMBLYAI_API_KEY = "04e7afe730d24159bdb79bbb33a59f20"
os.environ['AWS_ACCESS_KEY_ID'] = 'AKIA3KSMPS5ZLO5FLU6I'
os.environ['AWS_SECRET_ACCESS_KEY'] = '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'


app = FastAPI()

def assemblyai_transcript(audio_url, language_code):
    endpoint = "https://api.assemblyai.com/v2/transcript"
    payload = {
        "audio_url": audio_url,
        "language_code": language_code,
        "speaker_labels": True,
        "punctuate": True,
        'format_text': True,
        
    }
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
    }

    response = requests.post(endpoint, json=payload, headers=headers)
    result = response.json()
    try:
        transcript_id = result['id']
    except Exception as e:
        print(e)
        print(result)
        return "Error"
    return transcript_id

def get_transcript(transcript_id):
    endpoint = f'https://api.assemblyai.com/v2/transcript/{transcript_id}'
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    while True:
        response = requests.get(endpoint, headers=headers)
        result = response.json()
        if result['status'] in ('completed', 'error'):
            return result
        time.sleep(10)  # Wait for 10 seconds before polling again


def milliseconds_to_vtt_timestamp(milliseconds):
    milliseconds = int(milliseconds)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def assemblyai_to_vtt(response):
    vtt_content = "WEBVTT\n\n"
    utterances = response['utterances']
    for utterance in utterances:
        start_time = utterance['start']
        end_time = utterance['end']
        start_time = milliseconds_to_vtt_timestamp(start_time)
        end_time = milliseconds_to_vtt_timestamp(end_time)
        speaker = utterance['speaker']
        text = utterance['text']
        vtt_content += f"{start_time} --> {end_time}\n"
        vtt_content += f"Speaker {speaker}: {text}\n\n"
    return vtt_content


def upload_file_object_to_s3(file, VTT_FILENAME):
    object_name = VTT_FILENAME
    s3.put_object(Body=file, Bucket = BUCKET_NAME, Key = f'{FOLDER_NAME}/{object_name}')
    transcript_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{FOLDER_NAME}/{object_name}'
    transcript_url = quote(transcript_url, safe=':/')
    return transcript_url

class InputData(BaseModel):
    audio_url: str


@app.post("/get_transcription")
def get_transcription(input_data: InputData = Body(...), language_code: str = "en"):
    try:
        audio_url = input_data.audio_url
        VTT_FILENAME = Path(unquote(urlparse(audio_url).path)).stem + '.vtt'
        transcript_id = assemblyai_transcript(audio_url=audio_url, language_code=language_code)
        transcription_result = get_transcript(transcript_id=transcript_id)
        vtt = assemblyai_to_vtt(transcription_result)
        transcript_url = upload_file_object_to_s3(vtt, VTT_FILENAME)
        print("Item added to the table")
        op_response = {'message': 'completed', 'body': str(transcript_url)}

    except Exception as e:
        print(e)
        op_response = {'message': 'error', 'body': str(e)}

    return op_response


@app.get("/")
async def root():
    return {"message": "Service Running"}

class Inputs(BaseModel):
    media_url: HttpUrl

@app.post("/media_duration")
def get_media_duration(inputs: Inputs):
    print('started')
    tmp_dir = Path(f'tmp/{uuid.uuid4()}')
    tmp_dir.mkdir(parents=True, exist_ok=True)
    media_url = inputs.media_url
    print(media_url)
    
#    try:
    # Get file from S3 url and save to the temporary directory
    response = requests.get(media_url, stream=True)
    local_path = tmp_dir / media_url.split("/")[-1]
    local_path.write_bytes(response.content)

    # Use MoviePy to get the duration
    try: 
        clip = mp.VideoFileClip(str(local_path))
    except:
        clip = mp.AudioFileClip(str(local_path))
    duration = clip.duration
    clip.close()

    # Delete the file
    local_path.unlink()

    # Delete the temporary directory
    tmp_dir.rmdir()

    return {"duration": duration}

    # except Exception as e:
    #     # In case of any exception, cleanup the temporary directory
    #     for file in tmp_dir.iterdir():
    #         file.unlink()
    #     tmp_dir.rmdir()
    #     return {"error": str(e)}