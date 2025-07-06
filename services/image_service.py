import os
import requests
import base64
import hashlib
import time
import io
import logging
from PIL import Image

class ImageService:
    """Complete image service with photo reference support and character diversity."""

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
        """Generate image using photo reference for better consistency - FIXED VERSION with correct API format"""

        if not self.has_reference_photo():
            # Fallback to text-only generation
            logging.info("No photo reference found, using text-only generation")
            return self.generate_story_image_text_only(scene_description, page_number, story_context)

        try:
            logging.info(f"Using photo reference for page {page_number}")

            # Create enhanced prompt for image-to-image with character diversity
            prompt = f"""Create a cinematic children's book illustration showing: {scene_description}

CHARACTER REQUIREMENTS:
- Esme: Keep her facial features, hair, and appearance EXACTLY the same as in the reference photo
- Other characters (if present): Make them clearly different from Esme
  * Parents: Adult height, different hair colors, mature faces
  * Other children: Different hair (blonde, black, red), different clothing, different facial features
  * Animals: Cute kawaii style but each species distinct

STYLE REQUIREMENTS:
- Soft pastel children's book art style
- Cinematic composition with dynamic angles
- Rich environmental details
- Professional illustration quality
- Whimsical, magical storybook environment

SCENE: {scene_description}

Maintain Esme's exact appearance while ensuring all other characters look distinctly different."""

            negative_prompt = "realistic photography, adult features on child, all characters looking identical, scary, dark, blurry, distorted face, extra limbs"

            # Read and encode the reference photo
            with open(self.reference_photo_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode()

            # FIXED: Use correct JSON format for image-to-image endpoint
            payload = {
                "init_image": image_data,
                "text_prompts": [
                    {"text": prompt, "weight": 1.0},
                    {"text": negative_prompt, "weight": -1.0}
                ],
                "image_strength": 0.35,  # How much to change from original
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 25
            }

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/image-to-image",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                image_data = response.json()["artifacts"][0]["base64"]

                # Save the generated image
                image_hash = hashlib.md5(scene_description.encode()).hexdigest()
                image_path = f"static/images/story_page_{page_number}_{image_hash[:8]}.jpg"
                self._save_and_compress_image(image_data, image_path)

                logging.info(f"✓ Generated image with photo reference for page {page_number}")
                return f"/{image_path}"
            else:
                error_text = response.text
                logging.warning(f"Photo-based generation failed: {response.status_code} - {error_text}")
                # Fallback to text-only
                return self.generate_story_image_text_only(scene_description, page_number, story_context)

        except Exception as e:
            logging.error(f"Photo reference generation failed: {e}")
            # Fallback to text-only generation
            return self.generate_story_image_text_only(scene_description, page_number, story_context)

    def generate_story_image_text_only(self, scene_description, page_number, story_context=""):
        """Enhanced text-only generation with better character consistency"""

        character_desc = self.character_profile['description'] if self.character_profile else "4 years old, curly brown hair, light skin, blue-green eyes"

        # Enhanced prompt with much stronger character consistency
        prompt = f"""Cinematic children's book illustration: {scene_description}

MAIN CHARACTER - Esme (CRITICAL CONSISTENCY):
- EXACTLY: {character_desc}
- She must appear IDENTICAL in every image: same face shape, exact hair texture and color, same eye color, same skin tone
- Always the focal point and most detailed character
- Consistent proportions and facial features

OTHER CHARACTERS (if present):
- Parents: Adult height, clearly different hair colors from Esme, mature faces
- Dad: Tall adult man, different hair color (brown/black), kind expression
- Mom: Adult woman, different hair style from Esme (straight/wavy), warm smile
- Other children: Clearly different - if Esme has curly brown hair, give others straight blonde, black braids, red pigtails, etc.
- Animals: Cute kawaii style, large eyes, but each species distinct

VISUAL STYLE:
- Cinematic composition with dynamic camera angles
- Rich environmental storytelling
- Soft pastel colors with vibrant accents
- Professional children's book quality
- Whimsical, magical atmosphere

CHARACTER CONSISTENCY SEED: Use consistent visual elements for Esme across all scenes.

Make sure Esme looks exactly the same as previous illustrations - same face, hair, and overall appearance."""

        negative_prompt = "realistic photography, all characters looking identical, adult features on child, scary, dark, blurry, multiple faces, distorted anatomy, extra limbs"

        try:
            # FIXED: Use correct JSON format for text-to-image endpoint
            payload = {
                "text_prompts": [
                    {"text": prompt, "weight": 1.0},
                    {"text": negative_prompt, "weight": -1.0}
                ],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
                "seed": 12345  # Consistent seed for character consistency
            }

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                image_data = response.json()["artifacts"][0]["base64"]

                image_hash = hashlib.md5(scene_description.encode()).hexdigest()
                image_path = f"static/images/story_page_{page_number}_{image_hash[:8]}.jpg"
                self._save_and_compress_image(image_data, image_path)

                logging.info(f"✓ Generated text-only image for page {page_number}")
                return f"/{image_path}"
            else:
                error_text = response.text[:200] if response.text else "Unknown error"
                raise Exception(f"Image generation failed: {response.status_code} - {error_text}")

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