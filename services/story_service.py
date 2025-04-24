import requests
import re
import time
import logging
from pathlib import Path

class StoryService:
    """Service for generating and processing stories using Claude API."""

    def __init__(self, api_key):
        """Initialize StoryService with API key and model name.

        Args:
            api_key (str): Claude API key
        """
        self.api_key = api_key
        self.model = "claude-3-5-sonnet-20241022"

        # Load prompt templates
        self.story_prompt_template = Path("prompts/story_prompt.txt").read_text()
        self.image_desc_prompt_template = Path("prompts/image_description_prompt.txt").read_text()
        self.simplified_story_prompt_template = Path("prompts/simplified_story_prompt.txt").read_text()

    def generate_story(self, description, max_retries=3, initial_delay=1):
        """Generate a story based on user description with retry mechanism.

        Args:
            description (str): User-provided description of the story
            max_retries (int): Maximum number of retry attempts
            initial_delay (int): Initial delay in seconds before first retry

        Returns:
            str: Generated story text

        Raises:
            Exception: If story generation fails after all retries
        """
        # Prepare the prompt by replacing placeholders
        prompt = self.story_prompt_template.replace("{{description}}", description)

        for attempt in range(max_retries):
            try:
                delay = initial_delay * (2 ** attempt)  # Exponential backoff
                if attempt > 0:
                    logging.info(f"Retrying Claude API call (attempt {attempt + 1}/{max_retries}) after {delay} seconds...")
                    time.sleep(delay)

                response = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    json={
                        'model': self.model,
                        'max_tokens': 1000,
                        'messages': [{'role': 'user', 'content': prompt}]
                    },
                    headers={
                        'x-api-key': self.api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    }
                )

                logging.info(f"Claude API response status for story generation: {response.status_code}")

                # Handle specific API errors
                if response.status_code == 529:  # Overloaded error
                    if attempt == max_retries - 1:
                        raise Exception("Claude API is currently overloaded. Please try again later.")
                    continue

                response.raise_for_status()
                story_text = response.json()['content'][0]['text']

                # Replace any escaped newlines with actual newlines
                story_text = story_text.replace('\\\\n', '\n').replace('\\n', '\n')

                return story_text

            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Claude API error after {max_retries} attempts: {e}")
                    raise Exception(f"Failed to generate story after multiple retries: {str(e)}")
                logging.warning(f"Story generation attempt {attempt + 1} failed: {e}")

        # Should not reach here, but just in case
        raise Exception("Failed to generate story after multiple retries")

    def generate_simplified_story(self, original_story):
        """Generate a simplified version of the story for teaching reading.

        Args:
            original_story (str): The original story text

        Returns:
            str: Simplified version of the story

        Raises:
            Exception: If simplified story generation fails
        """
        # Prepare the prompt by replacing placeholders
        prompt = self.simplified_story_prompt_template.replace("{{original_story}}", original_story)

        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                json={
                    'model': self.model,
                    'max_tokens': 1000,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                headers={
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json'
                }
            )

            logging.info(f"Claude API response status for simplified story: {response.status_code}")
            response.raise_for_status()

            simplified_story = response.json()['content'][0]['text']

            # Replace any escaped newlines with actual newlines
            simplified_story = simplified_story.replace('\\\\n', '\n').replace('\\n', '\n')

            return simplified_story

        except Exception as e:
            logging.error(f"Error generating simplified story: {e}")
            # Return a fallback simple version if generation fails
            return self._create_fallback_simplified_story(original_story)

    def _create_fallback_simplified_story(self, original_story):
        """Create a basic simplified version of the story if API call fails.

        Args:
            original_story (str): The original story text

        Returns:
            str: Basic simplified version of the story
        """
        # Split into stanzas
        stanzas = original_story.split('\n\n')

        # Create a very basic simplification
        simplified_stanzas = []
        for stanza in stanzas:
            # Take first and last line of each stanza as a simplification
            lines = [line for line in stanza.split('\n') if line.strip()]
            if lines:
                simplified_lines = []
                if len(lines) > 0:
                    simplified_lines.append(lines[0])
                if len(lines) > 2:
                    simplified_lines.append(lines[-1])
                simplified_stanzas.append('\n'.join(simplified_lines))

        return '\n\n'.join(simplified_stanzas)

    def generate_image_descriptions(self, stanzas):
        """Generate concise image descriptions for each stanza using Claude.

        Args:
            stanzas (list): List of stanza text blocks

        Returns:
            list: List of image descriptions corresponding to each stanza
        """
        # Combine stanzas into prompt content
        stanzas_text = ""
        for i, stanza in enumerate(stanzas):
            stanzas_text += f"STANZA {i+1}:\n{stanza}\n\n"

        # Prepare the prompt for image descriptions
        prompt = self.image_desc_prompt_template.replace("{{stanzas}}", stanzas_text)

        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                json={
                    'model': self.model,
                    'max_tokens': 1000,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                headers={
                    'x-api-key': self.api_key,
                    'anthropic-version': '2023-06-01',
                    'Content-Type': 'application/json'
                }
            )

            response.raise_for_status()
            image_descriptions = response.json()['content'][0]['text'].strip().split('\n')

            # Clean up responses - remove any numbering or prefixes
            cleaned_descriptions = []
            for desc in image_descriptions:
                # Remove numbers and other common prefixes
                desc = re.sub(r'^(\d+\.|\*|\-|STANZA \d+:)\s*', '', desc.strip())
                if desc:  # Only add non-empty descriptions
                    cleaned_descriptions.append(desc)

            logging.info(f"Generated {len(cleaned_descriptions)} image descriptions")
            return cleaned_descriptions

        except Exception as e:
            logging.error(f"Error generating image descriptions: {e}")
            # Return empty list - will fall back to using stanzas directly
            return []