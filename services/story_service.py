import requests
import re
import time
import logging
import json
from pathlib import Path

class StoryService:
    """Enhanced service for generating high-quality stories using Claude API with self-critique."""

    def __init__(self, api_key):
        """Initialize StoryService with API key and model name."""
        self.api_key = api_key
        self.model = "claude-3-5-sonnet-20241022"

        # Simple story templates for different types
        self.story_templates = {
            'adventure': 'Esme explores somewhere new and discovers something exciting',
            'mystery': 'Esme finds clues and solves a puzzle or mystery', 
            'friendship': 'Esme meets someone new and they become friends',
            'problem_solving': 'Esme faces a challenge and finds a creative solution'
        }

    def generate_story_with_template(self, description, character_description, template_type="adventure"):
        """Generate story using template guidance"""

        template_guidance = self.story_templates.get(template_type, self.story_templates['adventure'])

        prompt = f"""Create a delightful 5-6 stanza rhyming story for 4-year-old Esme.

Story type: {template_type}
Template: {template_guidance}
Description: {description}
Character: {character_description}

Requirements:
- 5-6 stanzas of 4 lines each
- Mix of AABB and ABCB rhyme patterns  
- Each stanza = one clear scene for illustration
- Age-appropriate vocabulary with 2-3 new learning words
- Happy, engaging story that follows the {template_type} template

Create the story now. Do not include any revision notes or metadata - just the story."""

        # Generate initial story
        initial_story = self._call_claude_api(prompt)

        # Clean initial story first
        if initial_story:
            initial_story = self._clean_story_output(initial_story)

        # Simple self-critique (just one improvement pass)
        if initial_story:
            critique_prompt = f"""Improve this children's story for better flow and engagement:

{initial_story}

Make it more engaging for a 4-year-old while keeping the same structure. Focus on:
1. Better rhymes
2. More vivid, fun descriptions  
3. Clear action in each stanza
4. Age-appropriate language

Provide ONLY the improved story - no revision notes or explanations."""

            improved_story = self._call_claude_api(critique_prompt)

            # Clean the improved story
            if improved_story:
                improved_story = self._clean_story_output(improved_story)
                return improved_story

        return initial_story

    def _clean_story_output(self, story_text):
        """Remove metadata but keep all story content - less aggressive filtering"""
        if not story_text:
            return story_text

        # Split into sections by double newlines
        sections = story_text.split('\n\n')
        cleaned_sections = []

        for section in sections:
            section = section.strip()

            # Skip empty sections
            if not section:
                continue

            # Only skip OBVIOUS metadata sections - be much more conservative
            obvious_metadata = [
                '[The revised version includes:',  # Exact match only
                '[The improved version has:',
                '1. More playful, bouncy rhymes',  # Exact numbered list items
                '2. Concrete details kids can relate to',
                '3. Active verbs (zoomed, bouncing, rolled, tumbled)',
                '4. Simple but engaging language',
                '5. More sensory details and movement',
                '6. Fun activities that 4-year-olds enjoy]'
            ]

            # Check for exact matches of obvious metadata
            is_obvious_metadata = False
            for metadata_pattern in obvious_metadata:
                if section.startswith(metadata_pattern):
                    is_obvious_metadata = True
                    break

            # Skip only if it's obvious metadata
            if is_obvious_metadata:
                continue

            # Keep everything else - including story titles and content
            # Even if it mentions "Little Esme" or starts with titles
            cleaned_sections.append(section)

        return '\n\n'.join(cleaned_sections)

    def generate_story(self, description, character_description=None):
        """Main entry point - use template method"""
        # Default to adventure if called without template
        return self.generate_story_with_template(description, character_description, "adventure")

    def generate_simplified_story(self, original_story):
        """Much better simplified version"""

        # Clean the original story first
        clean_original = self._clean_story_output(original_story)

        prompt = f"""Create a simplified version for beginning readers (ages 3-5).

Original story:
{clean_original}

Rules:
- Same number of stanzas
- Use ONLY these words: a, and, at, can, come, do, go, has, he, her, him, I, in, is, it, me, my, no, on, see, she, the, to, up, we, you, big, cat, dog, run, sit, fun, red, mom, dad, get, let, wet, hot, not
- 2-4 sentences per stanza, maximum 4 words per sentence
- Keep the same story events but much simpler

Example:
Original: "Down at PlayWorld, what did she spy? A slide that stretched up to the sky!"
Simplified: "Esme went to play. She saw a big slide. It was very high. Up she went."

Create ONLY the simplified version - no explanations."""

        simplified = self._call_claude_api(prompt)

        # Clean the simplified version too
        if simplified:
            simplified = self._clean_story_output(simplified)
            return simplified

        return self._create_basic_fallback(clean_original)

    def generate_image_descriptions(self, stanzas, character_description=""):
        """Generate enhanced image descriptions with character consistency."""
        stanzas_text = "\n\n".join([f"STANZA {i+1}:\n{stanza}" for i, stanza in enumerate(stanzas)])

        prompt = f"""Create vivid, consistent image descriptions for children's book illustrations.

Character consistency requirement: Esme must appear identical in every image - {character_description}

For each stanza, provide a detailed description focusing on:
1. Esme's specific action/pose/expression
2. Key objects or environment elements
3. Emotional tone of the scene
4. Visual composition that tells the story

Stanzas to describe:
{stanzas_text}

Format: One detailed description per stanza, 15-25 words each, focusing on specific visual elements that an illustrator could draw.

Provide ONLY the descriptions - no explanations."""

        try:
            response = self._call_claude_api(prompt)
            if response:
                descriptions = [desc.strip() for desc in response.split('\n') if desc.strip()]
                # Clean up any numbering
                cleaned = [re.sub(r'^(\d+\.|\*|\-)\s*', '', desc) for desc in descriptions]
                return [desc for desc in cleaned if desc and len(desc) > 10]
            return []
        except Exception as e:
            logging.error(f"Error generating image descriptions: {e}")
            return []

    def _call_claude_api(self, prompt, max_retries=3):
        """Call Claude API with retry logic."""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    time.sleep(2 ** attempt)  # Exponential backoff

                response = requests.post(
                    'https://api.anthropic.com/v1/messages',
                    json={
                        'model': self.model,
                        'max_tokens': 1500,
                        'messages': [{'role': 'user', 'content': prompt}]
                    },
                    headers={
                        'x-api-key': self.api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    content = response.json()['content'][0]['text']
                    return content.replace('\\\\n', '\n').replace('\\n', '\n')
                elif response.status_code == 529:  # Overloaded
                    if attempt == max_retries - 1:
                        raise Exception("Claude API overloaded")
                    continue
                else:
                    response.raise_for_status()

            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Claude API call failed after {max_retries} attempts: {e}")
                    raise
                logging.warning(f"Attempt {attempt + 1} failed: {e}")

        return None

    def _create_basic_fallback(self, original_story):
        """Enhanced fallback simplified story creation."""
        stanzas = original_story.split('\n\n')
        simplified_stanzas = []

        for stanza in stanzas:
            lines = [line.strip() for line in stanza.split('\n') if line.strip()]
            if lines:
                # Create simple sentences about what Esme does
                simple_lines = [
                    "Esme went to play.",
                    "She saw something new.", 
                    "It was big and fun.",
                    "She had a good time."
                ]
                simplified_stanzas.append('\n'.join(simple_lines[:len(lines)]))

        return '\n\n'.join(simplified_stanzas)