/**
 * Vidnag Main Application Controller
 * Handles tab switching, user state, and app initialization
 */

class VidnagApp {
    constructor() {
        this.currentTab = 'downloads';
        this.currentUser = null;
        this.activeDownloads = new Map();
        this.activeConversions = new Map();
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Initializing Vidnag App...');

        // Check authentication
        if (!API.getToken()) {
            window.location.href = '/login.html';
            return;
        }

        try {
            // Load user data
            await this.loadUserData();

            // Set up event listeners
            this.setupEventListeners();

            // Load initial tab content
            this.loadTabContent(this.currentTab);

            console.log('Vidnag App initialized successfully');
        } catch (error) {
            console.error('Failed to initialize app:', error);
            this.showError('Failed to load application. Please try refreshing the page.');
        }
    }

    /**
     * Load current user data
     */
    async loadUserData() {
        try {
            this.currentUser = await API.getCurrentUser();

            // Update UI with user data
            const usernameDisplay = document.getElementById('username-display');
            if (usernameDisplay) {
                usernameDisplay.textContent = this.currentUser.username;
            }

            // Show/hide admin button based on user role
            const adminBtn = document.getElementById('admin-btn');
            if (adminBtn) {
                adminBtn.style.display = this.currentUser.is_admin ? 'inline-flex' : 'none';
            }

            console.log('User data loaded:', this.currentUser);
        } catch (error) {
            console.error('Failed to load user data:', error);
            throw error;
        }
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Tab navigation
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                this.switchTab(tabId);
            });
        });

        // Header buttons
        const profileBtn = document.getElementById('profile-btn');
        if (profileBtn) {
            profileBtn.addEventListener('click', () => this.showProfile());
        }

        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettings());
        }

        const adminBtn = document.getElementById('admin-btn');
        if (adminBtn) {
            adminBtn.addEventListener('click', () => this.showAdmin());
        }

        const themeToggleBtn = document.getElementById('theme-toggle-btn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', () => {
                ThemeManager.toggleTheme();
            });
        }

        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Downloads tab events
        const downloadBtn = document.getElementById('download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.handleDownload());
        }

        // Tools tab events
        const toolSelector = document.getElementById('tool-selector');
        if (toolSelector) {
            toolSelector.addEventListener('change', (e) => this.handleToolChange(e.target.value));
        }

        // File browser events
        const chooseFilesBtn = document.getElementById('choose-files-btn');
        const fileInput = document.getElementById('file-input');
        if (chooseFilesBtn && fileInput) {
            chooseFilesBtn.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', (e) => this.handleFileUpload(e.target.files));
        }

        const uploadZone = document.getElementById('upload-zone');
        if (uploadZone) {
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.classList.add('drag-over');
            });

            uploadZone.addEventListener('dragleave', () => {
                uploadZone.classList.remove('drag-over');
            });

            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.classList.remove('drag-over');
                this.handleFileUpload(e.dataTransfer.files);
            });
        }

        // Search and filter handlers
        const historySearch = document.getElementById('history-search');
        if (historySearch) {
            historySearch.addEventListener('input', (e) => this.filterHistory(e.target.value));
        }

        const historyFilter = document.getElementById('history-filter');
        if (historyFilter) {
            historyFilter.addEventListener('change', (e) => this.filterHistoryByStatus(e.target.value));
        }

        const fileSearch = document.getElementById('file-search');
        if (fileSearch) {
            fileSearch.addEventListener('input', (e) => this.filterFiles(e.target.value));
        }
    }

    /**
     * Switch to a different tab
     */
    switchTab(tabId) {
        // Update button states
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            if (btn.dataset.tab === tabId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update content visibility
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            if (content.id === `tab-${tabId}`) {
                content.classList.add('active');
            } else {
                content.classList.remove('active');
            }
        });

        this.currentTab = tabId;
        this.loadTabContent(tabId);
    }

    /**
     * Load content for the active tab
     */
    async loadTabContent(tabId) {
        switch (tabId) {
            case 'downloads':
                await this.loadDownloads();
                break;
            case 'tools':
                await this.loadConversions();
                break;
            case 'browser':
                await this.loadFiles();
                break;
        }
    }

    /**
     * Load downloads data (placeholder)
     */
    async loadDownloads() {
        console.log('Loading downloads...');
        // TODO: Implement actual API call
        // For now, show empty state
        const historyContainer = document.getElementById('download-history');
        if (historyContainer) {
            historyContainer.innerHTML = '<p class="empty-state">No downloads yet</p>';
        }
    }

    /**
     * Load conversions data (placeholder)
     */
    async loadConversions() {
        console.log('Loading conversions...');
        // TODO: Implement actual API call
        const completedContainer = document.getElementById('completed-conversions');
        if (completedContainer) {
            completedContainer.innerHTML = '<p class="empty-state">No completed conversions</p>';
        }
    }

    /**
     * Load files data (placeholder)
     */
    async loadFiles() {
        console.log('Loading files...');
        // TODO: Implement actual API call
        const fileList = document.getElementById('file-list');
        if (fileList) {
            fileList.innerHTML = '<tr><td colspan="6" class="empty-state">No files yet</td></tr>';
        }
    }

    /**
     * Handle video download
     */
    async handleDownload() {
        const urlInput = document.getElementById('url-input');
        if (!urlInput) return;

        const urls = urlInput.value
            .split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0);

        if (urls.length === 0) {
            this.showError('Please enter at least one URL');
            return;
        }

        console.log('Starting downloads:', urls);
        this.showSuccess(`Added ${urls.length} download(s) to queue`);

        // TODO: Implement actual download logic
        // For now, just clear the input
        urlInput.value = '';
    }

    /**
     * Handle tool selection change
     */
    handleToolChange(tool) {
        console.log('Tool changed:', tool);
        const optionsContainer = document.getElementById('tool-options');
        if (!optionsContainer) return;

        // TODO: Load tool-specific options
        optionsContainer.innerHTML = `
            <div class="form-group">
                <label>Source File</label>
                <div class="file-selector">
                    <input type="text" class="glass-input" placeholder="Select a file..." readonly>
                    <button class="glass-btn">Browse</button>
                </div>
            </div>
            <div class="form-group">
                <label>Output Format</label>
                <select class="glass-select">
                    <option>MP4</option>
                    <option>WebM</option>
                    <option>AVI</option>
                </select>
            </div>
            <button class="glass-btn-primary">Process</button>
        `;
    }

    /**
     * Handle file upload
     */
    async handleFileUpload(files) {
        if (!files || files.length === 0) return;

        console.log('Uploading files:', files);
        this.showSuccess(`Uploading ${files.length} file(s)...`);

        // TODO: Implement actual upload logic with progress
    }

    /**
     * Filter download history
     */
    filterHistory(searchTerm) {
        console.log('Filtering history:', searchTerm);
        // TODO: Implement filtering
    }

    /**
     * Filter download history by status
     */
    filterHistoryByStatus(status) {
        console.log('Filtering by status:', status);
        // TODO: Implement filtering
    }

    /**
     * Filter files
     */
    filterFiles(searchTerm) {
        console.log('Filtering files:', searchTerm);
        // TODO: Implement filtering
    }

    /**
     * Show profile modal
     */
    showProfile() {
        console.log('Show profile');
        // TODO: Implement profile modal
        this.showInfo('Profile page coming soon!');
    }

    /**
     * Show settings modal
     */
    showSettings() {
        console.log('Show settings');
        // TODO: Implement settings modal
        this.showInfo('Settings page coming soon!');
    }

    /**
     * Show admin panel
     */
    showAdmin() {
        console.log('Show admin panel');
        // TODO: Implement admin panel
        window.location.href = '/admin.html';
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        if (!confirm('Are you sure you want to logout?')) {
            return;
        }

        try {
            await API.logout();
            window.location.href = '/login.html';
        } catch (error) {
            console.error('Logout failed:', error);
            // Clear token anyway and redirect
            API.clearToken();
            window.location.href = '/login.html';
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        console.log('SUCCESS:', message);
        // TODO: Implement toast notifications
        alert(message);
    }

    /**
     * Show error message
     */
    showError(message) {
        console.error('ERROR:', message);
        // TODO: Implement toast notifications
        alert(message);
    }

    /**
     * Show info message
     */
    showInfo(message) {
        console.log('INFO:', message);
        // TODO: Implement toast notifications
        alert(message);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new VidnagApp();
    window.app.init();
});
