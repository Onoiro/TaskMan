/**
 * Theme Toggle for TaskMan
 * Handles light/dark/auto theme switching with localStorage persistence
 */

(function() {
    'use strict';

    /**
     * Get the preferred theme from localStorage or system preference
     * @returns {string} 'light', 'dark', or 'auto'
     */
    function getPreferredTheme() {
        const stored = localStorage.getItem('theme');
        if (stored) {
            return stored;
        }
        return 'auto';
    }

    /**
     * Get the effective theme (resolves 'auto' to actual theme)
     * @param {string} theme - 'light', 'dark', or 'auto'
     * @returns {string} 'light' or 'dark'
     */
    function getEffectiveTheme(theme) {
        if (theme === 'auto') {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return theme;
    }

    /**
     * Set the theme on the document
     * @param {string} theme - 'light', 'dark', or 'auto'
     * @param {boolean} animate - whether to animate the transition
     */
    function setTheme(theme, animate) {
        const effectiveTheme = getEffectiveTheme(theme);

        if (animate) {
            document.documentElement.classList.add('theme-transition');
        }

        document.documentElement.setAttribute('data-bs-theme', effectiveTheme);
        localStorage.setItem('theme', theme);
        updateToggleIcon(theme);
        updateActiveButtons(theme);

        if (animate) {
            setTimeout(function() {
                document.documentElement.classList.remove('theme-transition');
            }, 350);
        }
    }

    /**
     * Update the toggle button icon based on current theme
     * @param {string} theme - Current theme value
     */
    function updateToggleIcon(theme) {
        const iconMap = {
            'light': 'bi-sun-fill',
            'dark': 'bi-moon-fill',
            'auto': 'bi-circle-half'
        };
        
        // Update icons in all theme switcher buttons
        document.querySelectorAll('[data-theme-value]').forEach(button => {
            const buttonTheme = button.getAttribute('data-theme-value');
            const icon = button.querySelector('i');
            if (icon && iconMap[buttonTheme]) {
                // Remove all theme icons
                icon.classList.remove('bi-sun-fill', 'bi-moon-fill', 'bi-circle-half');
                // Add current theme icon
                icon.classList.add(iconMap[buttonTheme]);
            }
        });
    }

    /**
     * Update active state of theme toggle buttons
     * @param {string} theme - Current theme value
     */
    function updateActiveButtons(theme) {
        document.querySelectorAll('[data-theme-value]').forEach(button => {
            const buttonTheme = button.getAttribute('data-theme-value');
            if (buttonTheme === theme) {
                button.classList.remove('btn-outline-secondary');
                button.classList.add('btn-primary');
            } else {
                button.classList.remove('btn-primary');
                button.classList.add('btn-outline-secondary');
            }
        });
    }

    /**
     * Handle system theme change
     */
    function handleSystemThemeChange() {
        const storedTheme = localStorage.getItem('theme');
        // Only auto-update if theme is 'auto' or not set
        if (!storedTheme || storedTheme === 'auto') {
            const effectiveTheme = getEffectiveTheme('auto');
            document.documentElement.setAttribute('data-bs-theme', effectiveTheme);
        }
    }

    // Initialize on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function() {
        const preferredTheme = getPreferredTheme();
        
        // Apply the theme
        setTheme(preferredTheme, false);

        // Add click handlers to all theme toggle buttons
        document.querySelectorAll('[data-theme-value]').forEach(function(button) {
            button.addEventListener('click', function() {
                var theme = this.getAttribute('data-theme-value');
                setTheme(theme, true);
            });
        });

        // Listen for system theme changes
        var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', handleSystemThemeChange);
    });

    // Expose functions for global access if needed
    window.themeToggle = {
        getPreferredTheme: getPreferredTheme,
        setTheme: setTheme,
        getEffectiveTheme: getEffectiveTheme
    };
})();
