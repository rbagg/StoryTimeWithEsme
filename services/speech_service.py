import requests
import logging

class SpeechService:
    """Service for text-to-speech using ElevenLabs API."""

    def __init__(self, api_key, reading_settings):
        """Initialize SpeechService with API key and reading speed settings.

        Args:
            api_key (str): ElevenLabs API key
            reading_settings (dict): Dictionary of reading speed settings
        """
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.reading_settings = reading_settings

    def get_voices(self):
        """Get available voices from ElevenLabs API.

        Returns:
            list: List of voice objects with id and name

        Raises:
            Exception: If API request fails
        """
        if not self.api_key:
            logging.warning("ElevenLabs API key not set - cannot retrieve voices")
            return []

        try:
            url = f"{self.base_url}/voices"
            headers = {
                "Accept": "application/json",
                "xi-api-key": self.api_key
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Log voices to console for debugging
            logging.info(f"Retrieved {len(data['voices'])} voices from ElevenLabs API")
            for voice in data['voices']:
                logging.debug(f"Voice: {voice['name']} (ID: {voice['voice_id']})")

            # Format voice data for the frontend
            voice_options = [{"id": voice['voice_id'], "name": voice['name']} for voice in data['voices']]
            return voice_options

        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            raise

    def generate_speech(self, text, voice_id, reading_mode="normal", reading_speed=1.0):
        """Generate speech from text.

        Args:
            text (str): Text to convert to speech
            voice_id (str): ID of the voice to use
            reading_mode (str): Reading mode (normal or learning)
            reading_speed (float): Speed multiplier for reading

        Returns:
            tuple: (generator, headers) Stream of audio data and response headers

        Raises:
            Exception: If API request fails
        """
        if not self.api_key:
            logging.error("ElevenLabs API key not set - cannot generate speech")
            raise Exception("ElevenLabs API key not configured")

        try:
            # Clean the text
            clean_text = ' '.join(filter(bool, [line.strip() for line in text.split('\n')]))

            # Get settings for current mode
            if reading_mode not in self.reading_settings:
                logging.warning(f"Unknown reading mode: {reading_mode}, falling back to 'normal'")
                reading_mode = "normal"

            mode_settings = self.reading_settings[reading_mode]

            # Apply speed multiplier to base speaking rate
            effective_speaking_rate = mode_settings['speaking_rate'] * float(reading_speed)

            # Clamp to reasonable range for ElevenLabs API (0.25 to 4.0)
            effective_speaking_rate = max(0.25, min(4.0, effective_speaking_rate))

            # Log detailed information for debugging
            logging.info(f"Speech synthesis: mode={reading_mode}, speed={reading_speed}, effective_rate={effective_speaking_rate}")

            url = f"{self.base_url}/text-to-speech/{voice_id}/stream"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }

            data = {
                "text": clean_text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.6,
                    "similarity_boost": 0.7,
                    "style": 0.0,
                    "use_speaker_boost": True,
                    "speed": effective_speaking_rate
                }
            }

            # Add custom headers for the client-side to use
            response_headers = {
                'X-Reading-Mode': reading_mode,
                'X-Effective-Rate': str(effective_speaking_rate),
                'X-Playback-Rate': str(mode_settings['playback_rate'])
            }

            # Make the API request
            response = requests.post(url, headers=headers, json=data, stream=True)
            response.raise_for_status()

            # Return a generator that yields chunks of audio data
            def generate():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return generate(), response_headers

        except Exception as e:
            logging.error(f"Error generating speech: {e}")
            raise Exception(f"Failed to generate speech: {str(e)}")