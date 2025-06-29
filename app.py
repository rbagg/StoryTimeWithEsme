from flask import Flask, request, render_template, jsonify, session
import os
import json
import logging
from datetime import datetime
import re

# Import enhanced services
from services.story_service import StoryService
from services.image_service import ImageService
from services.speech_service import SpeechService
from services.reader_service import ReaderService
from services.storage_service import StorageService
from services.story_animation_service import StoryAnimationService  # NEW: Prompt-based Animation service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Create directories
os.makedirs('static/images', exist_ok=True)
os.makedirs('static/videos', exist_ok=True)  # NEW: For animations
os.makedirs('temp_stories', exist_ok=True)

# API Keys
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')

# Enhanced reading speed settings with predictive timing
READING_SPEED_SETTINGS = {
    "normal": {
        "base_duration": 180,
        "char_duration": 60,
        "speaking_rate": 1.0,
        "playback_rate": 1.0
    },
    "learning": {
        "base_duration": 600,
        "char_duration": 150,
        "speaking_rate": 0.7,
        "playback_rate": 0.6
    }
}

# Initialize enhanced services
story_service = StoryService(CLAUDE_API_KEY)
image_service = ImageService(STABILITY_API_KEY)
speech_service = SpeechService(ELEVEN_LABS_API_KEY, READING_SPEED_SETTINGS)
reader_service = ReaderService()
storage_service = StorageService()
# NEW: Initialize animation service with your reading speed settings
story_animation_service = StoryAnimationService(STABILITY_API_KEY, READING_SPEED_SETTINGS)

@app.route('/')
def index():
    """Main page with story creation and library."""
    return render_template('index.html')

@app.route('/get_voices')
def get_voices():
    """Get available voices optimized for children's content."""
    try:
        voices = speech_service.get_voices()
        return jsonify({"voices": voices})
    except Exception as e:
        logging.error(f"Error fetching voices: {e}")
        return jsonify({"voices": []})

@app.route('/generate', methods=['POST'])
def generate():
    """Generate story with balanced filtering and optional animations"""
    description = request.form.get('description')
    template_type = request.form.get('template_type', 'adventure')
    # NEW: Animation options
    enable_animation = request.form.get('enable_animation') == 'true'
    animation_reading_mode = request.form.get('animation_reading_mode', 'normal')

    # Use photo-based character description since we have the reference photo
    character_description = "4 years old, curly brown hair, light skin, blue-green eyes"

    if not description:
        return render_template('index.html', error="Please describe Esme's adventure!")

    try:
        logging.info(f"Generating {template_type} story with photo reference...")
        if enable_animation:
            logging.info(f"Animation enabled for {animation_reading_mode} reading mode")

        # Generate story with selected template
        story_text = story_service.generate_story_with_template(
            description, character_description, template_type
        )

        if not story_text:
            return render_template('index.html', error="Story generation failed. Please try again.")

        # Generate enhanced simplified version
        simplified_story_text = story_service.generate_simplified_story(story_text)

        # Process into pages - ONLY filter obvious metadata
        raw_pages = story_text.split('\n\n')
        pages = []

        for page in raw_pages:
            page = page.strip()

            # Skip empty pages
            if not page:
                continue

            # Only skip VERY OBVIOUS metadata - be conservative
            obvious_skip_patterns = [
                '[The revised version includes:',  # Exact metadata headers
                '[The improved version has:',
                '1. More playful, bouncy rhymes',  # Exact numbered improvements
                '2. Concrete details kids can relate to',
                '3. Active verbs (',
                '4. Simple but engaging language',
                '5. More sensory details',
                '6. Fun activities that 4-year-olds enjoy'
            ]

            should_skip = False
            for pattern in obvious_skip_patterns:
                if page.startswith(pattern):
                    should_skip = True
                    logging.info(f"Skipped obvious metadata: {page[:50]}...")
                    break

            # Keep everything else, including story titles and content
            if not should_skip and len(page) > 10:  # Keep anything with substance
                pages.append(page)
                logging.info(f"Kept story content: {page[:50]}...")

        logging.info(f"Final result: {len(pages)} story pages (filtered from {len(raw_pages)} raw sections)")

        # If we have too few pages, be even less aggressive
        if len(pages) < 3:
            logging.warning("Too few pages detected, using minimal filtering...")
            pages = []
            for page in raw_pages:
                page = page.strip()
                if page and len(page) > 20:  # Keep almost everything
                    pages.append(page)
            logging.info(f"Minimal filtering result: {len(pages)} pages")

        if len(pages) == 0:
            return render_template('index.html', error="Story processing failed - no valid content found. Please try again.")

        # Process simplified pages the same way
        raw_simplified = simplified_story_text.split('\n\n') if simplified_story_text else []
        simplified_pages = []

        for page in raw_simplified:
            page = page.strip()
            if page and len(page) > 10:  # Keep substantial simplified content
                # Apply same obvious metadata filtering to simplified version
                should_skip = False
                for pattern in obvious_skip_patterns:
                    if page.startswith(pattern):
                        should_skip = True
                        break

                if not should_skip:
                    simplified_pages.append(page)

        logging.info(f"Processed {len(simplified_pages)} simplified pages")

        # Initialize image service with photo reference
        image_service.generate_character_profile(character_description)

        # Generate image descriptions for better scenes
        image_descriptions = story_service.generate_image_descriptions(pages, character_description)

        content = []
        story_context = ""

        for index, text in enumerate(pages):
            logging.info(f"Processing story page {index + 1} of {len(pages)}")

            # Use enhanced image description or fallback
            image_description = image_descriptions[index] if index < len(image_descriptions) else text

            # Generate image using photo reference
            image_url = image_service.generate_story_image(
                image_description, 
                index + 1, 
                story_context
            )

            # Process text for reading
            stanzas = reader_service.process_story_text(text)

            # Process simplified text
            simplified_text = simplified_pages[index] if index < len(simplified_pages) else ""
            simplified_stanzas = reader_service.process_story_text(simplified_text)

            content.append({
                'page': index + 1,
                'text': text,
                'image': image_url,
                'stanzas': stanzas,
                'simplified_text': simplified_text,
                'simplified_stanzas': simplified_stanzas,
                'has_animation': False  # Will be updated if animations are generated
            })

            # Build context for next image
            story_context += f" {text}"
            if len(story_context) > 300:
                story_context = story_context[-300:]

        # NEW: Generate story-driven animations if requested
        if enable_animation and STABILITY_API_KEY:
            logging.info(f"Generating story-driven animations synchronized with {animation_reading_mode} reading mode...")

            try:
                content = story_animation_service.batch_generate_story_animations(
                    content, 
                    character_description,
                    animation_reading_mode
                )

                # Count successful animations
                successful_animations = sum(1 for page in content if page.get('has_animation', False))
                logging.info(f"Successfully generated {successful_animations}/{len(content)} animations")

            except Exception as e:
                logging.error(f"Animation generation failed: {e}")
                # Continue without animations rather than failing the entire story
                for page in content:
                    page['animation_error'] = f"Animation generation failed: {str(e)}"

        # Store enhanced story data
        temp_id = storage_service.store_temp_story({
            'description': description,
            'character_description': character_description,
            'template_type': template_type,
            'story_text': story_text,
            'simplified_text': simplified_story_text,
            'image_descriptions': image_descriptions,
            'content': content,
            'uses_photo_reference': image_service.has_reference_photo(),
            'has_animations': enable_animation and any(page.get('has_animation', False) for page in content)  # NEW
        })

        session['current_story_id'] = temp_id

        logging.info(f"Story generation completed successfully! Generated {len(content)} pages")
        return render_template('story.html', story=content, has_animations=enable_animation)

    except Exception as e:
        logging.error(f"Error in story generation: {e}")
        return render_template('index.html', error=f"Story creation failed: {str(e)}")

@app.route('/read', methods=['POST'])
def read_text():
    """Enhanced text-to-speech with predictive timing."""
    try:
        data = json.loads(request.data)

        raw_text = data.get('text', '')
        voice_id = data.get('voice', '')
        reading_mode = data.get('reading_mode', 'normal')

        if not raw_text or not voice_id:
            return "Missing text or voice", 400

        logging.info(f"Enhanced speech generation: mode={reading_mode}, text_length={len(raw_text)}")

        # Generate speech with enhanced timing prediction
        audio_stream, response_headers = speech_service.generate_speech(
            raw_text, 
            voice_id, 
            reading_mode
        )

        return app.response_class(
            audio_stream, 
            mimetype='audio/mpeg', 
            headers=response_headers
        )

    except Exception as e:
        logging.error(f"Enhanced speech generation error: {e}")
        return f"Speech generation failed: {str(e)}", 500

@app.route('/analyze_timing', methods=['POST'])
def analyze_timing():
    """Analyze text timing for better word highlighting synchronization."""
    try:
        data = json.loads(request.data)
        text = data.get('text', '')
        reading_mode = data.get('reading_mode', 'normal')

        # Get timing analysis from enhanced speech service
        timing_analysis = speech_service.get_timing_preview(text, reading_mode)

        return jsonify(timing_analysis)

    except Exception as e:
        logging.error(f"Timing analysis error: {e}")
        return jsonify({'error': str(e)}), 500

# NEW: Animation-related routes

@app.route('/analyze_scene', methods=['POST'])
def analyze_scene():
    """Analyze a scene for animation potential (for debugging/testing)."""
    data = request.json
    scene_text = data.get('scene_text', '')

    if not scene_text:
        return jsonify({'error': 'No scene text provided'}), 400

    try:
        animation_config = story_animation_service.analyze_scene_content(scene_text)

        # Calculate duration for both reading modes
        normal_duration = story_animation_service.calculate_animation_duration(scene_text, 'normal', animation_config['detected_action'])
        learning_duration = story_animation_service.calculate_animation_duration(scene_text, 'learning', animation_config['detected_action'])

        return jsonify({
            'success': True,
            'analysis': animation_config,
            'scene_text': scene_text,
            'durations': {
                'normal': normal_duration,
                'learning': learning_duration
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/generate_scene_animation', methods=['POST'])
def generate_scene_animation():
    """Generate animation for a specific scene on demand."""
    data = request.json
    image_path = data.get('image_path')
    scene_text = data.get('scene_text')
    character_description = data.get('character_description', '4 years old, curly brown hair, light skin, blue-green eyes')
    reading_mode = data.get('reading_mode', 'normal')

    if not image_path or not scene_text:
        return jsonify({'error': 'Missing required parameters'}), 400

    try:
        result = story_animation_service.generate_story_animation(
            image_path,
            scene_text,
            character_description,
            reading_mode
        )

        return jsonify(result)
    except Exception as e:
        logging.error(f"Error generating scene animation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# END NEW animation routes

@app.route('/save_story', methods=['POST'])
def save_story():
    """Save story with photo reference metadata"""
    data = request.json
    title = data.get('title')

    if not title:
        return jsonify({'error': 'No title provided'}), 400

    current_story_id = session.get('current_story_id')
    if not current_story_id:
        return jsonify({'error': 'No story to save'}), 400

    try:
        current_story = storage_service.get_temp_story(current_story_id)
        if not current_story:
            return jsonify({'error': 'Story data not found'}), 500

        # Save with photo reference info
        story_id = storage_service.save_story(
            title=title,
            description=current_story['description'],
            character_description=current_story.get('character_description', 'Photo reference used'),
            story_text=current_story['story_text'],
            image_descriptions=current_story.get('image_descriptions', []),
            content=current_story['content'],
            simplified_text=current_story.get('simplified_text', '')
        )

        return jsonify({'success': True, 'story_id': story_id})

    except Exception as e:
        logging.error(f"Error saving story: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_stories')
def get_stories():
    """Get all stories with enhanced metadata."""
    try:
        stories = storage_service.get_all_stories()
        return jsonify({'stories': stories})
    except Exception as e:
        logging.error(f"Error getting stories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/view_story/<story_id>')
def view_story(story_id):
    """View story with enhanced features."""
    try:
        story = storage_service.get_story(story_id)
        has_animations = any(page.get('has_animation', False) for page in story['content'])
        return render_template('story.html', story=story['content'], has_animations=has_animations)
    except Exception as e:
        logging.error(f"Error viewing story {story_id}: {e}")
        return render_template('index.html', error=f"Could not load story: {str(e)}")

@app.route('/delete_story/<story_id>', methods=['DELETE'])
def delete_story(story_id):
    """Delete story."""
    try:
        storage_service.delete_story(story_id)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error deleting story {story_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/story_templates')
def get_story_templates():
    """Get available story templates."""
    templates = {
        'adventure': {
            'name': 'Adventure Story',
            'description': 'Esme explores, discovers, and overcomes challenges',
            'example': 'Esme discovers a hidden cave and finds treasure'
        },
        'mystery': {
            'name': 'Mystery Story', 
            'description': 'Esme solves puzzles and uncovers secrets',
            'example': 'Esme finds clues to solve the missing toy mystery'
        },
        'friendship': {
            'name': 'Friendship Story',
            'description': 'Esme makes new friends and learns about cooperation',
            'example': 'Esme meets a new neighbor and they become best friends'
        },
        'problem_solving': {
            'name': 'Problem-Solving Story',
            'description': 'Esme uses creativity to solve challenges',
            'example': 'Esme builds a bridge to help animals cross the stream'
        }
    }
    return jsonify(templates)

# Initialize database and cleanup on startup
with app.app_context():
    storage_service.init_db()
    storage_service.cleanup_temp_stories()

if __name__ == '__main__':
    print("🌟 Starting Enhanced Esme's Story Generator...")
    print(f"📚 Claude API: {'✓ Ready' if CLAUDE_API_KEY else '✗ Missing'}")
    print(f"🎨 Stability AI: {'✓ Ready' if STABILITY_API_KEY else '✗ Missing'}")
    print(f"🔊 ElevenLabs: {'✓ Ready' if ELEVEN_LABS_API_KEY else '✗ Missing'}")
    print("🚀 Enhanced features: Self-critique stories, better character consistency, predictive timing")

    # NEW: Animation capability status
    if STABILITY_API_KEY:
        print("✨ Story-driven animation capability: ENABLED")
    else:
        print("📖 Story-driven animation capability: DISABLED (no Stability AI key)")

    app.run(host='0.0.0.0', port=8080, debug=True)