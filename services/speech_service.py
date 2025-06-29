import requests
import logging
import re
import json
from datetime import datetime

class SpeechService:
    """Enhanced service for text-to-speech with predictive timing and better synchronization."""

    def __init__(self, api_key, reading_settings):
        """Initialize SpeechService with API key and enhanced reading settings."""
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.reading_settings = reading_settings

        # Enhanced timing prediction models
        self.timing_models = {
            'normal': {
                'base_word_duration': 180,  # ms per word
                'syllable_factor': 80,      # ms per syllable
                'punctuation_pause': 200,   # ms for punctuation
                'sentence_pause': 300,      # ms between sentences
                'complexity_multiplier': 1.2  # for complex words
            },
            'learning': {
                'base_word_duration': 600,  # Much longer for learning
                'syllable_factor': 200,     # More time per syllable
                'punctuation_pause': 400,   # Longer pauses
                'sentence_pause': 600,      # Much longer between sentences
                'complexity_multiplier': 1.5  # Even more time for complex words
            }
        }

        # Word complexity patterns
        self.complexity_patterns = {
            'sight_words': [
                'a', 'and', 'away', 'big', 'blue', 'can', 'come', 'down', 'find', 'for', 'funny',
                'go', 'help', 'here', 'I', 'in', 'is', 'it', 'jump', 'little', 'look', 'make',
                'me', 'my', 'not', 'one', 'play', 'red', 'run', 'said', 'see', 'the', 'three',
                'to', 'two', 'up', 'we', 'where', 'yellow', 'you', 'all', 'am', 'are', 'at'
            ],
            'phonics_patterns': {
                'simple_cvc': r'^[bcdfghjklmnpqrstvwxyz][aeiou][bcdfghjklmnpqrstvwxyz]$',
                'consonant_blends': r'(bl|br|cl|cr|dr|fl|fr|gl|gr|pl|pr|sc|sk|sl|sm|sn|sp|st|sw|tr)',
                'vowel_teams': r'(ai|ay|ea|ee|ie|oa|ow|ue)',
                'silent_e': r'[bcdfghjklmnpqrstvwxyz][aeiou][bcdfghjklmnpqrstvwxyz]e$'
            }
        }

    def get_voices(self):
        """Get available voices with enhanced filtering for children's content."""
        if not self.api_key:
            logging.warning("ElevenLabs API key not set")
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

            # Filter and prioritize voices suitable for children's content
            suitable_voices = []
            for voice in data['voices']:
                voice_name = voice['name'].lower()
                # Prioritize female, young, or gentle voices for children's stories
                if any(keyword in voice_name for keyword in ['female', 'young', 'child', 'gentle', 'sarah', 'alice', 'lily']):
                    suitable_voices.insert(0, {"id": voice['voice_id'], "name": voice['name']})
                else:
                    suitable_voices.append({"id": voice['voice_id'], "name": voice['name']})

            logging.info(f"Retrieved {len(suitable_voices)} voices, prioritized for children's content")
            return suitable_voices

        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            return []

    def analyze_text_for_timing(self, text, reading_mode="normal"):
        """Analyze text to predict precise timing for word highlighting."""

        # Get timing model for the reading mode
        timing_model = self.timing_models.get(reading_mode, self.timing_models['normal'])

        # Clean and prepare text
        clean_text = ' '.join(filter(bool, [line.strip() for line in text.split('\n')]))

        # Split into words while preserving punctuation context
        words_with_context = self._extract_words_with_context(clean_text)

        # Analyze each word for timing
        word_timings = []
        cumulative_time = 0

        for word_data in words_with_context:
            word = word_data['word']
            context = word_data['context']

            # Calculate base timing for this word
            word_duration = self._calculate_word_duration(word, timing_model, context)

            word_timings.append({
                'word': word,
                'start_time': cumulative_time,
                'duration': word_duration,
                'end_time': cumulative_time + word_duration,
                'complexity': self._classify_word_complexity(word),
                'has_punctuation': bool(context.get('punctuation')),
                'sentence_end': context.get('sentence_end', False)
            })

            cumulative_time += word_duration

            # Add extra pause for punctuation
            if context.get('punctuation'):
                pause_duration = timing_model['punctuation_pause']
                if context.get('sentence_end'):
                    pause_duration = timing_model['sentence_pause']
                cumulative_time += pause_duration

        total_duration = cumulative_time

        # Return comprehensive timing analysis
        return {
            'word_timings': word_timings,
            'total_estimated_duration': total_duration,
            'word_count': len(word_timings),
            'reading_mode': reading_mode,
            'average_word_duration': total_duration / len(word_timings) if word_timings else 0,
            'complexity_distribution': self._analyze_complexity_distribution(word_timings)
        }

    def _extract_words_with_context(self, text):
        """Extract words while preserving punctuation and sentence context."""
        # Pattern to match words with optional punctuation
        word_pattern = r'\b(\w+)([.!?,:;]*)\b'

        words_with_context = []
        matches = re.finditer(word_pattern, text)

        for match in matches:
            word = match.group(1)
            punctuation = match.group(2)

            context = {
                'punctuation': punctuation,
                'sentence_end': bool(re.search(r'[.!?]', punctuation)),
                'pause_punctuation': bool(re.search(r'[,:;]', punctuation))
            }

            words_with_context.append({
                'word': word,
                'context': context
            })

        return words_with_context

    def _calculate_word_duration(self, word, timing_model, context):
        """Calculate precise duration for a single word based on complexity."""

        # Base duration
        duration = timing_model['base_word_duration']

        # Add time based on syllables
        syllable_count = self._count_syllables(word)
        duration += syllable_count * timing_model['syllable_factor']

        # Adjust for word complexity
        complexity = self._classify_word_complexity(word)
        if complexity == 'complex':
            duration *= timing_model['complexity_multiplier']
        elif complexity == 'sight_word':
            duration *= 0.8  # Sight words are faster

        # Adjust for word length
        if len(word) > 7:
            duration *= 1.2
        elif len(word) <= 3:
            duration *= 0.9

        return int(duration)

    def _count_syllables(self, word):
        """Count syllables in a word using phonetic rules."""
        word = word.lower().strip(".,!?;:")

        # Handle empty or very short words
        if len(word) <= 1:
            return 1

        # Count vowel groups
        vowel_groups = re.findall(r'[aeiouy]+', word)
        syllable_count = len(vowel_groups)

        # Adjust for silent 'e'
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        # Special cases
        if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiou':
            syllable_count += 1

        # Minimum of 1 syllable
        return max(1, syllable_count)

    def _classify_word_complexity(self, word):
        """Classify word complexity for timing adjustments."""
        word_clean = word.lower().strip(".,!?;:")

        # Check if it's a sight word
        if word_clean in self.complexity_patterns['sight_words']:
            return 'sight_word'

        # Check phonics patterns
        if re.match(self.complexity_patterns['phonics_patterns']['simple_cvc'], word_clean):
            return 'simple'

        # Check for complex patterns
        if (re.search(self.complexity_patterns['phonics_patterns']['consonant_blends'], word_clean) or
            re.search(self.complexity_patterns['phonics_patterns']['vowel_teams'], word_clean) or
            len(word_clean) > 6):
            return 'complex'

        return 'regular'

    def _analyze_complexity_distribution(self, word_timings):
        """Analyze the distribution of word complexities in the text."""
        distribution = {'sight_word': 0, 'simple': 0, 'regular': 0, 'complex': 0}

        for word_timing in word_timings:
            complexity = word_timing['complexity']
            distribution[complexity] += 1

        total_words = len(word_timings)
        if total_words > 0:
            for key in distribution:
                distribution[key] = round((distribution[key] / total_words) * 100, 1)

        return distribution

    def generate_speech(self, text, voice_id, reading_mode="normal", reading_speed=None):
        """Generate speech with enhanced timing prediction."""
        if not self.api_key:
            logging.error("ElevenLabs API key not set")
            raise Exception("ElevenLabs API key not configured")

        try:
            # Analyze text for timing prediction
            timing_analysis = self.analyze_text_for_timing(text, reading_mode)

            # Clean the text for speech synthesis
            clean_text = ' '.join(filter(bool, [line.strip() for line in text.split('\n')]))

            # Get mode-specific settings
            mode_settings = self.reading_settings.get(reading_mode, self.reading_settings['normal'])

            # Calculate optimal speech settings
            speaking_rate = mode_settings['speaking_rate']
            client_playback_rate = mode_settings['playback_rate']

            # Adjust speaking rate based on text complexity
            complexity_dist = timing_analysis['complexity_distribution']
            if complexity_dist['complex'] > 30:  # If more than 30% complex words
                speaking_rate *= 0.9  # Slow down slightly

            # Ensure speaking rate is within ElevenLabs limits
            speaking_rate = max(0.5, min(2.0, speaking_rate))

            logging.info(f"Speech generation: mode={reading_mode}, estimated_duration={timing_analysis['total_estimated_duration']}ms")
            logging.info(f"Complexity distribution: {complexity_dist}")

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
                    "stability": 0.7,        # Higher stability for children
                    "similarity_boost": 0.8,  # Better voice consistency
                    "style": 0.1,            # Minimal style variation
                    "use_speaker_boost": True,
                    "speed": speaking_rate
                }
            }

            # Enhanced response headers with timing data
            response_headers = {
                'X-Reading-Mode': reading_mode,
                'X-Playback-Rate': str(client_playback_rate),
                'X-Word-Count': str(timing_analysis['word_count']),
                'X-Estimated-Duration': str(timing_analysis['total_estimated_duration']),
                'X-Average-Word-Duration': str(timing_analysis['average_word_duration']),
                'X-Complexity-Distribution': json.dumps(complexity_dist),
                'X-Timing-Data': json.dumps(timing_analysis['word_timings'][:10])  # First 10 words for debugging
            }

            response = requests.post(url, headers=headers, json=data, stream=True)

            if response.status_code != 200:
                error_message = f"ElevenLabs API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_message += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    error_message += f" - {response.text[:100]}"

                logging.error(error_message)
                response_headers['X-Error'] = error_message

                def empty_generator():
                    yield b""
                return empty_generator(), response_headers

            def generate():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk

            return generate(), response_headers

        except Exception as e:
            logging.error(f"Error generating speech: {e}")

            def empty_generator():
                yield b""

            response_headers = {
                'X-Error': f"Failed to generate speech: {str(e)}"
            }
            return empty_generator(), response_headers

    def get_timing_preview(self, text, reading_mode="normal"):
        """Get a preview of timing analysis without generating speech."""
        return self.analyze_text_for_timing(text, reading_mode)

    def validate_text_for_speech(self, text, reading_mode="normal"):
        """Validate and suggest optimizations for text before speech generation."""
        timing_analysis = self.analyze_text_for_timing(text, reading_mode)

        suggestions = []

        # Check for overly long text
        if timing_analysis['total_estimated_duration'] > 30000:  # 30 seconds
            suggestions.append("Text is quite long. Consider breaking into shorter segments for better attention span.")

        # Check complexity distribution
        complexity_dist = timing_analysis['complexity_distribution']
        if reading_mode == 'learning' and complexity_dist['complex'] > 25:
            suggestions.append("High complexity for learning mode. Consider simplifying some words.")

        # Check for very long words
        long_words = [wt for wt in timing_analysis['word_timings'] if len(wt['word']) > 8]
        if len(long_words) > 3:
            suggestions.append(f"Found {len(long_words)} very long words that might be challenging.")

        return {
            'timing_analysis': timing_analysis,
            'suggestions': suggestions,
            'ready_for_speech': len(suggestions) == 0
        }