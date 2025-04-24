import re
import logging
from pathlib import Path

class ReaderService:
    """Service for processing text for the 'Learn to Read' mode."""

    def __init__(self):
        """Initialize ReaderService."""
        # Load reader optimization prompt if needed
        try:
            self.reader_prompt_template = Path("prompts/reader_prompt.txt").read_text()
        except Exception as e:
            logging.warning(f"Could not load reader prompt template: {e}")
            self.reader_prompt_template = ""

    def process_story_text(self, text):
        """Process story text into structured format with stanzas and lines.

        Args:
            text (str): Raw story text

        Returns:
            list: List of stanza dictionaries with index and lines
        """
        if not text:
            return []

        # Replace any escaped newlines with actual newlines
        text = text.replace('\\\\n', '\n').replace('\\n', '\n')

        # Split text into stanzas
        stanzas = [stanza.strip() for stanza in text.split('\n\n') if stanza.strip()]

        processed_stanzas = []
        for index, stanza in enumerate(stanzas):
            # Remove trailing newlines and whitespace from each line
            lines = [line.rstrip('\n').strip() for line in stanza.split('\n') if line.strip()]
            processed_stanzas.append({'index': index, 'lines': lines})

        return processed_stanzas

    def clean_text_for_speech(self, text):
        """Clean and optimize text for speech generation.

        Args:
            text (str): Raw text to clean

        Returns:
            str: Cleaned text
        """
        # 1. Replace multiple spaces with a single space
        # 2. Remove leading/trailing whitespace
        # 3. Remove any empty lines
        clean_text = ' '.join(filter(bool, [line.strip() for line in text.split('\n')]))

        return clean_text

    def calculate_word_timing(self, word, reading_mode="normal"):
        """Calculate timing for word highlighting based on word complexity and reading mode.

        Args:
            word (str): The word to analyze
            reading_mode (str): Reading mode (normal or learning)

        Returns:
            int: Milliseconds to highlight this word
        """
        # Remove punctuation for length calculation
        clean_word = re.sub(r'[^\w\s]', '', word)

        # Base timing varies by mode
        if reading_mode == "learning":
            base_timing = 700  # Longer base time for learning mode
            length_factor = len(clean_word) * 120  # More time per character
        else:
            base_timing = 300  # Standard base time for normal mode
            length_factor = len(clean_word) * 80  # Standard time per character

        # Add time for complex words (containing multiple vowels)
        vowel_count = len(re.findall(r'[aeiou]', clean_word.lower()))
        complexity_factor = vowel_count * 50

        # Add time for punctuation
        punctuation_factor = 100 if re.search(r'[.,!?;:]', word) else 0

        # Calculate final timing, with appropriate min/max based on mode
        if reading_mode == "learning":
            timing = min(1800, max(500, base_timing + length_factor + complexity_factor + punctuation_factor))
        else:
            timing = min(1200, max(300, base_timing + length_factor + complexity_factor + punctuation_factor))

        return timing

    def classify_word_type(self, word):
        """Classify word as sight word, vocabulary word, or regular word.

        Args:
            word (str): The word to classify

        Returns:
            str: Word type classification
        """
        # Clean the word for analysis
        clean_word = re.sub(r'[^\w\s]', '', word.lower())

        # Simple list of common sight words for early readers
        sight_words = [
            'a', 'and', 'away', 'big', 'blue', 'can', 'come', 'down', 'find', 'for', 'funny',
            'go', 'help', 'here', 'I', 'in', 'is', 'it', 'jump', 'little', 'look', 'make',
            'me', 'my', 'not', 'one', 'play', 'red', 'run', 'said', 'see', 'the', 'three',
            'to', 'two', 'up', 'we', 'where', 'yellow', 'you', 'all', 'am', 'are', 'at', 'ate',
            'be', 'black', 'brown', 'but', 'came', 'did', 'do', 'eat', 'four', 'get', 'good',
            'have', 'he', 'into', 'like', 'must', 'new', 'no', 'now', 'on', 'our', 'out', 'please',
            'pretty', 'ran', 'ride', 'saw', 'say', 'she', 'so', 'soon', 'that', 'there', 'they',
            'this', 'too', 'under', 'want', 'was', 'well', 'went', 'what', 'white', 'who', 'will',
            'with', 'yes'
        ]

        # Heuristic for advanced vocabulary words
        def is_vocabulary_word(word):
            # Words with more than 7 letters are likely vocabulary words
            if len(word) > 7:
                return True

            # Words with certain complex patterns
            if re.search(r'[aeiou]{3}', word):  # Three vowels in a row
                return True

            # Words with uncommon letter combinations
            if re.search(r'(ph|gh|th|wh|qu|sc|ck|dge|tch|sch)', word):
                return True

            return False

        # Classify the word
        if clean_word in sight_words:
            return "sight-word"
        elif is_vocabulary_word(clean_word):
            return "vocabulary-word"
        else:
            return "regular-word"