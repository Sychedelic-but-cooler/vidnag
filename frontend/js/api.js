/**
 * Vidnag API Client
 * Handles all API communication with the backend
 */

const API = {
    baseURL: '/api',

    /**
     * Get authentication token from localStorage
     */
    getToken() {
        return localStorage.getItem('vidnag_access_token');
    },

    /**
     * Set authentication token in localStorage
     */
    setToken(token) {
        localStorage.setItem('vidnag_access_token', token);
    },

    /**
     * Remove authentication token
     */
    clearToken() {
        localStorage.removeItem('vidnag_access_token');
        localStorage.removeItem('vidnag_refresh_token');
    },

    /**
     * Make authenticated API request
     */
    async request(endpoint, options = {}) {
        const token = this.getToken();

        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add authorization header if token exists
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);

            // Handle 401 Unauthorized - redirect to login
            if (response.status === 401) {
                this.clearToken();
                window.location.href = '/login.html';
                return null;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    /**
     * GET request
     */
    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    /**
     * POST request
     */
    async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT request
     */
    async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // ========================================
    // AUTH ENDPOINTS
    // ========================================

    /**
     * Get current user info
     */
    async getCurrentUser() {
        return this.get('/auth/me');
    },

    /**
     * Logout
     */
    async logout() {
        const result = await this.post('/auth/logout');
        this.clearToken();
        return result;
    },

    /**
     * Logout from all devices
     */
    async logoutAll() {
        const result = await this.post('/auth/logout-all');
        this.clearToken();
        return result;
    },

    // ========================================
    // VIDEO ENDPOINTS (Placeholder)
    // ========================================

    /**
     * Get user's videos
     */
    async getVideos(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/videos${query ? '?' + query : ''}`);
    },

    /**
     * Download video from URL
     */
    async downloadVideo(url, title = null, visibility = 'private') {
        return this.post('/videos/download', { url, title, visibility });
    },

    /**
     * Get download job status
     */
    async getDownloadStatus(jobId) {
        return this.get(`/videos/download/${jobId}`);
    },

    /**
     * Get video by ID
     */
    async getVideo(videoId) {
        return this.get(`/videos/${videoId}`);
    },

    /**
     * Delete video
     */
    async deleteVideo(videoId) {
        return this.delete(`/videos/${videoId}`);
    },

    // ========================================
    // PROCESSING ENDPOINTS (Placeholder)
    // ========================================

    /**
     * Get processing jobs
     */
    async getJobs(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/jobs${query ? '?' + query : ''}`);
    },

    /**
     * Create processing job
     */
    async createJob(jobData) {
        return this.post('/jobs', jobData);
    },

    /**
     * Get job by ID
     */
    async getJob(jobId) {
        return this.get(`/jobs/${jobId}`);
    },

    /**
     * Cancel job
     */
    async cancelJob(jobId) {
        return this.post(`/jobs/${jobId}/cancel`);
    },

    // ========================================
    // FILE ENDPOINTS (Placeholder)
    // ========================================

    /**
     * Get user's files
     */
    async getFiles(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/files${query ? '?' + query : ''}`);
    },

    /**
     * Upload file
     */
    async uploadFile(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        const token = this.getToken();

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    resolve(JSON.parse(xhr.responseText));
                } else if (xhr.status === 401) {
                    this.clearToken();
                    window.location.href = '/login.html';
                } else {
                    reject(new Error('Upload failed'));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', `${this.baseURL}/files/upload`);
            if (token) {
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            }

            xhr.send(formData);
        });
    },

    /**
     * Delete file
     */
    async deleteFile(fileId) {
        return this.delete(`/files/${fileId}`);
    }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
