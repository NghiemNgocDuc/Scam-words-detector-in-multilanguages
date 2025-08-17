import speech_recognition as sr
from risk_service import RiskService

# Initialize services
risk_service = RiskService()
recognizer = sr.Recognizer()
mic = sr.Microphone()

print("Listening for scam-related speech...")

with mic as source:
    recognizer.adjust_for_ambient_noise(source)

    while True:
        try:
            print("Waiting for speech...")
            audio = recognizer.listen(source, timeout=5)

            # Transcribe speech
            text = recognizer.recognize_google(audio, language="vi-VN")  # or "en-US"
            print(f"Heard: {text}")

            # Send transcript to RiskService
            risk_service.on_transcript_event(
                text=text,
                lang="vi",         # or "en", "fr", etc.
                is_final=True      # marks this as a complete utterance
                # audio_path=...   # optional: for spoof detection
            )

        except sr.WaitTimeoutError:
            print("No speech detected...")
        except sr.UnknownValueError:
            print("Couldn't understand audio...")
        except sr.RequestError as e:
            print(f"API error: {e}")
