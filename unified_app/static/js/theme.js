/**
 * Theme Management for Spine News Hub
 * Handles dark/light theme switching and persistence
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeThemeToggle();
});

/**
 * Initialize theme from localStorage or system preference
 */
function initializeTheme() {
    const html = document.documentElement;
    const savedTheme = localStorage.getItem('theme');
    
    if (savedTheme) {
        html.setAttribute('data-theme', savedTheme);
    } else {
        // Check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const theme = prefersDark ? 'dark' : 'light';
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }
}

/**
 * Initialize theme toggle button functionality
 */
function initializeThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        updateThemeIcon(); // Set initial icon state
    }
}

/**
 * Toggle between dark and light themes
 */
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Update theme
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update icon
    updateThemeIcon();
    
    // Add transition effect
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Remove transition after completion
    setTimeout(() => {
        document.body.style.transition = '';
    }, 300);
}

/**
 * Update theme toggle icon based on current theme
 */
function updateThemeIcon() {
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    
    if (themeToggle) {
        const themeIcon = themeToggle.querySelector('.theme-icon');
        if (themeIcon) {
            themeIcon.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
            themeIcon.setAttribute('title', 
                currentTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'
            );
        }
    }
}

/**
 * Get current theme
 * @returns {string} Current theme ('dark' or 'light')
 */
function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
}

/**
 * Set theme programmatically
 * @param {string} theme - 'dark' or 'light'
 */
function setTheme(theme) {
    if (theme === 'dark' || theme === 'light') {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        updateThemeIcon();
    }
}

/**
 * Listen for system theme changes
 */
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (!localStorage.getItem('theme')) {
        const theme = e.matches ? 'dark' : 'light';
        setTheme(theme);
    }
});

// Export functions for global access
window.themeUtils = {
    getCurrentTheme,
    setTheme,
    toggleTheme
};
