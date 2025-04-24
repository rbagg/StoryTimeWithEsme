# Esme's Story Generator

A Flask web application that generates rhyming children's stories with matching illustrations and text-to-speech narration for a character named Esme. Perfect for early childhood education with a "Learn to Read" mode.

## Features

- **Story Generation**: Creates engaging, educational rhyming stories using Claude API
- **Image Generation**: Produces consistent, child-friendly illustrations using Stability AI
- **Text-to-Speech**: Narrates the story with ElevenLabs voice synthesis
- **Learn to Read Mode**: Highlights words in sync with the narration to help children learn to read
- **Simplified Text**: Provides an alternative simplified version for early readers
- **Story Library**: Save and load previously created stories

## Application Structure

The application follows a modular, component-based structure:

```
/
├── app.py                 # Main application file with routes
├── requirements.txt       # Dependencies
├── .env.example           # Example environment variables
├── .replit                # Replit configuration
├── README.md              # Setup and usage instructions
├── /templates
│   ├── base.html          # Base template
│   ├── index.html         # Main page template
│   └── story.html         # Story display template
├── /static
│   ├── /css
│   │   ├── main.css       # Main styles
│   │   └── reader.css     # Learn to Read specific styles
│   ├── /js
│   │   ├── main.js        # Main functionality
│   │   └── reader.js      # Learn to Read functionality
│   └── /images            # Generated images storage
├── /prompts
│   ├── story_prompt.txt                # Story generation prompt
│   ├── simplified_story_prompt.txt     # Simplified story prompt
│   ├── image_prompt.txt                # Image generation prompt
│   ├── image_description_prompt.txt    # Image description prompt
│   └── reader_prompt.txt               # Learn to Read optimization prompt
└── /services
    ├── __init__.py
    ├── story_service.py   # Story generation logic
    ├── image_service.py   # Image generation logic
    ├── speech_service.py  # Text-to-speech logic
    ├── reader_service.py  # Learn to Read optimization logic
    └── storage_service.py # Database and file storage logic
```

## Prerequisites

- Python 3.8 or higher
- API keys for:
  - [Claude](https://anthropic.com/) (for story generation)
  - [Stability AI](https://stability.ai/) (for image generation)
  - [ElevenLabs](https://elevenlabs.io/) (for text-to-speech)

## Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/esmes-story-generator.git
   cd esmes-story-generator
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys (copy from `.env.example`):
   ```
   CLAUDE_API_KEY=your_claude_api_key_here
   STABILITY_API_KEY=your_stability_api_key_here
   ELEVEN_LABS_API_KEY=your_elevenlabs_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   ```

5. Run the application:
   ```bash
   python app.py
   ```

6. Open your browser and navigate to `http://localhost:8080`

## Replit Deployment

### Step 1: Create a New Replit Project

1. Go to [Replit](https://replit.com/) and sign in or create an account.
2. Click on the "Create" button to create a new Repl.
3. Select "Python" as the template.
4. Name your project (e.g., "esmes-story-generator").
5. Click "Create Repl".

### Step 2: Set Up the Project Structure

1. Delete any initial files that Replit creates (like `main.py`).
2. Upload all the files from this repository to your Repl, maintaining the directory structure.
   - You can drag and drop folders into the Replit file explorer.
   - Alternatively, you can use the Replit Git integration to clone the repository.

### Step 3: Configure API Keys as Secrets

1. In your Repl, click on the padlock icon (🔒) in the left sidebar to access the "Secrets" panel.
2. Add the following secrets with your API keys:
   - Key: `CLAUDE_API_KEY`, Value: your Claude API key
   - Key: `STABILITY_API_KEY`, Value: your Stability AI API key
   - Key: `ELEVEN_LABS_API_KEY`, Value: your ElevenLabs API key
   - Key: `FLASK_SECRET_KEY`, Value: a secure random string for session encryption
3. Click "Add new secret" after entering each key-value pair.
4. These secrets will be automatically available as environment variables to your application.

### Step 4: Install Dependencies

1. Replit will automatically detect and install the dependencies from `requirements.txt` when you run the application.
2. You don't need to manually install dependencies, but if you want to ensure they're installed correctly, you can run this command in the Replit Shell:
   ```bash
   pip install -r requirements.txt
   ```

### Step 5: Run the Application

1. Click the "Run" button at the top of the Replit interface.
2. Replit will start the Flask server and automatically open a web browser window showing your application.
3. If everything is set up correctly, you should see the Esme's Story Generator interface.

### Step 6: Troubleshooting Common Issues

#### Issue: Application Not Starting
- Check the console output for error messages.
- Verify that all API keys are correctly set in the Secrets panel.
- Make sure all dependencies are installed correctly.

#### Issue: Images Not Generating
- Verify your Stability AI API key is correct.
- Check if the `/static/images` directory exists and has write permissions.
- Look for specific error messages in the console logs.

#### Issue: Audio Not Playing
- Verify your ElevenLabs API key is correct.
- Some browsers require user interaction before playing audio; make sure to click on the page first.
- Check browser console for specific errors related to audio playback.

#### Issue: Database Errors
- The application uses SQLite, which should work out of the box.
- If you see database errors, make sure the application has write permissions to create the database file.

## Using the Application

1. **Creating a Story**:
   - Enter a description of the adventure (e.g., "Esme goes camping with her family")
   - Provide a physical description of Esme (e.g., "4-year-old girl with curly brown hair and blue eyes")
   - Click "Generate Story" to create a new story

2. **Reading a Story**:
   - Select a voice from the dropdown menu
   - Click on any stanza to hear it read aloud with synchronized word highlighting
   - Use the speed controls to adjust the reading speed

3. **Learn to Read Mode**:
   - Click the "Learning to Read" button to switch to simplified text mode
   - The text will be simplified for early readers with shorter sentences and simpler vocabulary
   - Word highlighting is slower and more prominent in this mode

4. **Saving Stories**:
   - Click "Save Story" when viewing a story
   - Enter a title for the story
   - The story will be saved to your library

5. **Library**:
   - Click the "Story Library" tab to view all saved stories
   - Click on a story card to load and view that story
   - Use the delete button to remove stories from your library

## Customizing the Application

### Modifying Prompt Templates

You can customize the stories by editing the prompt templates in the `/prompts` directory:

- `story_prompt.txt`: Change the structure, style, or themes of the generated stories.
- `simplified_story_prompt.txt`: Modify how the simplified version is created.
- `image_prompt.txt`: Adjust the visual style, character appearance, or scene composition.
- `image_description_prompt.txt`: Change how scene descriptions are generated.
- `reader_prompt.txt`: Modify how the "Learn to Read" mode processes and highlights words.

### Styling Changes

- Modify `static/css/main.css` to change the overall look and feel.
- Edit `static/css/reader.css` to customize the "Learn to Read" mode appearance.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Claude API](https://anthropic.com/) for story generation
- [Stability AI](https://stability.ai/) for image generation
- [ElevenLabs](https://elevenlabs.io/) for text-to-speech synthesis