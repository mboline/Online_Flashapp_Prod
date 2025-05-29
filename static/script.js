document.addEventListener('DOMContentLoaded', function () {
    // Handle the start session button on the index page
    const startSessionButton = document.getElementById('start-session');
    if (startSessionButton) {
        startSessionButton.addEventListener('click', function () {
            const selectedPhonograms = Array.from(document.querySelectorAll('input[name="phonograms"]:checked'))
                .map(cb => cb.value);
            const randomize = document.getElementById('randomize').checked;

            // Debug logs in console only, no alerts
            console.log('Selected Phonograms:', selectedPhonograms);
            console.log('Randomize:', randomize);

            if (selectedPhonograms.length === 0) {
                alert('Please select at least one phonogram to start the session.');
                return;
            }

            fetch('/start-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_phonograms: selectedPhonograms, randomize: randomize })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Session Data:', data);
                
                if (data.success) {
                    // No alert - directly redirect to the session page
                    window.location.href = data.redirect || '/session';
                } else if (data.error) {
                    throw new Error(data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while starting the session. Please try again.');
            });
        });
    }

    // Handle session page functionality
    if (window.location.pathname.includes('/session')) {
        // Get all phonogram cards
        const phonogramCards = document.querySelectorAll('.phonogram-card');
        if (phonogramCards.length > 0) {
            // Initialize: hide all cards except the first
            let currentCardIndex = 0;
            updateDisplay();
            
            // Add event listeners for navigation buttons
            const nextButton = document.getElementById('next');
            if (nextButton) {
                nextButton.addEventListener('click', function() {
                    currentCardIndex = (currentCardIndex + 1) % phonogramCards.length;
                    updateDisplay();
                });
            }
            
            const prevButton = document.getElementById('previous');
            if (prevButton) {
                prevButton.addEventListener('click', function() {
                    currentCardIndex = (currentCardIndex - 1 + phonogramCards.length) % phonogramCards.length;
                    updateDisplay();
                });
            }
            
            function updateDisplay() {
                // Hide all cards
                phonogramCards.forEach(card => card.style.display = 'none');
                // Show current card
                phonogramCards[currentCardIndex].style.display = 'block';
                
                // Update counter
                const counter = document.getElementById('card-counter');
                if (counter) {
                    counter.textContent = `Card ${currentCardIndex + 1} of ${phonogramCards.length}`;
                }
            }
        }
    }
    
    // Handle the "Select All Phonograms" checkbox
    const selectAllCheckbox = document.getElementById('select-all');
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('input[name="phonograms"]');
            checkboxes.forEach(cb => cb.checked = this.checked);
        });
    }

    // Handle the "Select All" checkbox for each lesson
    const selectLessonCheckboxes = document.querySelectorAll('.select-lesson');
    if (selectLessonCheckboxes.length > 0) {
        selectLessonCheckboxes.forEach(lessonCheckbox => {
            lessonCheckbox.addEventListener('change', function() {
                const lesson = this.dataset.lesson;
                const lessonDiv = this.closest('.lesson');
                if (lessonDiv) {
                    const checkboxes = lessonDiv.querySelectorAll('input[name="phonograms"]');
                    checkboxes.forEach(cb => cb.checked = this.checked);
                }
            });
        });
    }
});
