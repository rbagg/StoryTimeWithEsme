import requests
import os
import logging
import base64
import time
from pathlib import Path

class StoryAnimationService:
    """Service for generating story animations using direct scene-to-video prompting.

    Instead of categorizing actions, we feed the scene text directly to the video generator
    and let it interpret what Esme should be doing in that specific scene.
    """

    def __init__(self, api_key, reading_speed_settings):
        """Initialize with API key and reading speed settings.

        Args:
            api_key (str): Stability AI API key
            reading_speed_settings (dict): Reading speed configuration from your app.py
        """
        self.api_key = api_key
        self.base_url = "https://api.stability.ai/v2beta"
        self.reading_speed_settings = reading_speed_settings

    def calculate_animation_duration(self, scene_text, reading_mode):
        """Calculate animation duration based on reading speed settings.

        Args:
            scene_text (str): Text of the scene
            reading_mode (str): normal or learning mode

        Returns:
            float: Duration in seconds for the animation
        """
        # Get your reading speed settings for the mode
        mode_settings = self.reading_speed_settings.get(reading_mode, self.reading_speed_settings['normal'])

        # Calculate approximate speech duration based on word count and your settings
        word_count = len(scene_text.split())

        # Base calculation using your settings
        avg_word_length = sum(len(word) for word in scene_text.split()) / max(word_count, 1)
        speech_duration_ms = word_count * (mode_settings['base_duration'] + avg_word_length * mode_settings['char_duration'])

        # Convert to seconds and apply your playback rate
        speech_duration_seconds = (speech_duration_ms / 1000) / mode_settings['playback_rate']

        # Make animation slightly longer than speech for dramatic effect
        animation_duration = speech_duration_seconds * 1.2

        # Cap duration for reasonable file sizes and processing time
        max_duration = 8.0 if reading_mode == 'learning' else 6.0
        min_duration = 3.0  # Minimum for meaningful animation

        animation_duration = max(min_duration, min(animation_duration, max_duration))

        logging.info(f"Animation duration: words={word_count}, speech={speech_duration_seconds:.1f}s, animation={animation_duration:.1f}s")

        return animation_duration

    def generate_story_animation(self, static_image_path, scene_text, character_description, reading_mode="normal"):
        """Generate animation by directly prompting the video generator with the scene.

        Args:
            static_image_path (str): Path to the base static image
            scene_text (str): The full text of the scene
            character_description (str): Description of the main character
            reading_mode (str): Reading mode for duration synchronization

        Returns:
            dict: Results including video path and animation details
        """
        try:
            # Calculate synchronized duration
            duration = self.calculate_animation_duration(scene_text, reading_mode)

            # Read the static image
            with open(static_image_path.lstrip('/'), 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Create animation prompt directly from the scene
            animation_prompt = self._create_scene_animation_prompt(
                scene_text, 
                character_description
            )

            # Determine motion intensity based on scene content
            motion_intensity = self._analyze_motion_intensity(scene_text)

            payload = {
                "image": image_data,
                "seed": 42,  # Consistent seed for character consistency
                "cfg_scale": 1.8,  # Lower for faithfulness to original image
                "motion_bucket_id": int(motion_intensity * 127),
                "prompt": animation_prompt[:500]  # API limit
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            logging.info(f"Generating {reading_mode} animation from scene: {scene_text[:50]}...")
            logging.info(f"Motion intensity: {motion_intensity}, Duration: {duration:.1f}s")

            response = requests.post(
                f"{self.base_url}/image-to-video",
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                video_data = base64.b64decode(result["video"])

                # Save video file
                video_filename = f"scene_animation_{reading_mode}_{int(time.time())}.mp4"
                video_path = f"static/videos/{video_filename}"
                os.makedirs("static/videos", exist_ok=True)

                with open(video_path, 'wb') as f:
                    f.write(video_data)

                # Extract a simple action description for UI
                action_description = self._extract_simple_action(scene_text)

                return {
                    'success': True,
                    'video_path': f"/{video_path}",
                    'detected_action': action_description,
                    'duration': duration,
                    'reading_mode': reading_mode,
                    'motion_intensity': motion_intensity,
                    'description': f"Animation of: {action_description}"
                }
            else:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('message', 'Unknown error')}"
                except:
                    error_msg += f" - {response.text[:100]}"

                logging.error(f"Animation generation failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            logging.error(f"Error generating story animation: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _create_scene_animation_prompt(self, scene_text, character_description):
        """Create animation prompt directly from the scene text.

        This is where the magic happens - we let the AI interpret the scene
        and animate Esme accordingly.
        """

        # Clean the scene text for better prompting
        clean_scene = scene_text.replace('\n', ' ').strip()

        prompt = f"""
        Animate this scene with Esme performing the actions described:

        SCENE: {clean_scene}

        CHARACTER: Esme ({character_description}) - maintain exact appearance from the image

        ANIMATION REQUIREMENTS:
        - Esme should act out what is happening in the scene text
        - Show natural, child-appropriate movement and expressions
        - Maintain character consistency (same face, hair, clothing)
        - Focus on Esme's actions and reactions as described in the scene
        - Include appropriate facial expressions for the scene emotion
        - Keep background elements stable unless part of the action
        - Smooth, believable motion suitable for children's content

        Make Esme come alive by having her perform the specific actions and show the emotions described in this scene.
        """.strip()

        return prompt

    def _analyze_motion_intensity(self, scene_text):
        """Analyze scene text to determine appropriate motion intensity.

        Args:
            scene_text (str): The scene text

        Returns:
            float: Motion intensity between 0.2 and 0.9
        """
        scene_lower = scene_text.lower()

        # High motion words
        high_motion_words = [
            'run', 'running', 'ran', 'jump', 'jumping', 'leapt', 'slide', 'sliding', 'slid',
            'swim', 'swimming', 'dive', 'diving', 'fly', 'flying', 'dance', 'dancing',
            'race', 'racing', 'chase', 'chasing', 'climb', 'climbing', 'rush', 'rushing'
        ]

        # Medium motion words
        medium_motion_words = [
            'walk', 'walking', 'move', 'moving', 'reach', 'reaching', 'turn', 'turning',
            'play', 'playing', 'build', 'building', 'work', 'working', 'help', 'helping',
            'point', 'pointing', 'wave', 'waving', 'clap', 'clapping'
        ]

        # Low motion words (expressions, gentle movements)
        low_motion_words = [
            'smile', 'smiling', 'laugh', 'laughing', 'think', 'thinking', 'wonder', 'wondering',
            'look', 'looking', 'see', 'seeing', 'watch', 'watching', 'listen', 'listening',
            'sit', 'sitting', 'rest', 'resting'
        ]

        # Count word types
        high_count = sum(1 for word in high_motion_words if word in scene_lower)
        medium_count = sum(1 for word in medium_motion_words if word in scene_lower)
        low_count = sum(1 for word in low_motion_words if word in scene_lower)

        # Determine intensity
        if high_count > 0:
            return 0.8  # High motion
        elif medium_count > 0:
            return 0.5  # Medium motion
        elif low_count > 0:
            return 0.3  # Low motion
        else:
            return 0.4  # Default medium-low

    def _extract_simple_action(self, scene_text):
        """Extract a simple action description for the UI.

        Args:
            scene_text (str): The scene text

        Returns:
            str: Simple action description
        """
        scene_lower = scene_text.lower()

        # Common action patterns
        action_patterns = {
            'sliding': ['slide', 'sliding', 'slid'],
            'running': ['run', 'running', 'ran', 'dash', 'dashed'],
            'jumping': ['jump', 'jumping', 'leapt', 'leap'],
            'swimming': ['swim', 'swimming', 'splash'],
            'diving': ['dive', 'diving'],
            'climbing': ['climb', 'climbing'],
            'dancing': ['dance', 'dancing'],
            'playing': ['play', 'playing'],
            'building': ['build', 'building'],
            'puzzle solving': ['puzzle', 'pieces'],
            'laughing': ['laugh', 'laughing'],
            'smiling': ['smile', 'smiling'],
            'wondering': ['wonder', 'wondering', 'think'],
            'exploring': ['explore', 'exploring'],
            'discovering': ['discover', 'found', 'find']
        }

        # Find the first matching action
        for action, keywords in action_patterns.items():
            if any(keyword in scene_lower for keyword in keywords):
                return action

        # Fallback to first significant word
        words = scene_text.split()
        for word in words:
            if len(word) > 3 and word.lower() not in ['esme', 'the', 'and', 'with', 'that', 'this']:
                return word.lower()

        return "scene animation"

    def batch_generate_story_animations(self, story_content, character_description, reading_mode="normal"):
        """Generate animations for all scenes in a story.

        Args:
            story_content (list): List of story page data
            character_description (str): Character description
            reading_mode (str): Reading mode for synchronization

        Returns:
            list: Updated story content with animation data
        """
        updated_content = []

        for i, page_data in enumerate(story_content):
            page_copy = page_data.copy()

            logging.info(f"Generating animation for page {i+1}/{len(story_content)}")

            # Generate animation for this page by feeding the scene directly
            animation_result = self.generate_story_animation(
                page_data['image'],
                page_data['text'],
                character_description,
                reading_mode
            )

            if animation_result['success']:
                page_copy['animation'] = animation_result['video_path']
                page_copy['animation_action'] = animation_result['detected_action']
                page_copy['animation_duration'] = animation_result['duration']
                page_copy['animation_description'] = animation_result['description']
                page_copy['has_animation'] = True
                logging.info(f"✓ Page {i+1} animation created: {animation_result['detected_action']}")
            else:
                page_copy['has_animation'] = False
                page_copy['animation_error'] = animation_result.get('error', 'Unknown error')
                logging.warning(f"✗ Page {i+1} animation failed: {animation_result.get('error')}")

            updated_content.append(page_copy)

            # Add delay between requests to be nice to the API
            if i < len(story_content) - 1:
                time.sleep(3)

        return updated_content

    # Simple analysis method for debugging/testing
    def analyze_scene_content(self, scene_text):
        """Simple scene analysis for debugging purposes."""
        motion_intensity = self._analyze_motion_intensity(scene_text)
        action_description = self._extract_simple_action(scene_text)

        return {
            'detected_action': action_description,
            'motion_intensity': motion_intensity,
            'scene_text': scene_text,
            'animation_approach': 'direct_scene_prompting'
        }