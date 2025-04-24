from flask import Flask, request, render_template, jsonify, session
import os
import json
import logging
from pathlib import Path
import uuid
from datetime import datetime
import shutil

# Import services
from services.story_service import StoryService
from services.image_service import ImageService
from services.speech_service import SpeechService
from services.reader_service import ReaderService
from services.storage_service import StorageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Try to load .env file for local development, but this won't be used on Replit
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded .env file for local development")
except ImportError:
    print("python-dotenv not installed, using environment variables directly")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Create necessary directories
os.makedirs('static/images', exist_ok=True)
os.makedirs('temp_stories', exist_ok=True)

# Initialize API keys
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')

# Log API key status
print(f"Claude API Key loaded: {CLAUDE_API_KEY is not None}")
print(f"Stability API Key loaded: {STABILITY_API_KEY is not None}")
print(f"ElevenLabs API Key loaded: {ELEVEN_LABS_API_KEY is not None}")

# Configuration for word highlighting and reading speed
READING_SPEED_SETTINGS = {
    "normal": {
        "base_duration": 200,    # ms per word base time
        "char_duration": 40,     # ms per character
        "speaking_rate": 1.0,    # Normal speed for ElevenLabs
        "playback_rate": 1.0     # Client-side playback rate
    },
    "learning": {
        "base_duration": 700,    # ms per word base time
        "char_duration": 120,    # ms per character
        "speaking_rate": 0.7,    # Slowest possible ElevenLabs speed
        "playback_rate": 0.5     # Additional client-side slowdown
    }
}

# Initialize services
story_service = StoryService(CLAUDE_API_KEY)
image_service = ImageService(STABILITY_API_KEY)
speech_service = SpeechService(ELEVEN_LABS_API_KEY, READING_SPEED_SETTINGS)
reader_service = ReaderService()
storage_service = StorageService()

@app.route('/', methods=['GET'])
def index():
    """Render the main page with the story generation form and library."""
    return render_template('index.html')

@app.route('/get_voices', methods=['GET'])
def get_voices():
    """Get available voices from ElevenLabs API."""
    try:
        voices = speech_service.get_voices()
        return jsonify({"voices": voices})
    except Exception as e:
        logging.error(f"Error fetching voices: {e}")
        return jsonify({"voices": []})

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a story based on user input."""
    description = request.form.get('description')
    character_description = request.form.get('character_description')

    if not description or not character_description:
        return render_template('index.html', 
                              error="Please enter both a description and Esme's appearance!")

    try:
        # Generate the story text
        story_text = story_service.generate_story(description)
        if not story_text:
            return render_template('index.html', 
                                  error="Story generation failed. The service is currently overloaded. Please try again in a few moments.")

        # Process the story into pages/stanzas
        pages = [p.strip() for p in story_text.split('\n\n') if p.strip()]

        # Generate image descriptions
        image_descriptions = story_service.generate_image_descriptions(pages)

        # Generate simplified version for early readers
        simplified_story_text = story_service.generate_simplified_story(story_text)
        simplified_pages = [p.strip() for p in simplified_story_text.split('\n\n') if p.strip()]

        # Process and build the complete story content
        content = []

        for index, text in enumerate(pages):
            # Use the corresponding image description if available, otherwise use the stanza text
            image_description = image_descriptions[index] if index < len(image_descriptions) else text

            # Generate context from previous stanzas
            story_context = ""
            if index > 0:
                context_start = max(0, index - 2)
                previous_stanzas = pages[context_start:index]
                story_context = "Previous story context: " + " ".join(previous_stanzas)

                # Limit context length
                if len(story_context) > 300:
                    story_context = story_context[:297] + "..."

            # Generate image with context
            image_url = image_service.generate_image(
                text, 
                image_description, 
                character_description, 
                story_context=story_context
            )

            # Process the stanza text into structured format
            stanzas = reader_service.process_story_text(text)

            # Process simplified stanzas
            simplified_text = simplified_pages[index] if index < len(simplified_pages) else ""
            simplified_stanzas = reader_service.process_story_text(simplified_text)

            # Add to content list
            content.append({
                'page': index + 1, 
                'text': text, 
                'image': image_url, 
                'stanzas': stanzas,
                'simplified_text': simplified_text,
                'simplified_stanzas': simplified_stanzas
            })

        # Store the current story in session or temporary storage
        temp_id = storage_service.store_temp_story({
            'description': description,
            'character_description': character_description,
            'story_text': story_text,
            'simplified_text': simplified_story_text,
            'image_descriptions': image_descriptions,
            'content': content
        })

        # Store temp_id in session for reference
        session['current_story_id'] = temp_id

        return render_template('story.html', story=content)

    except Exception as e:
        logging.error(f"Error generating story: {e}")
        return render_template('index.html', 
                              error=f"Oops! Something went wrong: {str(e)}")

@app.route('/read', methods=['POST'])
def read_text():
    """Convert text to speech using ElevenLabs API."""
    try:
        data = json.loads(request.data)

        # Validate required parameters
        if 'text' not in data:
            return "No text provided", 400
        if 'voice' not in data:
            return "No voice ID provided", 400

        raw_text = data['text']
        voice_id = data['voice']
        reading_mode = data.get('reading_mode', 'normal')
        reading_speed = data.get('reading_speed', 1.0)

        # Log the request details
        logging.info(f"Read request: mode={reading_mode}, speed={reading_speed}, text_length={len(raw_text)}")

        # Generate audio stream from ElevenLabs
        audio_stream, response_headers = speech_service.generate_speech(
            raw_text, 
            voice_id, 
            reading_mode, 
            reading_speed
        )

        return app.response_class(audio_stream, mimetype='audio/mpeg', headers=response_headers)

    except Exception as e:
        logging.error(f"Error reading text: {e}")
        return f"Error reading text: {str(e)}", 500

@app.route('/save_story', methods=['POST'])
def save_story_route():
    """Save the current story to the database."""
    data = request.json
    title = data.get('title')

    if not title:
        return jsonify({'error': 'No title provided'}), 400

    # Get the current story from session
    current_story_id = session.get('current_story_id')
    if not current_story_id:
        return jsonify({'error': 'No story to save'}), 400

    current_story = storage_service.get_temp_story(current_story_id)
    if not current_story:
        return jsonify({'error': 'Failed to retrieve story data'}), 500

    try:
        # Save the story to the database
        story_id = storage_service.save_story(
            title=title,
            description=current_story['description'],
            character_description=current_story['character_description'],
            story_text=current_story['story_text'],
            image_descriptions=current_story['image_descriptions'],
            content=current_story['content'],
            simplified_text=current_story['simplified_text']
        )

        return jsonify({'success': True, 'story_id': story_id})
    except Exception as e:
        logging.error(f"Error saving story: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_stories', methods=['GET'])
def get_stories_route():
    """Get all stories from the database."""
    try:
        stories = storage_service.get_all_stories()
        return jsonify({'stories': stories})
    except Exception as e:
        logging.error(f"Error getting stories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_story/<story_id>', methods=['GET'])
def get_story_route(story_id):
    """Get a specific story by ID."""
    try:
        story = storage_service.get_story(story_id)
        return jsonify(story)
    except Exception as e:
        logging.error(f"Error getting story {story_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/view_story/<story_id>', methods=['GET'])
def view_story(story_id):
    """Render a specific story by ID."""
    try:
        story = storage_service.get_story(story_id)
        return render_template('story.html', story=story['content'])
    except Exception as e:
        logging.error(f"Error viewing story {story_id}: {e}")
        return render_template('index.html', error=f"Oops! Something went wrong: {str(e)}")

@app.route('/delete_story/<story_id>', methods=['DELETE'])
def delete_story_route(story_id):
    """Delete a story from the database."""
    try:
        storage_service.delete_story(story_id)
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error deleting story {story_id}: {e}")
        return jsonify({'error': str(e)}), 500

# Cleanup routine for temporary stories
def cleanup_temp_stories():
    """Remove old temporary stories."""
    storage_service.cleanup_temp_stories()

# Run cleanup on app startup
with app.app_context():
    storage_service.init_db()
    cleanup_temp_stories()

if __name__ == '__main__':
    # Create all necessary directories if they don't exist
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('prompts', exist_ok=True)
    os.makedirs('services', exist_ok=True)

    print("Starting Esme's Story Generator...")
    print(f"Claude API Key status: {'Available' if CLAUDE_API_KEY else 'Missing'}")
    print(f"Stability API Key status: {'Available' if STABILITY_API_KEY else 'Missing'}")
    print(f"ElevenLabs API Key status: {'Available' if ELEVEN_LABS_API_KEY else 'Missing'}")

    app.run(host='0.0.0.0', port=8080)