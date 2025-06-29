/**
 * Complete Reader JavaScript with SLOWER word highlighting
 * Replace your entire static/js/reader.js file with this code
 */

// Global variables
let currentAudio = null;
let currentHighlightInterval = null;
let isHighlighting = false;
let currentReadingMode = 'normal';
let audioStartTime = null;
let highlightStartTime = null;

// Word classification for highlighting styles
const WORD_TYPES = {
    'sight-word': 'sight-word-highlight',
    'phonics-word': 'phonics-word-highlight', 
    'complex-word': 'complex-word-highlight',
    'regular-word': 'regular-word-highlight'
};

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Complete Reader.js loaded with SLOWER highlighting');

    // Restore reading mode
    const savedMode = localStorage.getItem('currentReadingMode') || 'normal';
    switchReadingMode(savedMode);

    // Load voices
    loadVoices();

    // Attach stanza listeners
    attachStanzaListeners();

    // Initialize word styling and legend
    initializeWordStyling();
    addWordTypeLegend();
});

/**
 * Add word type legend to the page
 */
function addWordTypeLegend() {
    // Check if legend already exists
    if (document.getElementById('word-legend')) {
        return;
    }

    const legend = document.createElement('div');
    legend.id = 'word-legend';
    legend.className = 'word-legend';
    legend.innerHTML = `
        <h4>Word Types Guide</h4>
        <div class="legend-items">
            <div class="legend-item">
                <span class="legend-color sight-word-sample">the</span>
                <span class="legend-text">Sight Words (green) - Words to recognize instantly</span>
            </div>
            <div class="legend-item">
                <span class="legend-color phonics-word-sample">cat</span>
                <span class="legend-text">Phonics Words (blue) - Sound out these words</span>
            </div>
            <div class="legend-item">
                <span class="legend-color complex-word-sample">wonderful</span>
                <span class="legend-text">Complex Words (pink) - Practice these together</span>
            </div>
        </div>
    `;

    // Add to the page
    const storyContainer = document.querySelector('.story-container');
    if (storyContainer) {
        storyContainer.insertBefore(legend, storyContainer.firstChild.nextSibling);
    }
}

/**
 * Enhanced reading mode switching
 */
function switchReadingMode(mode) {
    const previousMode = currentReadingMode;
    currentReadingMode = mode;

    console.log(`Mode switch: ${previousMode} → ${mode}`);

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

    // Update legend visibility based on mode
    const legend = document.getElementById('word-legend');
    if (legend) {
        legend.style.display = mode === 'learning' ? 'block' : 'none';
    }

    // Re-attach listeners and update styling
    attachStanzaListeners();
    updateWordStyling(mode);

    // Save mode
    localStorage.setItem('currentReadingMode', mode);
}

/**
 * Initialize word type styling
 */
function initializeWordStyling() {
    document.querySelectorAll('.word').forEach(wordElement => {
        const word = wordElement.textContent.trim();
        const wordType = classifyWordType(word);

        // Add word type class for styling
        wordElement.classList.add(WORD_TYPES[wordType] || 'regular-word-highlight');
        wordElement.setAttribute('data-word-type', wordType);
    });
}

/**
 * Update word styling based on reading mode
 */
function updateWordStyling(mode) {
    document.querySelectorAll('.word').forEach(wordElement => {
        if (mode === 'learning') {
            wordElement.classList.add('learning-mode-word');
        } else {
            wordElement.classList.remove('learning-mode-word');
        }
    });
}

/**
 * Enhanced word classification
 */
function classifyWordType(word) {
    const cleanWord = word.toLowerCase().replace(/[^\w]/g, '');

    // Sight words list
    const sightWords = [
        'a', 'and', 'away', 'big', 'blue', 'can', 'come', 'down', 'find', 'for', 'funny',
        'go', 'help', 'here', 'I', 'in', 'is', 'it', 'jump', 'little', 'look', 'make',
        'me', 'my', 'not', 'one', 'play', 'red', 'run', 'said', 'see', 'the', 'three',
        'to', 'two', 'up', 'we', 'where', 'yellow', 'you', 'all', 'am', 'are', 'at'
    ];

    if (sightWords.includes(cleanWord)) {
        return 'sight-word';
    }

    // Simple phonics patterns (CVC)
    if (/^[bcdfghjklmnpqrstvwxyz][aeiou][bcdfghjklmnpqrstvwxyz]$/.test(cleanWord)) {
        return 'phonics-word';
    }

    // Complex words
    if (cleanWord.length > 6 || /[aeiou]{2,}|[bcdfghjklmnpqrstvwxyz]{3,}/.test(cleanWord)) {
        return 'complex-word';
    }

    return 'regular-word';
}

/**
 * Enhanced voice loading
 */
async function loadVoices() {
    try {
        const voiceSelect = document.getElementById('voiceSelect');
        if (!voiceSelect) return;

        voiceSelect.innerHTML = '<option value="" disabled selected>Loading voices...</option>';

        const response = await fetch('/get_voices');
        if (!response.ok) throw new Error(`Voice loading failed: ${response.status}`);

        const data = await response.json();
        if (!data.voices || data.voices.length === 0) {
            voiceSelect.innerHTML = '<option value="" disabled selected>No voices available</option>';
            return;
        }

        voiceSelect.innerHTML = '';

        // Group voices by suitability
        const childFriendlyVoices = [];
        const otherVoices = [];

        data.voices.forEach(voice => {
            const voiceName = voice.name.toLowerCase();
            if (voiceName.includes('child') || voiceName.includes('young') || 
                voiceName.includes('female') || voiceName.includes('gentle')) {
                childFriendlyVoices.push(voice);
            } else {
                otherVoices.push(voice);
            }
        });

        // Add grouped options
        if (childFriendlyVoices.length > 0) {
            const childGroup = document.createElement('optgroup');
            childGroup.label = 'Recommended for Children';
            childFriendlyVoices.forEach((voice, index) => {
                const option = document.createElement('option');
                option.value = voice.id;
                option.textContent = voice.name;
                if (index === 0) option.selected = true;
                childGroup.appendChild(option);
            });
            voiceSelect.appendChild(childGroup);
        }

        if (otherVoices.length > 0) {
            const otherGroup = document.createElement('optgroup');
            otherGroup.label = 'Other Voices';
            otherVoices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.id;
                option.textContent = voice.name;
                otherGroup.appendChild(option);
            });
            voiceSelect.appendChild(otherGroup);
        }

        console.log(`Voice loading complete: ${data.voices.length} voices organized`);

    } catch (error) {
        console.error('Voice loading error:', error);
        const voiceSelect = document.getElementById('voiceSelect');
        if (voiceSelect) {
            voiceSelect.innerHTML = '<option value="" disabled selected>Error loading voices</option>';
        }
    }
}

/**
 * Attach stanza listeners
 */
function attachStanzaListeners() {
    const isLearningMode = currentReadingMode === 'learning';
    const stanzaSelector = isLearningMode ? '.simplified-content .stanza' : '.original-content .stanza';
    const stanzas = document.querySelectorAll(stanzaSelector);

    console.log(`Found ${stanzas.length} stanzas for ${currentReadingMode} mode`);

    stanzas.forEach(stanza => {
        const newStanza = stanza.cloneNode(true);
        stanza.parentNode.replaceChild(newStanza, stanza);

        newStanza.addEventListener('click', function(event) {
            event.preventDefault();
            console.log(`Stanza clicked: ${this.id}`);
            readStanzaWithSlowerSync(this.id);
        });
    });
}

/**
 * Stanza reading with MUCH SLOWER synchronization
 */
async function readStanzaWithSlowerSync(stanzaId) {
    console.log(`Starting SLOWER sync reading: ${stanzaId}`);

    // Stop any current audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    clearAllHighlights();

    const stanza = document.getElementById(stanzaId);
    if (!stanza) {
        console.error(`Stanza not found: ${stanzaId}`);
        return;
    }

    const words = stanza.getElementsByClassName('word');
    if (!words || words.length === 0) {
        console.error('No words found in stanza');
        return;
    }

    const text = Array.from(words).map(word => word.textContent.trim()).join(' ');
    const voiceSelect = document.getElementById('voiceSelect');

    if (!voiceSelect || !voiceSelect.value) {
        alert('Please select a voice before reading');
        return;
    }

    try {
        stanza.classList.add('enhanced-loading');

        console.log(`Generating speech for ${words.length} words in ${currentReadingMode} mode`);

        const speechResponse = await fetch('/read', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: voiceSelect.value,
                reading_mode: currentReadingMode
            })
        });

        stanza.classList.remove('enhanced-loading');

        const errorMessage = speechResponse.headers.get('X-Error');
        if (errorMessage) {
            console.error('Speech API Error:', errorMessage);
            alert(`Text-to-speech error: ${errorMessage}`);
            return;
        }

        if (!speechResponse.ok) {
            throw new Error(`Speech generation failed: ${speechResponse.status}`);
        }

        // Get timing information from headers
        const playbackRate = parseFloat(speechResponse.headers.get('X-Playback-Rate') || '1.0');
        const wordCount = parseInt(speechResponse.headers.get('X-Word-Count') || words.length);

        console.log(`Audio settings: playback=${playbackRate}, words=${wordCount}`);

        const audioBlob = await speechResponse.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);

        audio.playbackRate = playbackRate;
        currentAudio = audio;

        // Better sync: Wait for audio to actually start playing
        audio.addEventListener('loadeddata', function() {
            console.log('Audio loaded, duration:', audio.duration);
        });

        audio.addEventListener('playing', function() {
            console.log('Audio playing started - beginning SLOWER word highlighting');
            audioStartTime = Date.now();
            highlightStartTime = Date.now();
            startMuchSlowerWordHighlighting(words, audio.duration * 1000);
        });

        audio.addEventListener('ended', function() {
            console.log('Audio playback complete');
            cleanupAudioPlayback(stanza);
        });

        audio.addEventListener('error', function(e) {
            console.error('Audio error:', e);
            stanza.classList.remove('enhanced-loading');
            alert('Audio playback error. Please try again.');
        });

        // Start playback
        await audio.play();

    } catch (error) {
        console.error('Slower sync reading error:', error);
        stanza.classList.remove('enhanced-loading');
        alert(`Reading error: ${error.message || 'Could not play audio'}`);
    }
}

/**
 * MUCH SLOWER word highlighting - This is the key fix!
 */
function startMuchSlowerWordHighlighting(words, estimatedDuration) {
    console.log(`Starting MUCH SLOWER highlighting: ${words.length} words, ${estimatedDuration}ms duration`);

    isHighlighting = true;
    let currentWordIndex = 0;

    // Calculate timing per word with MUCH more conservative approach
    const totalWords = words.length;

    // MUCH SLOWER base timing
    let baseTimePerWord;
    if (currentReadingMode === 'learning') {
        // Learning mode: VERY slow - 1.8-2.5 seconds per word minimum
        baseTimePerWord = Math.max(1800, estimatedDuration / (totalWords * 0.5)); // Use only 50% of audio time
    } else {
        // Normal mode: Still much slower - 1.0-1.5 seconds per word minimum  
        baseTimePerWord = Math.max(1000, estimatedDuration / (totalWords * 0.7)); // Use only 70% of audio time
    }

    console.log(`MUCH SLOWER timing: ${Math.round(baseTimePerWord)}ms base per word (mode: ${currentReadingMode})`);

    function highlightNextWord() {
        if (!currentAudio || currentAudio.paused || currentAudio.ended || !isHighlighting) {
            console.log('Highlighting stopped - audio ended or paused');
            return;
        }

        // Clear previous highlights
        clearAllHighlights();

        if (currentWordIndex < words.length) {
            const wordElement = words[currentWordIndex];
            const wordType = wordElement.getAttribute('data-word-type') || 'regular-word';

            // Apply highlighting with word type
            wordElement.classList.add('highlight', `highlight-${wordType}`);

            if (currentReadingMode === 'learning') {
                wordElement.classList.add('learning-pulse');
                wordElement.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center', 
                    inline: 'nearest' 
                });
            }

            console.log(`Highlighted word ${currentWordIndex + 1}/${totalWords}: "${wordElement.textContent}" (${wordType})`);

            currentWordIndex++;

            // Calculate next word timing - MUCH SLOWER adjustments
            let nextWordDelay = baseTimePerWord;

            // Adjust for word length and complexity - but keep it very slow
            const wordLength = wordElement.textContent.length;
            if (wordLength > 8) {
                nextWordDelay *= 1.6; // Much longer for very long words
            } else if (wordLength > 5) {
                nextWordDelay *= 1.3; // Longer for medium words
            } else if (wordLength <= 3) {
                nextWordDelay *= 0.85; // Only slightly faster for short words
            }

            // Extra time for complex words in learning mode
            if (currentReadingMode === 'learning') {
                if (wordType === 'complex-word') {
                    nextWordDelay *= 1.8; // Much more time for complex words
                } else if (wordType === 'sight-word') {
                    nextWordDelay *= 0.9; // Slightly less for sight words
                }
            }

            // STRICT minimum timing constraints - never go too fast
            if (currentReadingMode === 'learning') {
                nextWordDelay = Math.max(1500, nextWordDelay); // Never faster than 1.5 seconds in learning
            } else {
                nextWordDelay = Math.max(800, nextWordDelay); // Never faster than 0.8 seconds in normal
            }

            console.log(`Next word in ${Math.round(nextWordDelay)}ms (${(nextWordDelay/1000).toFixed(1)}s)`);

            currentHighlightInterval = setTimeout(highlightNextWord, nextWordDelay);
        } else {
            console.log('Word highlighting complete');
            isHighlighting = false;
        }
    }

    // Start highlighting with longer initial delay to sync with audio
    const initialDelay = currentReadingMode === 'learning' ? 800 : 500;
    console.log(`Starting first word in ${initialDelay}ms`);
    currentHighlightInterval = setTimeout(highlightNextWord, initialDelay);
}

/**
 * Clear all highlighting
 */
function clearAllHighlights() {
    document.querySelectorAll('.word.highlight').forEach(word => {
        word.classList.remove('highlight', 'highlight-sight-word', 'highlight-phonics-word', 
                             'highlight-complex-word', 'highlight-regular-word', 'learning-pulse');
    });
}

/**
 * Enhanced audio cleanup
 */
function cleanupAudioPlayback(stanza) {
    currentAudio = null;
    audioStartTime = null;
    highlightStartTime = null;

    if (currentHighlightInterval) {
        clearTimeout(currentHighlightInterval);
        currentHighlightInterval = null;
    }

    setTimeout(clearAllHighlights, 200);

    if (stanza) {
        stanza.classList.remove('active', 'enhanced-loading');
    }

    isHighlighting = false;
    console.log('Audio cleanup complete');
}

// Export for debugging
window.ReaderDebug = {
    getCurrentMode: () => currentReadingMode,
    getHighlightingStatus: () => isHighlighting,
    clearHighlights: clearAllHighlights,
    switchMode: switchReadingMode
};