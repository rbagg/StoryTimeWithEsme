import os
import requests
import base64
import hashlib
import time
import io
import logging
from PIL import Image

class ImageService:
    """Complete image service with photo reference support for better character consistency."""

    def __init__(self, api_key):
        self.api_key = api_key
        self.character_profile = None
        self.reference_photo_path = "static/images/esme_reference.jpg"  # Path to uploaded photo

    def has_reference_photo(self):
        """Check if reference photo exists"""
        exists = os.path.exists(self.reference_photo_path)
        logging.info(f"Reference photo check: {self.reference_photo_path} exists = {exists}")
        return exists

    def generate_character_profile(self, character_description):
        """Create character profile, using photo if available"""
        self.character_profile = {
            'description': character_description,
            'uses_photo_reference': self.has_reference_photo(),
            'photo_path': self.reference_photo_path if self.has_reference_photo() else None
        }

        logging.info(f"Character profile created. Photo reference: {self.has_reference_photo()}")
        return self.character_profile

    def generate_story_image_with_photo(self, scene_description, page_number, story_context=""):
        """Generate image using photo reference for better consistency"""

        if not self.has_reference_photo():
            # Fallback to text-only generation
            logging.info("No photo reference found, using text-only generation")
            return self.generate_story_image_text_only(scene_description, page_number, story_context)

        try:
            logging.info(f"Using photo reference for page {page_number}")

            # Read and encode the reference photo
            with open(self.reference_photo_path, 'rb') as image_file:
                photo_data = base64.b64encode(image_file.read()).decode()

            # Create enhanced prompt for image-to-image
            prompt = f"""Transform this photo into a children's book illustration style showing: {scene_description}

Style requirements:
- Soft pastel children's book art style
- Keep the character's facial features and appearance EXACTLY the same
- Whimsical, magical storybook environment
- Professional children's book illustration quality
- Scene: {scene_description}

Maintain character consistency while changing the scene and background."""

            # Use Stability AI's image-to-image endpoint
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "init_image": photo_data,
                    "text_prompts": [
                        {"text": prompt, "weight": 1.0},
                        {"text": "realistic photography, adult features, scary, dark", "weight": -1.0}
                    ],
                    "image_strength": 0.3,  # Keep character features but allow scene changes
                    "cfg_scale": 8,
                    "height": 896,
                    "width": 1152,
                    "samples": 1,
                    "steps": 30
                },
                timeout=60
            )

            if response.status_code == 200:
                image_data = response.json()["artifacts"][0]["base64"]

                # Save the generated image
                image_hash = hashlib.md5(scene_description.encode()).hexdigest()
                image_path = f"static/images/story_page_{page_number}_{image_hash[:8]}.jpg"
                self._save_and_compress_image(image_data, image_path)

                logging.info(f"Generated image with photo reference for page {page_number}")
                return f"/{image_path}"
            else:
                logging.warning(f"Photo-based generation failed: {response.status_code}")
                # Fallback to text-only
                return self.generate_story_image_text_only(scene_description, page_number, story_context)

        except Exception as e:
            logging.error(f"Photo reference generation failed: {e}")
            # Fallback to text-only generation
            return self.generate_story_image_text_only(scene_description, page_number, story_context)

    def generate_story_image_text_only(self, scene_description, page_number, story_context=""):
        """Fallback text-only generation when no photo available"""

        character_desc = self.character_profile['description'] if self.character_profile else "4 years old, curly brown hair, light skin, blue-green eyes"

        prompt = f"""Soft pastel children's book illustration: {scene_description}

Character: Esme is exactly {character_desc}. She must appear IDENTICAL in every image.

Style: Whimsical children's book art, soft pastels, magical storybook quality"""

        # Ensure prompt is not too long
        if len(prompt) > 1900:
            prompt = prompt[:1900] + "..."

        try:
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "text_prompts": [
                        {"text": prompt, "weight": 1.0},
                        {"text": "realistic photography, inconsistent character, scary, dark", "weight": -1.0}
                    ],
                    "cfg_scale": 8,
                    "height": 896,
                    "width": 1152,
                    "samples": 1,
                    "steps": 30,
                    "seed": 42  # Consistent seed for character consistency
                },
                timeout=60
            )

            if response.status_code == 200:
                image_data = response.json()["artifacts"][0]["base64"]

                image_hash = hashlib.md5(scene_description.encode()).hexdigest()
                image_path = f"static/images/story_page_{page_number}_{image_hash[:8]}.jpg"
                self._save_and_compress_image(image_data, image_path)

                logging.info(f"Generated text-only image for page {page_number}")
                return f"/{image_path}"
            else:
                raise Exception(f"Image generation failed: {response.status_code}")

        except Exception as e:
            logging.error(f"Text-only generation failed: {e}")
            raise

    def _save_and_compress_image(self, image_data, output_path, quality=85):
        """Save and compress image"""
        try:
            img = Image.open(io.BytesIO(base64.b64decode(image_data)))
            img = img.convert('RGB')

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, 'JPEG', quality=quality, optimize=True)

            file_size = os.path.getsize(output_path)
            logging.info(f"Image saved: {output_path} ({file_size // 1024}KB)")

        except Exception as e:
            logging.error(f"Error saving image: {e}")
            raise

    # Legacy compatibility methods that your existing code expects
    def generate_reference_image(self, character_description, scene="cheerful portrait"):
        """Generate or use reference image"""
        self.generate_character_profile(character_description)

        if self.has_reference_photo():
            logging.info("Using uploaded photo as reference")
            return f"/{self.reference_photo_path}"
        else:
            # Generate a reference image using text-to-image
            logging.info("No photo found, generating reference image")
            return self.generate_story_image_text_only(f"Portrait of Esme - {scene}", 0)

    def generate_story_image(self, scene_description, page_number, story_context=""):
        """Main method that chooses photo or text generation"""
        if self.has_reference_photo():
            return self.generate_story_image_with_photo(scene_description, page_number, story_context)
        else:
            return self.generate_story_image_text_only(scene_description, page_number, story_context)

    def get_character_consistency_summary(self):
        """Get summary of character consistency approach"""
        return {
            'uses_photo_reference': self.has_reference_photo(),
            'photo_path': self.reference_photo_path if self.has_reference_photo() else None,
            'consistency_method': 'Photo-based' if self.has_reference_photo() else 'Text-based with seed'
        }

    # For backward compatibility - some code might call this
    def generate_image(self, stanza_text, image_description, character_description, story_context=""):
        """Legacy method for backward compatibility."""
        # Initialize character profile if not done
        if not self.character_profile:
            self.generate_character_profile(character_description)

        # Use new method
        page_number = 1  # Default page number
        return self.generate_story_image(image_description, page_number, story_context)