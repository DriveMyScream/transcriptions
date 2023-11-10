import time
import logging
import azure.cognitiveservices.speech as speechsdk

speech_key, service_region = "8ede1198316842f583dd2591c7271231", "centralindia"
audio_file = "Arabic_Language.wav"

logger = logging.getLogger('my_logger')

def process():
    logger.debug("Speech to text request received")
    audio_filepath = audio_file
    locale = "ar-SA" # Change as per requirement

    logger.debug(audio_filepath)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_filepath) 
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.request_word_level_timestamps()
    speech_config.speech_recognition_language = locale
    speech_config.output_format = speechsdk.OutputFormat(1)
    # speech_config.add_target_language("en")

    # Creates a recognizer with the given settings
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Variable to monitor status
    done = False

    # Service callback for recognition text 
    transcript_display_list = []
    transcript_ITN_list = []
    confidence_list = []
    words = []
    def parse_azure_result(evt):
        import json
        response = json.loads(evt.result.json)
        transcript_display_list.append(response['DisplayText'])
        confidence_list_temp = [item.get('Confidence') for item in response['NBest']]
        max_confidence_index = confidence_list_temp.index(max(confidence_list_temp))
        confidence_list.append(response['NBest'][max_confidence_index]['Confidence'])
        transcript_ITN_list.append(response['NBest'][max_confidence_index]['ITN'])
        words.extend(response['NBest'][max_confidence_index]['Words'])
        logger.debug(evt)

    # Service callback that stops continuous recognition upon receiving an event `evt`
    def stop_cb(evt):
        print('CLOSING on {}'.format(evt))
        speech_recognizer.stop_continuous_recognition()
        nonlocal done
        done = True

        # Do something with the combined responses
        print(transcript_display_list)
        print(confidence_list)
        print(words)

    # Connect callbacks to the events fired by the speech recognizer
    speech_recognizer.recognizing.connect(lambda evt: logger.debug('RECOGNIZING: {}'.format(evt)))
    speech_recognizer.recognized.connect(parse_azure_result)
    speech_recognizer.session_started.connect(lambda evt: logger.debug('SESSION STARTED: {}'.format(evt)))
    speech_recognizer.session_stopped.connect(lambda evt: logger.debug('SESSION STOPPED {}'.format(evt)))
    speech_recognizer.canceled.connect(lambda evt: logger.debug('CANCELED {}'.format(evt)))
    # stop continuous recognition on either session stopped or canceled events
    speech_recognizer.session_stopped.connect(stop_cb)
    speech_recognizer.canceled.connect(stop_cb)

    # Start continuous speech recognition
    logger.debug("Initiating speech to text")
    speech_recognizer.start_continuous_recognition()
    while not done:
        time.sleep(.5)

process()