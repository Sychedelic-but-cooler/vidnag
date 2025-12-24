/**
 * Theme Switcher UI Component
 * Provides UI for switching themes and colors
 */

const ThemeSwitcherComponent = {
    /**
     * Create and inject the theme switcher UI
     */
    create() {
        const html = `
            <div class="theme-switcher">
                <button class="theme-toggle-btn" id="theme-toggle-btn" aria-label="Toggle theme menu">
                    🎨
                </button>

                <div class="theme-menu" id="theme-menu">
                    <h3>Mode</h3>
                    <div class="theme-options">
                        <button class="theme-option" data-theme="light">
                            ☀️ Light
                        </button>
                        <button class="theme-option" data-theme="dark">
                            🌙 Dark
                        </button>
                    </div>

                    <h3>Color</h3>
                    <div class="color-options">
                        <button class="color-option" data-color="blue" aria-label="Blue theme"></button>
                        <button class="color-option" data-color="green" aria-label="Green theme"></button>
                        <button class="color-option" data-color="purple" aria-label="Purple theme"></button>
                        <button class="color-option" data-color="red" aria-label="Red theme"></button>
                        <button class="color-option" data-color="orange" aria-label="Orange theme"></button>
                        <button class="color-option" data-color="teal" aria-label="Teal theme"></button>
                        <button class="color-option" data-color="pink" aria-label="Pink theme"></button>
                    </div>
                </div>
            </div>
        `;

        // Inject into body
        document.body.insertAdjacentHTML('beforeend', html);

        // Setup event listeners
        this.setupListeners();

        // Update active states
        this.updateActiveStates();

        console.log('[ThemeSwitcher] Component created');
    },

    /**
     * Setup event listeners
     */
    setupListeners() {
        const toggleBtn = document.getElementById('theme-toggle-btn');
        const menu = document.getElementById('theme-menu');

        // Toggle menu
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            menu.classList.toggle('show');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!menu.contains(e.target) && e.target !== toggleBtn) {
                menu.classList.remove('show');
            }
        });

        // Theme option buttons
        document.querySelectorAll('.theme-option').forEach(btn => {
            btn.addEventListener('click', () => {
                const theme = btn.dataset.theme;
                ThemeManager.setTheme(theme);
                this.updateActiveStates();
            });
        });

        // Color option buttons
        document.querySelectorAll('.color-option').forEach(btn => {
            btn.addEventListener('click', () => {
                const color = btn.dataset.color;
                ThemeManager.setColor(color);
                this.updateActiveStates();
            });
        });

        // Listen for theme changes from other sources
        window.addEventListener('themechange', () => {
            this.updateActiveStates();
        });

        window.addEventListener('colorchange', () => {
            this.updateActiveStates();
        });
    },

    /**
     * Update active states of buttons
     */
    updateActiveStates() {
        const currentTheme = ThemeManager.getCurrentTheme();
        const currentColor = ThemeManager.getCurrentColor();

        // Update theme buttons
        document.querySelectorAll('.theme-option').forEach(btn => {
            if (btn.dataset.theme === currentTheme) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update color buttons
        document.querySelectorAll('.color-option').forEach(btn => {
            if (btn.dataset.color === currentColor) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    },

    /**
     * Initialize the component
     */
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.create());
        } else {
            this.create();
        }
    }
};

// Auto-initialize
ThemeSwitcherComponent.init();

// Export for use in other scripts
window.ThemeSwitcherComponent = ThemeSwitcherComponent;
