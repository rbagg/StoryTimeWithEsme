import os
import requests
import hashlib
import time
import base64
import io
import logging
from pathlib import Path
from PIL import Image

class ImageService:
    """Service for generating images using Stability AI API."""

    def __init__(self, api_key):
        """Initialize the image service with API key.

        Args:
            api_key (str): Stability AI API key
        """
        self.api_key = api_key
        self.reference_seed = None

        # Load the image prompt template
        self.image_prompt_template = Path("prompts/image_prompt.txt").read_text()

    def generate_reference_image(self, character_description):
        """Generate an initial reference image for Esme to establish consistency.

        Args:
            character_description (str): Description of Esme's appearance

        Returns:
            str: Path to the generated reference image

        Raises:
            Exception: If image generation fails after max retries
        """
        # Format prompt for reference image
        image_prompt = self.image_prompt_template.replace("{{character_description}}", character_description)
        image_prompt = image_prompt.replace("{{is_reference}}", "YES")

        # Ensure we're under the stability API limit of 2000 chars
        if len(image_prompt) > 1900:
            # Truncate if needed but preserve essential elements
            image_prompt = (
                f"Vibrant portrait of Esme, a 4-year-old girl. She has EXACTLY: {character_description[:150]}. "
                f"Her face is clearly visible. Semi-lifelike features. Colorful outfit. Pastel background. Clean lines. "
                f"THIS CHARACTER APPEARANCE MUST BE CONSISTENT THROUGHOUT ALL IMAGES."
            )

        logging.info(f"Generating reference image with character description: {character_description[:50]}...")

        # Set seed for reference image to maintain consistency
        seed = 42

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text_prompts": [
                            {"text": image_prompt, "weight": 1.0},
                            {"text": "distorted faces, extra limbs, two heads, blurry, dark, scary, dull colors", "weight": -1.0}
                        ],
                        "cfg_scale": 8,
                        "height": 896,
                        "width": 1152,
                        "samples": 1,
                        "steps": 30,
                        "seed": seed
                    },
                    timeout=30
                )

                logging.info(f"Stability API response status: {response.status_code}")

                if response.status_code == 200:
                    image_data = response.json()["artifacts"][0]["base64"]
                    image_path = "static/images/esme_reference.jpg"
                    self._compress_image(image_data, image_path)

                    # Set the reference seed for future images
                    self.reference_seed = seed

                    return f"/{image_path}"
                elif response.status_code in (520, 502) and attempt < max_retries - 1:
                    logging.warning(f"Retry attempt {attempt + 1} due to {response.status_code} error. Waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    raise Exception(f"Stability API error: {response.status_code} - {response.text}")

            except requests.RequestException as e:
                logging.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Retry attempt {attempt + 1} due to request error. Waiting 5 seconds...")
                    time.sleep(5)
                    continue
                raise

        raise Exception("Max retries reached for Stability API request")

    def generate_image(self, stanza_text, image_description, character_description, story_context=""):
        """Generate an image based on stanza text and character description.

        Args:
            stanza_text (str): The text of the stanza
            image_description (str): Concise description for image generation
            character_description (str): Description of the character
            story_context (str): Context from previous stanzas

        Returns:
            str: Path to the generated image

        Raises:
            Exception: If image generation fails
        """
        # Generate reference image first if not already done
        if self.reference_seed is None:
            self.generate_reference_image(character_description)

        # Create a more detailed Esme character description block
        esme_description = (
            f"Esme is a 4-year-old girl with {character_description}. "
            f"She should be drawn consistently in EVERY image with these EXACT features: "
            f"{character_description}. "
            f"Her expression should match the emotion in the current scene but her physical features must remain identical between images."
        )

        # Include story context if provided
        context_prefix = f"{story_context}\n\n" if story_context else ""

        # Format the complete prompt using the template
        image_prompt = self.image_prompt_template
        image_prompt = image_prompt.replace("{{character_description}}", character_description)
        image_prompt = image_prompt.replace("{{image_description}}", image_description)
        image_prompt = image_prompt.replace("{{is_reference}}", "NO")
        image_prompt = image_prompt.replace("{{context_prefix}}", context_prefix)
        image_prompt = image_prompt.replace("{{esme_description}}", esme_description)

        # Ensure we're under the stability API limit of 2000 chars
        if len(image_prompt) > 1900:
            # If still too long, simplify while preserving the character consistency
            context_prefix_short = f"{story_context[:50]}... " if story_context else ""
            image_prompt = (
                f"{context_prefix_short}Soft pastel drawing showing: {image_description[:150]}\n"
                f"CRITICAL: Esme is a 4-year-old girl with {character_description[:100]}. "
                f"Draw Esme with CONSISTENT APPEARANCE in every image. "
                f"Animals: Adorably stylized with VERY large glossy eyes (1/3 of face), rounded shapes, kawaii style. "
                f"Pastel colors with clean outlines."
            )

        logging.info(f"Generating image for scene: {image_description[:50]}...")
        logging.info(f"Using consistent character seed: {self.reference_seed}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text_prompts": [
                            {"text": image_prompt, "weight": 1.0},
                            {"text": "distorted faces, extra limbs, two heads, blurry, dark, scary, dull colors, incorrect proportions, unnatural poses", "weight": -1.0}
                        ],
                        "cfg_scale": 8,
                        "height": 896,
                        "width": 1152,
                        "samples": 1,
                        "steps": 20,
                        "seed": self.reference_seed
                    },
                    timeout=30
                )

                logging.info(f"Stability API response status: {response.status_code}")

                if response.status_code == 200:
                    image_data = response.json()["artifacts"][0]["base64"]
                    # Create a unique filename based on the hash of the prompt
                    image_hash = hashlib.md5(image_prompt.encode()).hexdigest()
                    image_path = f"static/images/image_{image_hash}.jpg"
                    self._compress_image(image_data, image_path)
                    return f"/{image_path}"
                elif response.status_code in (520, 502) and attempt < max_retries - 1:
                    logging.warning(f"Retry attempt {attempt + 1} due to {response.status_code} error. Waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    raise Exception(f"Stability API error: {response.status_code} - {response.text}")

            except requests.RequestException as e:
                logging.error(f"Request error: {e}")
                if attempt < max_retries - 1:
                    logging.info(f"Retry attempt {attempt + 1} due to request error. Waiting 5 seconds...")
                    time.sleep(5)
                    continue
                raise

        raise Exception("Max retries reached for Stability API request")

    def _compress_image(self, image_data, output_path, quality=75):
        """Compress the image using PIL to reduce file size.

        Args:
            image_data (str): Base64 encoded image data
            output_path (str): Path to save the compressed image
            quality (int): JPEG quality setting (0-100)
        """
        img = Image.open(io.BytesIO(base64.b64decode(image_data)))
        img = img.convert('RGB')  # Convert to RGB for JPEG compatibility

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        logging.info(f"Compressed image saved to {output_path}")