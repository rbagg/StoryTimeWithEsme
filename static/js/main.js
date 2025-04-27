/**
 * Main JavaScript for Esme's Story Generator
 * Handles core functionality for the application
 */

// Global variables
let currentTab = 'create';

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing main.js components');

    // Load saved preferences from localStorage if available
    loadUserPreferences();

    // Switch to the initial tab
    switchTab(currentTab);
});

/**
 * Switch between Create and Library tabs
 * @param {string} tab - Tab ID to switch to
 */
function switchTab(tab) {
    console.log(`Switching to tab: ${tab}`);
    currentTab = tab;

    // Update tab UI
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.remove('active');
    });

    const activeTab = document.getElementById(`${tab}Tab`);
    if (activeTab) {
        activeTab.classList.add('active');
    }

    // Show/hide containers
    document.getElementById('createContainer').style.display = tab === 'create' ? 'block' : 'none';
    document.getElementById('libraryContainer').style.display = tab === 'library' ? 'block' : 'none';

    // If library tab, load stories
    if (tab === 'library') {
        loadStoryLibrary();
    }

    // Save current tab to localStorage
    localStorage.setItem('currentTab', tab);
}

/**
 * Load user preferences from localStorage
 */
function loadUserPreferences() {
    // Load current tab
    const savedTab = localStorage.getItem('currentTab');
    if (savedTab) {
        currentTab = savedTab;
    }
}

/**
 * Load stories from the server for the library tab
 */
async function loadStoryLibrary() {
    try {
        const libraryContent = document.getElementById('libraryContent');
        if (!libraryContent) return;

        libraryContent.innerHTML = '<p>Loading stories...</p>';

        const response = await fetch('/get_stories');
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Clear the loading message
        libraryContent.innerHTML = '';

        if (data.stories.length === 0) {
            libraryContent.innerHTML = '<p>No stories in your library yet.</p>';
            return;
        }

        // Create a card for each story
        data.stories.forEach(story => {
            const card = document.createElement('div');
            card.className = 'story-card';

            const content = document.createElement('div');
            content.className = 'story-card-content';
            content.onclick = () => loadStory(story.id);

            const title = document.createElement('h3');
            title.textContent = story.title;

            const description = document.createElement('p');
            description.textContent = story.description;

            const date = document.createElement('p');
            date.className = 'date';
            date.textContent = new Date(story.created_at).toLocaleDateString();

            content.appendChild(title);
            content.appendChild(description);
            content.appendChild(date);

            const deleteButton = document.createElement('button');
            deleteButton.className = 'delete-button';
            deleteButton.textContent = 'Delete';
            deleteButton.onclick = (e) => deleteStory(e, story.id, card, libraryContent);

            card.appendChild(content);
            card.appendChild(deleteButton);
            libraryContent.appendChild(card);
        });

        console.log(`Loaded ${data.stories.length} stories`);
    } catch (error) {
        console.error('Error loading story library:', error);
        const libraryContent = document.getElementById('libraryContent');
        if (libraryContent) {
            libraryContent.innerHTML = `<p class="error">Error loading stories: ${error.message}</p>`;
        }
    }
}

/**
 * Load a specific story
 * @param {string} storyId - ID of the story to load
 */
async function loadStory(storyId) {
    try {
        // Redirect to the story view page
        window.location.href = `/view_story/${storyId}`;
    } catch (error) {
        console.error('Error loading story:', error);
        alert(`Error loading story: ${error.message}`);
    }
}

/**
 * Delete a story after confirmation
 * @param {Event} e - Event object
 * @param {string} storyId - ID of the story to delete
 * @param {Element} card - DOM element for the story card
 * @param {Element} container - DOM element for the library content container
 */
async function deleteStory(e, storyId, card, container) {
    e.stopPropagation(); // Prevent click from bubbling to parent

    if (!confirm('Are you sure you want to delete this story?')) {
        return;
    }

    try {
        const response = await fetch(`/delete_story/${storyId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }

        // Remove the card from the DOM
        card.remove();

        // If no more stories, show empty message
        if (container.children.length === 0) {
            container.innerHTML = '<p>No stories in your library yet.</p>';
        }
    } catch (error) {
        console.error('Error deleting story:', error);
        alert(`Error deleting story: ${error.message}`);
    }
}

/**
 * Show the save story modal dialog
 */
function showSaveStoryModal() {
    const modal = document.getElementById('saveStoryModal');
    if (modal) {
        modal.style.display = 'block';
        document.getElementById('storyTitle').focus();
    }
}

/**
 * Hide the save story modal dialog
 */
function hideSaveStoryModal() {
    const modal = document.getElementById('saveStoryModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Save the current story with the given title
 */
async function saveStoryWithTitle() {
    const titleInput = document.getElementById('storyTitle');
    const title = titleInput ? titleInput.value.trim() : '';

    if (!title) {
        alert('Please enter a title for your story');
        return;
    }

    try {
        const response = await fetch('/save_story', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ title })
        });

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        alert(`Story "${title}" saved successfully!`);
        hideSaveStoryModal();
    } catch (error) {
        console.error('Error saving story:', error);
        alert(`Error saving story: ${error.message}`);
    }
}

// Handle form submission
document.addEventListener('DOMContentLoaded', function() {
    const storyForm = document.querySelector('form[action="/generate"]');
    if (storyForm) {
        storyForm.addEventListener('submit', function() {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="loading-spinner"></span> Generating...';
            }
        });
    }
});

// Close modal when clicking outside the content
window.onclick = function(event) {
    const modal = document.getElementById('saveStoryModal');
    if (modal && event.target === modal) {
        hideSaveStoryModal();
    }
};