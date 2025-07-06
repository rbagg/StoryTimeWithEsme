import requests
import os
import logging
import base64
import time
from pathlib import Path

class StorySummaryAnimationService:
    """Service for generating a single story summary animation at the end of the story."""

    def __init__(self, api_key, reading_speed_settings):
        """Initialize with API key and reading speed settings.

        Args:
            api_key (str): Stability AI API key
            reading_speed_settings (dict): Reading speed configuration from your app.py
        """
        self.api_key = api_key
        self.base_url = "https://api.stability.ai/v2beta/image-to-video"
        self.reading_speed_settings = reading_speed_settings

    def create_story_summary_image(self, story_content, character_description):
        """Create a composite summary image from the best story scenes.

        Args:
            story_content (list): List of story page data
            character_description (str): Character description

        Returns:
            str: Path to the summary image, or None if failed
        """
        try:
            # For now, use the first story image as the base for animation
            # In the future, you could create a composite image here
            if story_content and len(story_content) > 0:
                # Use the most action-packed scene (middle of story usually has most action)
                middle_index = len(story_content) // 2
                best_scene = story_content[middle_index]

                # Copy the image to use as summary base
                source_image = best_scene['image'].lstrip('/')
                if os.path.exists(source_image):
                    summary_image_path = f"static/images/story_summary_{int(time.time())}.jpg"

                    # For now, just copy the existing image
                    # In the future, you could generate a new composite image here
                    import shutil
                    shutil.copy2(source_image, summary_image_path)

                    logging.info(f"Created story summary base image: {summary_image_path}")
                    return summary_image_path

            return None

        except Exception as e:
            logging.error(f"Error creating story summary image: {e}")
            return None

    def generate_story_summary_animation(self, story_content, character_description, reading_mode="normal"):
        """Generate a single animation summarizing the entire story.

        Args:
            story_content (list): List of story page data
            character_description (str): Character description
            reading_mode (str): Reading mode for duration synchronization

        Returns:
            dict: Animation result with video path or error
        """
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'No Stability AI API key configured'
                }

            # Test API key
            try:
                test_response = requests.get(
                    "https://api.stability.ai/v1/user/account", 
                    headers={'Authorization': f'Bearer {self.api_key}'},
                    timeout=10
                )
                if test_response.status_code != 200:
                    return {
                        'success': False,
                        'error': f'Invalid API key (status: {test_response.status_code})'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'API connection failed: {str(e)}'
                }

            logging.info("Creating story summary animation...")

            # Create or get summary image
            summary_image_path = self.create_story_summary_image(story_content, character_description)
            if not summary_image_path:
                return {
                    'success': False,
                    'error': 'Could not create summary image'
                }

            # Create story summary text
            story_summary = self._create_story_summary(story_content)

            # Analyze overall story motion
            motion_intensity = self._analyze_story_motion(story_content)

            logging.info(f"Story summary: {story_summary[:100]}...")
            logging.info(f"Overall motion intensity: {motion_intensity}")

            # Generate animation using the summary image
            with open(summary_image_path, 'rb') as image_file:
                files = {
                    'image': ('story_summary.jpg', image_file, 'image/jpeg'),
                }

                # Parameters for story summary animation
                data = {
                    'seed': 123,  # Different seed for story summary
                    'cfg_scale': 1.5,  # Slightly lower for more faithful animation
                    'motion_bucket_id': int(motion_intensity * 127),
                }

                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Accept': 'video/*'
                }

                logging.info(f"Generating story summary video with motion_bucket_id: {int(motion_intensity * 127)}")

                response = requests.post(
                    self.base_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=180
                )

            if response.status_code == 200:
                video_data = response.content

                if not video_data:
                    return {
                        'success': False,
                        'error': 'Received empty video data from API'
                    }

                # Save story summary video
                video_filename = f"story_summary_animation_{int(time.time())}.mp4"
                video_path = f"static/videos/{video_filename}"
                os.makedirs("static/videos", exist_ok=True)

                with open(video_path, 'wb') as f:
                    f.write(video_data)

                # Verify file was saved
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    file_size = os.path.getsize(video_path)
                    logging.info(f"✓ Story summary animation saved: {video_path} ({file_size // 1024}KB)")

                    return {
                        'success': True,
                        'video_path': f"/{video_path}",
                        'summary_image': f"/{summary_image_path}",
                        'story_summary': story_summary,
                        'motion_intensity': motion_intensity,
                        'duration': 4.0,
                        'description': "Complete story summary animation"
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Video file was not saved properly'
                    }
            else:
                error_msg = f"API error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f" - {error_data['message']}"
                    elif 'errors' in error_data:
                        error_msg += f" - {', '.join(error_data['errors'])}"
                except:
                    error_msg += f" - {response.text[:200]}"

                logging.error(f"Story summary animation failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            logging.error(f"Unexpected error generating story summary animation: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def _create_story_summary(self, story_content):
        """Create a summary of the story from all pages.

        Args:
            story_content (list): List of story page data

        Returns:
            str: Story summary text
        """
        story_parts = []

        for page in story_content:
            # Get the main text content
            text = page.get('text', '')
            if text and len(text.strip()) > 0:
                # Clean up the text
                clean_text = text.replace('\n', ' ').strip()
                if clean_text:
                    story_parts.append(clean_text)

        # Join all parts into a summary
        full_story = ' '.join(story_parts)

        # If too long, take first part and last part
        if len(full_story) > 200:
            first_part = story_parts[0] if story_parts else ""
            last_part = story_parts[-1] if len(story_parts) > 1 else ""
            summary = f"{first_part} ... {last_part}"
        else:
            summary = full_story

        return summary[:200]  # Limit to 200 characters

    def _analyze_story_motion(self, story_content):
        """Analyze the overall motion level of the entire story.

        Args:
            story_content (list): List of story page data

        Returns:
            float: Overall motion intensity (0.2-0.8)
        """
        all_text = ""
        for page in story_content:
            text = page.get('text', '')
            all_text += " " + text.lower()

        # High motion words - more comprehensive list for story summary
        high_motion_words = [
            'run', 'running', 'ran', 'jump', 'jumping', 'leapt', 'slide', 'sliding', 'slid',
            'swim', 'swimming', 'dive', 'diving', 'fly', 'flying', 'dance', 'dancing',
            'race', 'racing', 'chase', 'chasing', 'climb', 'climbing', 'rush', 'rushing',
            'bounce', 'bouncing', 'twirl', 'twirling', 'adventure', 'explore', 'exploring'
        ]

        # Medium motion words
        medium_motion_words = [
            'walk', 'walking', 'move', 'moving', 'reach', 'reaching', 'turn', 'turning',
            'play', 'playing', 'build', 'building', 'work', 'working', 'help', 'helping',
            'point', 'pointing', 'wave', 'waving', 'clap', 'clapping', 'skip', 'skipping',
            'discover', 'find', 'found', 'search', 'searching'
        ]

        # Low motion words
        low_motion_words = [
            'smile', 'smiling', 'laugh', 'laughing', 'think', 'thinking', 'wonder', 'wondering',
            'look', 'looking', 'see', 'seeing', 'watch', 'watching', 'listen', 'listening',
            'sit', 'sitting', 'rest', 'resting', 'yawn', 'yawning', 'sleep', 'sleeping'
        ]

        # Count occurrences
        high_count = sum(1 for word in high_motion_words if word in all_text)
        medium_count = sum(1 for word in medium_motion_words if word in all_text)
        low_count = sum(1 for word in low_motion_words if word in all_text)

        total_motion_words = high_count + medium_count + low_count

        if total_motion_words == 0:
            return 0.4  # Default medium motion

        # Calculate weighted motion score
        motion_score = (high_count * 0.8 + medium_count * 0.5 + low_count * 0.2) / total_motion_words

        # Ensure it's in reasonable range for story summary (slightly more dynamic)
        motion_intensity = max(0.3, min(0.7, motion_score))

        logging.info(f"Story motion analysis: high={high_count}, medium={medium_count}, low={low_count}, score={motion_intensity:.2f}")

        return motion_intensity

    def add_story_summary_page(self, story_content, character_description, reading_mode="normal"):
        """Add a story summary animation page to the end of the story.

        Args:
            story_content (list): List of story page data
            character_description (str): Character description
            reading_mode (str): Reading mode

        Returns:
            list: Updated story content with summary page
        """
        if not story_content:
            return story_content

        logging.info("Adding story summary animation page...")

        # Generate the summary animation
        animation_result = self.generate_story_summary_animation(
            story_content, 
            character_description, 
            reading_mode
        )

        # Create the summary page
        summary_page = {
            'page': len(story_content) + 1,
            'text': 'The End - Story Summary',
            'image': animation_result.get('summary_image', story_content[0]['image']),  # Fallback to first image
            'stanzas': [{
                'index': 0,
                'lines': ['The End - Story Summary'],
                'reading_analysis': {
                    'word_count': 4,
                    'sight_words': 2,
                    'phonics_words': 0,
                    'complex_words': 1,
                    'sight_word_ratio': 50.0,
                    'difficulty': 'easy',
                    'recommended_reading_mode': 'normal'
                }
            }],
            'simplified_text': 'The End',
            'simplified_stanzas': [{
                'index': 0,
                'lines': ['The End'],
                'reading_analysis': {
                    'word_count': 2,
                    'sight_words': 1,
                    'phonics_words': 0,
                    'complex_words': 0,
                    'sight_word_ratio': 50.0,
                    'difficulty': 'easy',
                    'recommended_reading_mode': 'normal'
                }
            }],
            'is_summary_page': True,
            'has_animation': animation_result['success'],
        }

        if animation_result['success']:
            summary_page.update({
                'animation': animation_result['video_path'],
                'animation_description': animation_result['description'],
                'animation_duration': animation_result['duration'],
                'story_summary': animation_result['story_summary']
            })
            logging.info("✓ Story summary animation page created successfully")
        else:
            summary_page['animation_error'] = animation_result['error']
            logging.warning(f"✗ Story summary animation failed: {animation_result['error']}")

        # Add summary page to the end
        updated_content = story_content.copy()
        updated_content.append(summary_page)

        return updated_content