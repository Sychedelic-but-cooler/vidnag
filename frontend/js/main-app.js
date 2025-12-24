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
        this.pollInterval = null;
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
     * Load downloads data
     */
    async loadDownloads() {
        console.log('Loading downloads...');

        try {
            // Load video history
            const response = await API.getVideos({ source_type: 'download', page: 1, per_page: 20 });

            const historyContainer = document.getElementById('download-history');
            if (!historyContainer) return;

            if (response.videos && response.videos.length > 0) {
                historyContainer.innerHTML = response.videos.map(video => this.renderVideoHistoryItem(video)).join('');
            } else {
                historyContainer.innerHTML = '<p class="empty-state">No downloads yet</p>';
            }

            // Update active downloads display
            await this.updateActiveDownloads();
        } catch (error) {
            console.error('Failed to load downloads:', error);
        }
    }

    /**
     * Render a video history item
     */
    renderVideoHistoryItem(video) {
        const statusClass = video.status === 'ready' ? 'completed' :
                          video.status === 'error' ? 'failed' :
                          video.status === 'processing' ? 'processing' : 'cancelled';

        const statusText = video.status === 'ready' ? '✓ Completed' :
                          video.status === 'error' ? '✗ Failed' :
                          video.status === 'processing' ? '⟳ Processing' : '✗ Cancelled';

        return `
            <div class="history-item">
                <div class="history-item-thumbnail">
                    📹
                </div>
                <div class="history-item-info">
                    <div class="history-item-title">${this.escapeHtml(video.title)}</div>
                    <div class="history-item-meta">
                        <span class="history-item-status ${statusClass}">${statusText}</span>
                        ${video.file_size > 0 ? `<span>${this.formatFileSize(video.file_size)}</span>` : ''}
                        ${video.duration ? `<span>${this.formatDuration(video.duration)}</span>` : ''}
                        ${video.created_at ? `<span>${this.formatDate(video.created_at)}</span>` : ''}
                    </div>
                    ${video.error_message ? `<div class="error-text">${this.escapeHtml(video.error_message)}</div>` : ''}
                </div>
                <div class="history-item-actions">
                    ${video.status === 'ready' ? `<button class="glass-btn-small" onclick="app.downloadFile(${video.id})">Download</button>` : ''}
                    <button class="glass-btn-small" onclick="app.deleteVideo(${video.id})">Delete</button>
                </div>
            </div>
        `;
    }

    /**
     * Update active downloads display
     */
    async updateActiveDownloads() {
        const activeContainer = document.getElementById('active-downloads');
        if (!activeContainer) return;

        const activeJobs = Array.from(this.activeDownloads.values());

        if (activeJobs.length === 0) {
            activeContainer.innerHTML = '<p class="empty-state">No active downloads</p>';
            return;
        }

        // Fetch status for each active job
        const jobStatuses = await Promise.all(
            activeJobs.map(job => API.getDownloadStatus(job.job_id).catch(e => null))
        );

        const html = jobStatuses
            .filter(status => status && (status.status === 'running' || status.status === 'pending'))
            .map(status => this.renderActiveDownload(status))
            .join('');

        activeContainer.innerHTML = html || '<p class="empty-state">No active downloads</p>';

        // Remove completed/failed jobs from tracking
        jobStatuses.forEach(status => {
            if (status && (status.status === 'completed' || status.status === 'failed')) {
                this.activeDownloads.delete(status.job_id);
            }
        });
    }

    /**
     * Render an active download item
     */
    renderActiveDownload(jobStatus) {
        return `
            <div class="download-item">
                <div class="download-item-header">
                    <div class="download-item-title">${jobStatus.current_step || 'Processing...'}</div>
                    <button class="download-item-cancel" onclick="app.cancelDownload(${jobStatus.job_id})">Cancel</button>
                </div>
                <div class="download-progress">
                    <div class="download-progress-bar">
                        <div class="download-progress-fill" style="width: ${jobStatus.progress || 0}%"></div>
                    </div>
                </div>
                <div class="download-item-info">
                    <span>${Math.round(jobStatus.progress || 0)}%</span>
                    <span>${jobStatus.video?.title || 'Downloading...'}</span>
                </div>
            </div>
        `;
    }

    /**
     * Start polling for download status updates
     */
    startDownloadPolling() {
        // Clear existing interval
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        // Poll every 2 seconds
        this.pollInterval = setInterval(async () => {
            if (this.activeDownloads.size > 0) {
                await this.updateActiveDownloads();
            } else {
                // Stop polling if no active downloads
                clearInterval(this.pollInterval);
                this.pollInterval = null;
            }
        }, 2000);
    }

    /**
     * Cancel a download
     */
    async cancelDownload(jobId) {
        if (!confirm('Cancel this download?')) return;

        try {
            await API.cancelJob(jobId);
            this.activeDownloads.delete(jobId);
            await this.updateActiveDownloads();
            this.showSuccess('Download cancelled');
        } catch (error) {
            console.error('Failed to cancel download:', error);
            this.showError('Failed to cancel download');
        }
    }

    /**
     * Delete a video
     */
    async deleteVideo(videoId) {
        if (!confirm('Delete this video?')) return;

        try {
            await API.deleteVideo(videoId);
            await this.loadDownloads();
            this.showSuccess('Video deleted');
        } catch (error) {
            console.error('Failed to delete video:', error);
            this.showError('Failed to delete video');
        }
    }

    /**
     * Download a file
     */
    downloadFile(videoId) {
        // TODO: Implement file download
        window.open(`/api/videos/${videoId}/download`, '_blank');
    }

    /**
     * Helper: Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Helper: Format duration
     */
    formatDuration(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    /**
     * Helper: Format date
     */
    formatDate(isoString) {
        const date = new Date(isoString);
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return 'Today';
        if (days === 1) return 'Yesterday';
        if (days < 7) return `${days} days ago`;
        return date.toLocaleDateString();
    }

    /**
     * Helper: Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

        // Submit each URL
        let successCount = 0;
        let errorCount = 0;

        for (const url of urls) {
            try {
                const result = await API.downloadVideo(url);
                console.log('Download submitted:', result);

                // Add to active downloads tracking
                this.activeDownloads.set(result.job_id, {
                    job_id: result.job_id,
                    video_id: result.video_id,
                    url: url,
                    status: result.status
                });

                successCount++;
            } catch (error) {
                console.error('Failed to submit download:', error);
                errorCount++;
                this.showError(`Failed to download: ${url}\n${error.message}`);
            }
        }

        // Clear input on success
        if (successCount > 0) {
            urlInput.value = '';
            this.showSuccess(`Added ${successCount} download(s) to queue`);

            // Refresh the downloads view
            await this.loadDownloads();

            // Start polling for status updates
            this.startDownloadPolling();
        }

        if (errorCount > 0 && successCount === 0) {
            this.showError(`Failed to add ${errorCount} download(s)`);
        }
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
