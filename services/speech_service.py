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
            return []

    def generate_speech(self, text, voice_id, reading_mode="normal", reading_speed=None):
        """Generate speech from text.

        Args:
            text (str): Text to convert to speech
            voice_id (str): ID of the voice to use
            reading_mode (str): Reading mode (normal or learning)
            reading_speed (float, optional): Deprecated parameter kept for backward compatibility

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

            # Calculate word count for timing estimation
            word_count = len(clean_text.split())

            # Use mode-specific speaking rate
            effective_speaking_rate = mode_settings['speaking_rate']

            # Learning mode needs special handling due to ElevenLabs API limitations
            # ElevenLabs minimum speed is 0.5, but we want our learning mode to be slower
            if reading_mode == 'learning' and effective_speaking_rate < 0.7:
                # Use 0.7 as minimum ElevenLabs speed for quality
                # and let the browser handle additional slowdown
                client_playback_rate = mode_settings['playback_rate']
                effective_speaking_rate = 0.7  # Minimum viable for ElevenLabs
            else:
                client_playback_rate = mode_settings['playback_rate']

            # Log detailed information for debugging
            logging.info(f"Speech synthesis: mode={reading_mode}")
            logging.info(f"Effective API rate: {effective_speaking_rate}, Client playback rate: {client_playback_rate}")

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
                'X-Playback-Rate': str(client_playback_rate),
                'X-Word-Count': str(word_count)
            }

            # Make the API request
            response = requests.post(url, headers=headers, json=data, stream=True)

            # Check for API errors
            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    error_message += f" - {response.text[:100]}"

                logging.error(error_message)

                # Return empty generator with error info
                def empty_generator():
                    yield b""

                response_headers['X-Error'] = error_message
                return empty_generator(), response_headers

            # Return a generator that yields chunks of audio data
            def generate():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return generate(), response_headers

        except Exception as e:
            logging.error(f"Error generating speech: {e}")

            # Return an empty audio stream with error message in headers
            def empty_generator():
                yield b""

            response_headers = {
                'X-Error': f"Failed to generate speech: {str(e)}"
            }
            return empty_generator(), response_headers