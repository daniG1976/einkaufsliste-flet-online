"""

Ideen:
    
    - Kalenderfunktion, wo man Listen für verschiedene Wochentage anlegen kann
    
    - Spracheingabe: auf dem PC: 
        def record_audio(duration=5, fs=16000):
            print("Aufnahme startet...")
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()
            print("Aufnahme beendet.")
            return audio.flatten().tobytes()
    
    
        def speech_to_text(audio_bytes):
            client = speech.SpeechClient()

            audio = speech.RecognitionAudio(content=audio_bytes)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="de-DE"
            )

            response = client.recognize(config=config, audio=audio)

            # Gibt den erkannten Text zurück
            if response.results:
                return response.results[0].alternatives[0].transcript
            return ""

        def speech_button_clicked(e):
            audio = record_audio(duration=2)  # 5 Sekunden aufnehmen
            text = speech_to_text(audio)
            if text:
                text1.value = text  # text1 ist dein TextField im Dialog
                page.update()
    
    - Animationen und Sound 
    
    
    
    
    
"""