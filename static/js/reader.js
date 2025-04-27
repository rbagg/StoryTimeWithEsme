/**
 * Reader JavaScript for Esme's Story Generator
 * Handles the "Learn to Read" mode functionality
 */

// Global variables 
let currentAudio = null;
let currentHighlightInterval = null;
let isHighlighting = false;
let currentReadingMode = 'normal';

// Reading mode settings - this should match the backend Python constants
const READING_SPEED_SETTINGS = {
    "normal": {
        "base_duration": 200,  // ms per word base time
        "char_duration": 40,   // ms per character
        "speaking_rate": 1.0,  // Normal speed for ElevenLabs
        "playback_rate": 1.0   // Client-side playback rate
    },
    "learning": {
        "base_duration": 700,  // ms per word base time
        "char_duration": 120,  // ms per character
        "speaking_rate": 0.7,  // Minimum viable for ElevenLabs
        "playback_rate": 0.5   // Additional client-side slowdown
    }
};

// Initialize reading functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Reader.js loaded, initializing reading components');

    // Restore reading mode from localStorage
    const savedMode = localStorage.getItem('currentReadingMode') || 'normal';
    switchReadingMode(savedMode);

    // Fetch available voices
    loadVoices();

    // Attach click listeners to all stanzas
    attachStanzaListeners();
});

/**
 * Attach click event listeners to all stanzas
 */
function attachStanzaListeners() {
    console.log('Attaching click listeners to stanzas');

    // Select the appropriate stanzas based on current reading mode
    const isLearningMode = currentReadingMode === 'learning';
    const stanzaSelector = isLearningMode ? '.simplified-content .stanza' : '.original-content .stanza';
    const stanzas = document.querySelectorAll(stanzaSelector);

    console.log(`Found ${stanzas.length} stanza elements for mode: ${currentReadingMode}`);

    // First, clear any existing listeners by cloning and replacing elements
    stanzas.forEach(stanza => {
        const newStanza = stanza.cloneNode(true);
        stanza.parentNode.replaceChild(newStanza, stanza);

        // Add a click listener to the new clone
        newStanza.addEventListener('click', function() {
            console.log(`Stanza clicked: ${this.id}`);
            readStanza(this.id);
        });
    });
}

/**
 * Switch between normal and learning reading modes
 * @param {string} mode - Reading mode to switch to ('normal' or 'learning')
 */
function switchReadingMode(mode) {
    // Store previous mode for comparison
    const previousMode = currentReadingMode;

    // Update current mode
    currentReadingMode = mode;

    // Update UI
    document.querySelectorAll('.reading-mode-button').forEach(btn => {
        btn.classList.remove('active');
    });

    const activeButton = document.getElementById(`${mode}ModeButton`);
    if (activeButton) {
        activeButton.classList.add('active');
    }

    // Show appropriate content
    const originalContent = document.querySelectorAll('.original-content');
    const simplifiedContent = document.querySelectorAll('.simplified-content');

    originalContent.forEach(el => {
        el.style.display = mode === 'normal' ? 'block' : 'none';
    });

    simplifiedContent.forEach(el => {
        el.style.display = mode === 'learning' ? 'block' : 'none';
    });

    // Log the mode change
    console.log(`Reading mode switched from ${previousMode} to ${mode}`);
    console.log(`Using reading settings: ${JSON.stringify(READING_SPEED_SETTINGS[mode])}`);

    // Re-attach stanza listeners after switching mode
    attachStanzaListeners();

    // Store the current mode in localStorage to persist between page loads
    localStorage.setItem('currentReadingMode', mode);
}

/**
 * Load available voices from the server
 */
async function loadVoices() {
    try {
        console.log('Loading voices...');
        const voiceSelect = document.getElementById('voiceSelect');

        if (!voiceSelect) {
            console.error('Voice select element not found');
            return;
        }

        // Set loading state
        voiceSelect.innerHTML = '<option value="" disabled selected>Loading voices...</option>';

        const response = await fetch('/get_voices');
        if (!response.ok) {
            throw new Error(`Failed to fetch voices: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.voices || !Array.isArray(data.voices) || data.voices.length === 0) {
            voiceSelect.innerHTML = '<option value="" disabled selected>No voices available</option>';
            console.error('No voices returned from API');
            return;
        }

        // Clear and populate dropdown
        voiceSelect.innerHTML = '';

        console.log(`Loaded ${data.voices.length} voices`);

        // Add voices to dropdown
        data.voices.forEach((voice, index) => {
            const option = document.createElement('option');
            option.value = voice.id;
            option.textContent = voice.name;
            // Select the first voice by default
            if (index === 0) {
                option.selected = true;
            }
            voiceSelect.appendChild(option);
        });

        console.log(`Set default voice: ${data.voices[0].name}`);
    } catch (error) {
        console.error('Error loading voices:', error);
        const voiceSelect = document.getElementById('voiceSelect');
        if (voiceSelect) {
            voiceSelect.innerHTML = '<option value="" disabled selected>Error loading voices</option>';
        }
    }
}

/**
 * Read a stanza aloud with synchronized word highlighting
 * @param {string} stanzaId - The ID of the stanza to read
 */
async function readStanza(stanzaId) {
    console.log(`readStanza called for: ${stanzaId}`);
    console.log(`Active reading mode: ${currentReadingMode}`);

    // Stop any currently playing audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
        console.log('Stopped previous audio');
    }

    // Clear any ongoing highlighting
    if (currentHighlightInterval) {
        clearTimeout(currentHighlightInterval);
        currentHighlightInterval = null;
        console.log('Cleared previous highlighting');
    }

    // Remove any existing highlights
    document.querySelectorAll('.word.highlight').forEach(word => {
        word.classList.remove('highlight');
    });

    const stanza = document.getElementById(stanzaId);
    if (!stanza) {
        console.error(`Stanza element not found with ID: ${stanzaId}`);
        return;
    }

    // Add active class to the stanza
    document.querySelectorAll('.stanza').forEach(s => {
        s.classList.remove('active');
    });
    stanza.classList.add('active');

    // Get the words
    const words = stanza.getElementsByClassName('word');
    if (!words || words.length === 0) {
        console.error('No word elements found in stanza');
        return;
    }

    const text = Array.from(words).map(word => word.textContent.trim()).join(' ');
    const voiceSelect = document.getElementById('voiceSelect');

    if (!voiceSelect || !voiceSelect.value) {
        alert('Please select a voice before reading');
        return;
    }

    try {
        // Show loading indicator
        stanza.classList.add('loading');

        // Get the mode-specific settings
        const modeSettings = READING_SPEED_SETTINGS[currentReadingMode];

        // Prepare the request
        const requestBody = { 
            text, 
            voice: voiceSelect.value,
            reading_mode: currentReadingMode
        };

        console.log('Sending read request:', requestBody);

        const response = await fetch('/read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        // Remove loading indicator
        stanza.classList.remove('loading');

        // Check for error in response headers
        const errorMessage = response.headers.get('X-Error');
        if (errorMessage) {
            console.error('API Error:', errorMessage);
            alert(`Text-to-speech error: ${errorMessage}`);
            return;
        }

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error:', errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        // Extract custom headers with reading settings
        const playbackRate = parseFloat(response.headers.get('X-Playback-Rate') || modeSettings.playback_rate);
        const wordCount = parseInt(response.headers.get('X-Word-Count') || words.length);

        console.log(`Server returned playback rate: ${playbackRate}, word count: ${wordCount}`);

        const audioBlob = await response.blob();
        if (!audioBlob || audioBlob.size === 0) {
            throw new Error('Received empty audio data');
        }

        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        // Set the playback rate for the browser's audio element
        audio.playbackRate = playbackRate;
        console.log(`Setting browser playback rate to: ${playbackRate}`);

        // Configure error handling
        audio.onerror = (e) => {
            console.error('Audio playback error:', e);
            stanza.classList.remove('loading');
            alert('Error playing audio. Please try again.');
        };

        // Store for potential cleanup
        currentAudio = audio;

        // Start highlighting words when audio starts playing
        audio.addEventListener('playing', function() {
            console.log('Audio playback started, beginning word highlighting');
            startWordHighlighting(words);
        });

        // Clean up when audio ends
        audio.addEventListener('ended', function() {
            console.log('Audio playback complete');
            currentAudio = null;

            if (currentHighlightInterval) {
                clearTimeout(currentHighlightInterval);
                currentHighlightInterval = null;
            }

            // Remove all highlights
            document.querySelectorAll('.word.highlight').forEach(word => {
                word.classList.remove('highlight');
            });

            // Remove active class from stanza
            stanza.classList.remove('active');
        });

        // Try to play audio
        try {
            await audio.play();
            console.log('Audio playing');
        } catch (playError) {
            console.error('Audio play error:', playError);

            // Check if it's a user interaction issue
            if (playError.name === 'NotAllowedError') {
                alert('Please interact with the page first before playing audio (browser security policy)');
            } else {
                alert('Could not play audio. Please check your speakers and try again.');
            }
            throw playError;
        }
    } catch (error) {
        console.error('Error getting or playing audio:', error);
        stanza.classList.remove('loading');
        alert(`Error: ${error.message || 'Could not play audio'}`);
    }
}

/**
 * Start highlighting words with improved synchronization to speech
 * @param {HTMLCollection} words - Collection of word elements to highlight
 */
function startWordHighlighting(words) {
    let currentIndex = 0;
    isHighlighting = true;

    // Calculate the total text length and approximate duration
    const totalWords = words.length;
    const audioElement = currentAudio;

    if (!audioElement || !audioElement.duration) {
        console.warn("Cannot determine audio duration - using fallback timing");
        // Call the legacy timing function if we can't determine the audio duration
        startHighlightingWithFallbackTiming(words);
        return;
    }

    // Get the total audio duration in milliseconds
    const totalDuration = audioElement.duration * 1000;

    // Calculate average time per word, with a bit of buffer at the end
    const timePerWord = totalDuration / (totalWords + 1);
    console.log(`Audio duration: ${totalDuration}ms, Words: ${totalWords}, Average time per word: ${timePerWord}ms`);

    // Set up a timeUpdate listener to sync highlighting with audio
    let lastTimeUpdatePosition = 0;

    function updateHighlighting() {
        // Check if audio is still playing
        if (!audioElement || audioElement.paused || audioElement.ended) {
            return;
        }

        // Calculate which word should be highlighted based on current audio position
        const currentTime = audioElement.currentTime * 1000;
        const estimatedWordIndex = Math.floor(currentTime / timePerWord);

        // Only update if needed (prevents jitter and improves performance)
        if (estimatedWordIndex !== currentIndex && estimatedWordIndex < words.length) {
            // Clear all highlights
            document.querySelectorAll('.word.highlight').forEach(word => {
                word.classList.remove('highlight');
            });

            // Update the index and add highlight
            currentIndex = estimatedWordIndex;
            words[currentIndex].classList.add('highlight');

            // Scroll word into view if needed
            words[currentIndex].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center', 
                inline: 'nearest' 
            });
        }

        // Continue updating
        if (!audioElement.paused && !audioElement.ended) {
            requestAnimationFrame(updateHighlighting);
        } else {
            // Clean up when done
            document.querySelectorAll('.word.highlight').forEach(word => {
                word.classList.remove('highlight');
            });
            isHighlighting = false;
        }
    }

    // Start the highlighting update loop
    requestAnimationFrame(updateHighlighting);

    // Attach additional safety timeUpdate listener
    audioElement.addEventListener('timeupdate', function() {
        // If no updates for 1 second, restart the update loop
        const currentPosition = audioElement.currentTime;
        if (Math.abs(currentPosition - lastTimeUpdatePosition) > 1.0) {
            lastTimeUpdatePosition = currentPosition;
            requestAnimationFrame(updateHighlighting);
        }
    });
}

/**
 * Fallback timing method when audio duration can't be determined
 * @param {HTMLCollection} words - Collection of word elements to highlight
 */
function startHighlightingWithFallbackTiming(words) {
    let currentIndex = 0;

    function highlightNext() {
        // If audio has ended or was paused, stop highlighting
        if (!currentAudio || currentAudio.ended || currentAudio.paused) {
            document.querySelectorAll('.word.highlight').forEach(word => {
                word.classList.remove('highlight');
            });
            isHighlighting = false;
            return;
        }

        // Clear any previous highlights
        document.querySelectorAll('.word.highlight').forEach(word => {
            word.classList.remove('highlight');
        });

        if (currentIndex < words.length) {
            // Add highlight to current word
            words[currentIndex].classList.add('highlight');

            // Scroll word into view if needed
            words[currentIndex].scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center', 
                inline: 'nearest' 
            });

            // Simplified timing based on word length only
            const wordLength = words[currentIndex].textContent.length;

            // Faster timing for better synchronization
            // Base duration depends on reading mode
            const baseDuration = currentReadingMode === 'learning' ? 400 : 200;
            const charFactor = currentReadingMode === 'learning' ? 40 : 25;

            // Calculate adjusted duration
            const highlightDuration = baseDuration + (wordLength * charFactor);

            // Schedule next word
            currentIndex++;
            currentHighlightInterval = setTimeout(highlightNext, highlightDuration);
        } else {
            // All words have been highlighted
            console.log('Word highlighting complete');
            currentHighlightInterval = null;
            isHighlighting = false;
        }
    }

    // Start highlighting the first word
    highlightNext();
}