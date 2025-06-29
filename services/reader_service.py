import re
import logging
from pathlib import Path

class ReaderService:
    """Enhanced service for processing text for the 'Learn to Read' mode."""

    def __init__(self):
        """Initialize ReaderService with enhanced reading support."""

        # Expanded sight words list by difficulty level
        self.sight_words = {
            'pre_k': [
                'I', 'a', 'the', 'to', 'and', 'go', 'up', 'me', 'my', 'you', 'it', 'in', 'on', 'at', 'is'
            ],
            'kindergarten': [
                'am', 'an', 'as', 'at', 'be', 'by', 'do', 'he', 'if', 'in', 'is', 'it', 'no', 'of', 'on', 
                'or', 'so', 'to', 'up', 'we', 'all', 'and', 'are', 'but', 'can', 'come', 'day', 'did', 
                'eat', 'for', 'get', 'had', 'has', 'her', 'him', 'his', 'how', 'let', 'may', 'new', 'not', 
                'now', 'old', 'our', 'out', 'put', 'ran', 'red', 'run', 'said', 'saw', 'see', 'she', 'too', 
                'top', 'two', 'was', 'who', 'yes', 'you'
            ],
            'first_grade': [
                'after', 'again', 'any', 'ask', 'by', 'could', 'every', 'fly', 'from', 'give', 'going', 
                'had', 'has', 'her', 'him', 'his', 'how', 'just', 'know', 'let', 'live', 'may', 'of', 
                'old', 'once', 'open', 'over', 'put', 'round', 'some', 'stop', 'take', 'thank', 'them', 
                'think', 'walk', 'were', 'when'
            ]
        }

        # Combine all sight words for easy lookup
        self.all_sight_words = set()
        for level_words in self.sight_words.values():
            self.all_sight_words.update([word.lower() for word in level_words])

        # Phonics patterns for word classification
        self.phonics_patterns = {
            'cvc': r'^[bcdfghjklmnpqrstvwxyz][aeiou][bcdfghjklmnpqrstvwxyz]$',
            'cvce': r'^[bcdfghjklmnpqrstvwxyz][aeiou][bcdfghjklmnpqrstvwxyz]e$',
            'consonant_blend': r'^(bl|br|cl|cr|dr|fl|fr|gl|gr|pl|pr|sc|sk|sl|sm|sn|sp|st|sw|tr)',
            'vowel_team': r'(ai|ay|ea|ee|ie|oa|ow|ue|ou|oi|oy)',
            'r_controlled': r'(ar|er|ir|or|ur)',
            'complex': r'^.{7,}$'  # 7+ letters considered complex
        }

    def process_story_text(self, text):
        """Enhanced processing of story text into structured format with reading analysis."""
        if not text:
            return []

        # Clean text
        text = text.replace('\\\\n', '\n').replace('\\n', '\n')

        # Split into stanzas
        stanzas = [stanza.strip() for stanza in text.split('\n\n') if stanza.strip()]

        processed_stanzas = []
        for index, stanza in enumerate(stanzas):
            # Process lines within stanza
            lines = [line.rstrip('\n').strip() for line in stanza.split('\n') if line.strip()]

            # Analyze words in this stanza for reading difficulty
            stanza_analysis = self._analyze_stanza_for_reading(lines)

            processed_stanzas.append({
                'index': index,
                'lines': lines,
                'reading_analysis': stanza_analysis
            })

        return processed_stanzas

    def _analyze_stanza_for_reading(self, lines):
        """Analyze a stanza for reading difficulty and educational value."""
        all_words = []
        for line in lines:
            words = re.findall(r'\b\w+\b', line.lower())
            all_words.extend(words)

        if not all_words:
            return {'word_count': 0, 'difficulty': 'easy', 'sight_word_ratio': 0}

        # Classify words
        sight_words = [w for w in all_words if w in self.all_sight_words]
        phonics_words = []
        complex_words = []

        for word in all_words:
            if word not in self.all_sight_words:
                if self._classify_phonics_pattern(word) in ['cvc', 'cvce']:
                    phonics_words.append(word)
                elif len(word) > 6 or self._classify_phonics_pattern(word) == 'complex':
                    complex_words.append(word)

        # Calculate ratios
        total_words = len(all_words)
        sight_word_ratio = len(sight_words) / total_words
        complex_ratio = len(complex_words) / total_words

        # Determine difficulty
        if complex_ratio > 0.3:
            difficulty = 'hard'
        elif sight_word_ratio > 0.7:
            difficulty = 'easy'
        else:
            difficulty = 'medium'

        return {
            'word_count': total_words,
            'sight_words': len(sight_words),
            'phonics_words': len(phonics_words),
            'complex_words': len(complex_words),
            'sight_word_ratio': round(sight_word_ratio * 100, 1),
            'difficulty': difficulty,
            'recommended_reading_mode': 'learning' if difficulty in ['medium', 'hard'] else 'normal'
        }

    def _classify_phonics_pattern(self, word):
        """Classify a word by its phonics pattern."""
        word = word.lower()

        for pattern_name, pattern in self.phonics_patterns.items():
            if re.search(pattern, word):
                return pattern_name

        return 'irregular'

    def calculate_word_timing(self, word, reading_mode="normal", context=None):
        """Enhanced word timing calculation based on reading research."""

        # Clean word for analysis
        clean_word = re.sub(r'[^\w\s]', '', word.lower())

        # Base timing by reading mode
        if reading_mode == "learning":
            base_timing = 800
            char_factor = 150
            complexity_bonus = 300
        else:
            base_timing = 250
            char_factor = 60
            complexity_bonus = 100

        # Calculate basic timing
        timing = base_timing + (len(clean_word) * char_factor)

        # Adjust for word type
        word_type = self.classify_word_type(word)

        if word_type == "sight-word":
            # Sight words should be faster
            timing = int(timing * 0.7)
        elif word_type == "phonics-word":
            # Phonics words get standard timing
            pass
        elif word_type == "complex-word":
            # Complex words need more time
            timing += complexity_bonus

        # Adjust for punctuation
        if context and any(p in word for p in '.,!?;:'):
            timing += 200 if reading_mode == "learning" else 100

        # Reasonable bounds
        min_timing = 400 if reading_mode == "learning" else 200
        max_timing = 2000 if reading_mode == "learning" else 1000

        return max(min_timing, min(max_timing, timing))

    def classify_word_type(self, word):
        """Enhanced word classification for reading instruction."""
        clean_word = re.sub(r'[^\w\s]', '', word.lower())

        # Check sight words first
        if clean_word in self.all_sight_words:
            return "sight-word"

        # Check phonics patterns
        phonics_pattern = self._classify_phonics_pattern(clean_word)

        if phonics_pattern in ['cvc', 'cvce', 'consonant_blend']:
            return "phonics-word"
        elif phonics_pattern in ['vowel_team', 'r_controlled', 'complex']:
            return "complex-word"
        else:
            # Default classification based on length and common patterns
            if len(clean_word) <= 4 and re.match(r'^[a-z]+$', clean_word):
                return "phonics-word"
            else:
                return "complex-word"

    def _count_syllables(self, word):
        """Enhanced syllable counting for better timing."""
        word = re.sub(r'[^\w]', '', word.lower())

        if len(word) <= 1:
            return 1

        # Count vowel groups
        vowel_groups = len(re.findall(r'[aeiouy]+', word))

        # Adjust for common patterns
        if word.endswith('e') and vowel_groups > 1:
            vowel_groups -= 1

        # Handle 'le' endings
        if word.endswith('le') and len(word) > 2 and word[-3] not in 'aeiou':
            vowel_groups += 1

        # Special cases for common words
        special_cases = {
            'the': 1, 'are': 1, 'every': 3, 'little': 2, 'people': 2
        }

        if word in special_cases:
            return special_cases[word]

        return max(1, vowel_groups)