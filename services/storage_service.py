import os
import json
import sqlite3
import logging
import uuid
import shutil
from datetime import datetime

class StorageService:
    """Service for handling database operations and temporary story storage."""

    def __init__(self, db_path="stories.db", temp_dir="temp_stories"):
        """Initialize StorageService.

        Args:
            db_path (str): Path to the SQLite database
            temp_dir (str): Directory for temporary story storage
        """
        self.db_path = db_path
        self.temp_dir = temp_dir

        # Ensure temporary directory exists
        os.makedirs(temp_dir, exist_ok=True)

    def init_db(self):
        """Initialize the database schema."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Create stories table if it doesn't exist
            c.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                character_description TEXT,
                created_at TEXT,
                story_text TEXT,
                simplified_text TEXT,
                image_descriptions TEXT,
                content JSON
            )
            ''')

            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing database: {e}")
            raise

    def store_temp_story(self, story_data):
        """Store story data in a temporary file.

        Args:
            story_data (dict): Story data to store

        Returns:
            str: Temporary story ID
        """
        try:
            temp_id = str(uuid.uuid4())
            story_dir = os.path.join(self.temp_dir, temp_id)
            os.makedirs(story_dir, exist_ok=True)

            with open(os.path.join(story_dir, 'story_data.json'), 'w') as f:
                data_to_store = {
                    'description': story_data.get('description', ''),
                    'character_description': story_data.get('character_description', ''),
                    'story_text': story_data.get('story_text', ''),
                    'simplified_text': story_data.get('simplified_text', ''),
                    'image_descriptions': story_data.get('image_descriptions', []),
                    'temp_id': temp_id,
                    'created_at': datetime.now().isoformat()
                }
                json.dump(data_to_store, f)

            with open(os.path.join(story_dir, 'content.json'), 'w') as f:
                json.dump(story_data.get('content', []), f)

            logging.info(f"Stored temporary story with ID: {temp_id}")
            return temp_id
        except Exception as e:
            logging.error(f"Error storing temporary story: {e}")
            return None

    def get_temp_story(self, temp_id):
        """Get story data from a temporary file.

        Args:
            temp_id (str): Temporary story ID

        Returns:
            dict: Story data
        """
        try:
            story_dir = os.path.join(self.temp_dir, temp_id)

            with open(os.path.join(story_dir, 'story_data.json'), 'r') as f:
                story_data = json.load(f)

            with open(os.path.join(story_dir, 'content.json'), 'r') as f:
                content = json.load(f)

            story_data['content'] = content
            return story_data
        except Exception as e:
            logging.error(f"Error retrieving temporary story {temp_id}: {e}")
            return None

    def cleanup_temp_stories(self, max_age_hours=24):
        """Remove temporary stories older than the specified age.

        Args:
            max_age_hours (int): Maximum age in hours before deletion
        """
        try:
            now = datetime.now()
            count_removed = 0

            for item in os.listdir(self.temp_dir):
                story_dir = os.path.join(self.temp_dir, item)
                if os.path.isdir(story_dir):
                    try:
                        data_file = os.path.join(story_dir, 'story_data.json')
                        if os.path.exists(data_file):
                            with open(data_file, 'r') as f:
                                story_data = json.load(f)
                            created_at = datetime.fromisoformat(story_data.get('created_at', ''))
                            age_hours = (now - created_at).total_seconds() / 3600
                            if age_hours > max_age_hours:
                                shutil.rmtree(story_dir)
                                count_removed += 1
                        else:
                            # No data file, remove the directory
                            shutil.rmtree(story_dir)
                            count_removed += 1
                    except Exception as e:
                        logging.error(f"Error cleaning up temporary story {item}: {e}")
                        continue

            logging.info(f"Cleaned up {count_removed} temporary stories older than {max_age_hours} hours")
        except Exception as e:
            logging.error(f"Error cleaning up temporary stories: {e}")

    def save_story(self, title, description, character_description, story_text, image_descriptions, content, simplified_text=None):
        """Save a story to the database.

        Args:
            title (str): Story title
            description (str): Story description
            character_description (str): Character description
            story_text (str): Full story text
            image_descriptions (list): List of image descriptions
            content (list): Processed story content
            simplified_text (str, optional): Simplified version of the story

        Returns:
            str: Story ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            story_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()

            # Convert content to JSON string for storage
            content_json = json.dumps(content)

            # Convert image_descriptions to JSON string for storage
            image_descriptions_json = json.dumps(image_descriptions)

            c.execute('''
            INSERT INTO stories (id, title, description, character_description, created_at, story_text, simplified_text, image_descriptions, content)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (story_id, title, description, character_description, created_at, story_text, simplified_text, image_descriptions_json, content_json))

            conn.commit()
            conn.close()

            logging.info(f"Saved story '{title}' with ID: {story_id}")
            return story_id
        except Exception as e:
            logging.error(f"Error saving story to database: {e}")
            raise

    def get_all_stories(self):
        """Get all stories from the database.

        Returns:
            list: List of stories with basic information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables accessing columns by name
            c = conn.cursor()

            c.execute('''
            SELECT id, title, description, created_at FROM stories ORDER BY created_at DESC
            ''')

            stories = [dict(row) for row in c.fetchall()]
            conn.close()

            logging.info(f"Retrieved {len(stories)} stories from database")
            return stories
        except Exception as e:
            logging.error(f"Error getting stories from database: {e}")
            raise

    def get_story(self, story_id):
        """Get a specific story by ID.

        Args:
            story_id (str): Story ID

        Returns:
            dict: Story data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute('SELECT * FROM stories WHERE id = ?', (story_id,))
            row = c.fetchone()

            if not row:
                raise ValueError(f"Story with ID {story_id} not found")

            story = dict(row)

            # Parse JSON strings back to Python objects
            story['content'] = json.loads(story['content'])
            story['image_descriptions'] = json.loads(story['image_descriptions'])

            conn.close()
            return story
        except Exception as e:
            logging.error(f"Error getting story {story_id}: {e}")
            raise

    def delete_story(self, story_id):
        """Delete a story from the database.

        Args:
            story_id (str): Story ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM stories WHERE id = ?', (story_id,))
            conn.commit()
            conn.close()
            logging.info(f"Deleted story with ID: {story_id}")
        except Exception as e:
            logging.error(f"Error deleting story {story_id}: {e}")
            raise