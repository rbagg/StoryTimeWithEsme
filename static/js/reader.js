/**
 * Reader JavaScript for Esme's Story Generator
 * Handles the "Learn to Read" mode functionality
 */

// Global variables for tracking audio and highlighting state
let currentAudio = null;
let currentHighlightInterval = null;
let isHighlighting = false;

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
        "speaking_rate": 0.7,  // Slower for ElevenLabs
        "playback_rate": 0.5   // Slower client-side playback
    }
};

// Initialize reading functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Reader.js loaded, initializing reading components');

    // Restore reading mode from localStorage
    const savedMode = localStorage.getItem('currentReadingMode') || 'normal';
    switchReadingMode(savedMode);

    // Restore reading speed from localStorage
    const savedSpeed = localStorage.getItem('readingSpeed') || '1.0';
    updateReadingSpeed(parseFloat(savedSpeed));

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

    // Log the mode change and current settings
    console.log(`Reading mode switched from ${previousMode} to ${mode}`);

    // Re-attach stanza listeners after switching mode
    attachStanzaListeners();

    // Store the current mode in localStorage to persist between page loads
    localStorage.setItem('currentReadingMode', mode);
}

/**
 * Update the reading speed
 * @param {number} value - Speed multiplier (0.5 = half speed, 1.0 = normal, 1.5 = faster)
 */
function updateReadingSpeed(value) {
    readingSpeed = parseFloat(value);

    // Update button states
    document.querySelectorAll('.speed-btn').forEach(btn => {
        btn.classList.remove('active');
        if (parseFloat(btn.dataset.speed) === value) {
            btn.classList.add('active');
        }
    });

    // Store the speed value
    localStorage.setItem('readingSpeed', value);
    console.log(`Reading speed updated to: ${readingSpeed}x`);
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

        // Prepare the request
        const requestBody = { 
            text, 
            voice: voiceSelect.value,
            reading_mode: currentReadingMode,
            reading_speed: readingSpeed
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

        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error:', errorText);
            throw new Error(`Server error: ${response.status} - ${errorText}`);
        }

        // Extract custom headers with reading settings
        const effectiveRate = response.headers.get('X-Effective-Rate') || '1.0';
        const playbackRate = response.headers.get('X-Playback-Rate') || '1.0';

        console.log(`Server returned effective rate: ${effectiveRate}, playback rate: ${playbackRate}`);

        const audioBlob = await response.blob();
        if (!audioBlob || audioBlob.size === 0) {
            throw new Error('Received empty audio data');
        }

        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        // Configure audio
        audio.playbackRate = parseFloat(playbackRate);

        // Set up error handling
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
 * Start highlighting words with timing based on word complexity
 * @param {HTMLCollection} words - Collection of word elements to highlight
 */
function startWordHighlighting(words) {
    let currentIndex = 0;
    isHighlighting = true;

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

            // Determine word type for additional styling
            const wordText = words[currentIndex].textContent.trim().toLowerCase();
            const wordType = classifyWordType(wordText);

            // Add word type class
            words[currentIndex].classList.add(wordType);

            // Calculate timing based on word length and current mode settings
            const wordLength = words[currentIndex].textContent.length;
            const settings = READING_SPEED_SETTINGS[currentReadingMode];

            // Base timing calculation
            const baseTime = settings.base_duration;
            const charTime = settings.char_duration * wordLength;

            // Calculate final duration with speed adjustment
            const highlightDuration = Math.max(300, (baseTime + charTime)) / readingSpeed;

            // Log detailed timing for debugging
            console.log(`Word: "${words[currentIndex].textContent}", type: ${wordType}, duration: ${highlightDuration.toFixed(0)}ms`);

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

/**
 * Classify a word as sight word, vocabulary word, or regular word
 * @param {string} word - The word to classify
 * @returns {string} - Classification of the word
 */
function classifyWordType(word) {
    // Clean the word for analysis
    const cleanWord = word.replace(/[^\w\s]/g, '').toLowerCase();

    // Simple list of common sight words for early readers
    const sightWords = [
        'a', 'and', 'away', 'big', 'blue', 'can', 'come', 'down', 'find', 'for', 'funny',
        'go', 'help', 'here', 'i', 'in', 'is', 'it', 'jump', 'little', 'look', 'make',
        'me', 'my', 'not', 'one', 'play', 'red', 'run', 'said', 'see', 'the', 'three',
        'to', 'two', 'up', 'we', 'where', 'yellow', 'you', 'all', 'am', 'are', 'at', 'ate',
        'be', 'black', 'brown', 'but', 'came', 'did', 'do', 'eat', 'four', 'get', 'good',
        'have', 'he', 'into', 'like', 'must', 'new', 'no', 'now', 'on', 'our', 'out', 'please',
        'pretty', 'ran', 'ride', 'saw', 'say', 'she', 'so', 'soon', 'that', 'there', 'they',
        'this', 'too', 'under', 'want', 'was', 'well', 'went', 'what', 'white', 'who', 'will',
        'with', 'yes'
    ];

    // Check if it's a sight word
    if (sightWords.includes(cleanWord)) {
        return 'sight-word';
    }

    // Check for vocabulary word characteristics
    // Words with more than 7 letters or uncommon patterns
    if (cleanWord.length > 7 || 
        /[aeiou]{3}/.test(cleanWord) || 
        /(ph|gh|th|wh|qu|sc|ck|dge|tch|sch)/.test(cleanWord)) {
        return 'vocabulary-word';
    }

    // Default classification
    return 'regular-word';
}