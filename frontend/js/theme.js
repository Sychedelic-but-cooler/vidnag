/**
 * Vidnag Theme Manager
 *
 * Handles light/dark mode and color theme switching with localStorage persistence
 */

const ThemeManager = {
    // Available themes
    THEMES: ['light', 'dark'],
    COLORS: ['blue', 'green', 'purple', 'red', 'orange', 'teal', 'pink'],

    // Storage keys
    THEME_KEY: 'vidnag_theme',
    COLOR_KEY: 'vidnag_color',

    /**
     * Initialize theme system
     * Load saved preferences or detect system preference
     */
    init() {
        // Load saved theme or detect system preference
        const savedTheme = localStorage.getItem(this.THEME_KEY);
        const savedColor = localStorage.getItem(this.COLOR_KEY);

        if (savedTheme && this.THEMES.includes(savedTheme)) {
            this.setTheme(savedTheme);
        } else {
            // Detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.setTheme(prefersDark ? 'dark' : 'light');
        }

        // Load saved color or use default
        if (savedColor && this.COLORS.includes(savedColor)) {
            this.setColor(savedColor);
        } else {
            this.setColor('blue');
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            // Only auto-switch if user hasn't manually set a preference
            if (!localStorage.getItem(this.THEME_KEY)) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        console.log('[Theme] Initialized:', this.getCurrentTheme(), this.getCurrentColor());
    },

    /**
     * Set light/dark theme
     */
    setTheme(theme) {
        if (!this.THEMES.includes(theme)) {
            console.error('[Theme] Invalid theme:', theme);
            return;
        }

        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(this.THEME_KEY, theme);

        // Dispatch event for other components to react
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme, color: this.getCurrentColor() }
        }));

        console.log('[Theme] Changed to:', theme);
    },

    /**
     * Set color theme
     */
    setColor(color) {
        if (!this.COLORS.includes(color)) {
            console.error('[Theme] Invalid color:', color);
            return;
        }

        document.documentElement.setAttribute('data-color', color);
        localStorage.setItem(this.COLOR_KEY, color);

        // Dispatch event
        window.dispatchEvent(new CustomEvent('colorchange', {
            detail: { theme: this.getCurrentTheme(), color }
        }));

        console.log('[Theme] Color changed to:', color);
    },

    /**
     * Toggle between light and dark
     */
    toggleTheme() {
        const current = this.getCurrentTheme();
        const next = current === 'light' ? 'dark' : 'light';
        this.setTheme(next);
    },

    /**
     * Get current theme
     */
    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || 'light';
    },

    /**
     * Get current color
     */
    getCurrentColor() {
        return document.documentElement.getAttribute('data-color') || 'blue';
    },

    /**
     * Reset to system defaults
     */
    reset() {
        localStorage.removeItem(this.THEME_KEY);
        localStorage.removeItem(this.COLOR_KEY);

        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        this.setTheme(prefersDark ? 'dark' : 'light');
        this.setColor('blue');

        console.log('[Theme] Reset to defaults');
    }
};

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
} else {
    ThemeManager.init();
}

// Export for use in other scripts
window.ThemeManager = ThemeManager;
