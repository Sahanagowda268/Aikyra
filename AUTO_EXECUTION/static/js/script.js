// JavaScript for additional interactivity
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Chatbot auto-scroll
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // Theme toggle functionality
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            fetch('/toggle_theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.dark_mode) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                } else {
                    document.documentElement.setAttribute('data-theme', 'light');
                    themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                }
                // Force a reload to update the page with new theme
                location.reload();
            })
            .catch(error => console.error('Error:', error));
        });
    }
    
    // Voice input functionality
    const voiceInputBtn = document.createElement('button');
    voiceInputBtn.innerHTML = '<i class="fas fa-microphone"></i>';
    voiceInputBtn.className = 'btn btn-outline-secondary ms-2';
    voiceInputBtn.type = 'button';
    voiceInputBtn.id = 'voiceInputBtn';
    
    const messageInput = document.querySelector('input[name="message"]');
    if (messageInput) {
        messageInput.parentNode.appendChild(voiceInputBtn);
        
        voiceInputBtn.addEventListener('click', function() {
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                const recognition = new SpeechRecognition();
                recognition.continuous = false;
                recognition.interimResults = false;
                
                recognition.start();
                
                recognition.onresult = function(event) {
                    const transcript = event.results[0][0].transcript;
                    messageInput.value = transcript;
                    recognition.stop();
                };
                
                recognition.onerror = function(event) {
                    console.error('Speech recognition error', event.error);
                    recognition.stop();
                };
            } else {
                alert('Speech recognition not supported in this browser.');
            }
        });
    }
    
    // Auto-generate email body
    const generateBodyBtn = document.querySelector('#generateBodyBtn');
    const subjectInput = document.querySelector('input[name="subject"]');
    const bodyTextarea = document.querySelector('textarea[name="body"]');
    
    if (generateBodyBtn && subjectInput && bodyTextarea) {
        generateBodyBtn.addEventListener('click', function() {
            const subject = subjectInput.value;
            if (subject) {
                // Show loading indicator
                bodyTextarea.value = "Generating email content...";
                
                // Submit the form to generate content
                const form = document.querySelector('form');
                const generateInput = document.createElement('input');
                generateInput.type = 'hidden';
                generateInput.name = 'generate_body';
                generateInput.value = 'true';
                form.appendChild(generateInput);
                form.submit();
            } else {
                alert('Please enter a subject first.');
            }
        });
    }
    
    // Code syntax highlighting (simplified)
    const codeBlocks = document.querySelectorAll('pre code');
    codeBlocks.forEach(function(block) {
        // Simple syntax highlighting
        const code = block.textContent;
        // This would be replaced with a proper syntax highlighter like Prism.js in a real application
        block.innerHTML = code.replace(/(function|var|let|const|if|else|for|while|return)/g, '<span class="keyword">$1</span>');
    });
    
    // Animation for feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    featureCards.forEach(function(card, index) {
        card.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Floating animation for elements
    const floatElements = document.querySelectorAll('.float-up');
    floatElements.forEach(function(element, index) {
        element.style.animationDelay = `${index * 0.1}s`;
    });
    
    // Background animation
    const bubbles = document.querySelectorAll('.bubble');
    bubbles.forEach(function(bubble, index) {
        bubble.style.animationDelay = `${index * 2}s`;
    });
});
// Add these functions to your existing script.js

// Auto-scroll to bottom of chat
function scrollToBottom() {
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Simulate typing indicator
function showTypingIndicator() {
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        const typingIndicator = `
            <div class="message-bot d-flex mb-3 typing-indicator-container">
                <img src="${window.location.origin}/static/images/ai-bot.png" 
                     class="rounded-circle me-2" width="32" height="32" 
                     onerror="this.src='https://ui-avatars.com/api/?name=AI+Assistant&background=36b9cc&color=fff'"
                     alt="AI Assistant">
                <div>
                    <div class="message-content bg-light p-2 rounded typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', typingIndicator);
        scrollToBottom();
    }
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.querySelector('.typing-indicator-container');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Format message timestamps
function formatMessageTimestamps() {
    const timestamps = document.querySelectorAll('.message-timestamp');
    timestamps.forEach(timestamp => {
        const time = new Date(timestamp.textContent);
        if (!isNaN(time)) {
            timestamp.textContent = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    });
}

// Initialize chat functionality
function initChat() {
    scrollToBottom();
    formatMessageTimestamps();
    
    // Add event listener for form submission
    const chatForm = document.querySelector('.chat-input form');
    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            const messageInput = this.querySelector('input[name="message"]');
            if (messageInput && messageInput.value.trim() !== '') {
                showTypingIndicator();
                
                // Simulate AI response delay
                setTimeout(() => {
                    removeTypingIndicator();
                }, 1000);
            }
        });
    }
}

// Call initChat when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Your existing code...
    
    // Initialize chat
    initChat();
    
    // Auto-scroll when new messages are added
    const observer = new MutationObserver(scrollToBottom);
    const chatMessages = document.querySelector('.chat-messages');
    if (chatMessages) {
        observer.observe(chatMessages, { childList: true, subtree: true });
    }
});