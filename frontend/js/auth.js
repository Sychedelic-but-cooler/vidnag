/**
 * Vidnag Authentication
 *
 * JWT tokens stored in localStorage:
 * - access_token: Short-lived token for API calls
 * - refresh_token: Long-lived token for refreshing access token
 *
 * ALL validation happens server-side!
 */

const API_BASE = '/api/auth';

// Storage keys
const ACCESS_TOKEN_KEY = 'vidnag_access_token';
const REFRESH_TOKEN_KEY = 'vidnag_refresh_token';

// DOM elements
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const toggleLink = document.getElementById('toggle-link');
const toggleMessage = document.getElementById('toggle-message');
const errorMessage = document.getElementById('error-message');
const successMessage = document.getElementById('success-message');
const userInfo = document.getElementById('user-info');
const authBox = document.querySelector('.auth-box');

// === Token Management ===

function saveTokens(accessToken, refreshToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

function clearTokens() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function hasToken() {
    return !!getAccessToken();
}

// === API Calls ===

async function apiCall(endpoint, method = 'GET', body = null, requiresAuth = false) {
    const headers = {
        'Content-Type': 'application/json'
    };

    // Add auth header if required
    if (requiresAuth) {
        const token = getAccessToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }

    const options = {
        method,
        headers
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(endpoint, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
    }

    return data;
}

// === Auth Functions ===

async function register(username, email, password) {
    const data = await apiCall(`${API_BASE}/register`, 'POST', {
        username,
        email,
        password
    });

    // Save tokens (only storage on client side!)
    saveTokens(data.access_token, data.refresh_token);

    return data.user;
}

async function login(username, password) {
    const data = await apiCall(`${API_BASE}/login`, 'POST', {
        username,
        password
    });

    // Save tokens
    saveTokens(data.access_token, data.refresh_token);

    return data.user;
}

async function logout() {
    try {
        await apiCall(`${API_BASE}/logout`, 'POST', null, true);
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Always clear local tokens
        clearTokens();
    }
}

async function logoutAll() {
    try {
        await apiCall(`${API_BASE}/logout-all`, 'POST', null, true);
    } catch (error) {
        console.error('Logout all error:', error);
    } finally {
        clearTokens();
    }
}

async function getCurrentUser() {
    return await apiCall(`${API_BASE}/me`, 'GET', null, true);
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        throw new Error('No refresh token');
    }

    const data = await apiCall(`${API_BASE}/refresh`, 'POST', {
        refresh_token: refreshToken
    });

    // Save new tokens
    saveTokens(data.access_token, data.refresh_token);

    return data.user;
}

// === UI Functions ===

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    successMessage.style.display = 'none';
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    errorMessage.style.display = 'none';
}

function hideMessages() {
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';
}

function showUserInfo(user) {
    // Hide auth forms
    authBox.style.display = 'none';

    // Populate user info
    document.getElementById('username').textContent = user.username;
    document.getElementById('user-email').textContent = user.email;
    document.getElementById('user-admin').textContent = user.is_admin ? 'Yes' : 'No';
    document.getElementById('storage-used').textContent = formatBytes(user.storage_used);
    document.getElementById('storage-quota').textContent = formatBytes(user.storage_quota);

    // Show user info
    userInfo.style.display = 'block';
}

function showAuthForms() {
    userInfo.style.display = 'none';
    authBox.style.display = 'block';
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function toggleForms() {
    if (loginForm.style.display === 'none') {
        // Show login
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        toggleMessage.textContent = "Don't have an account?";
        toggleLink.textContent = 'Register';
    } else {
        // Show register
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        toggleMessage.textContent = 'Already have an account?';
        toggleLink.textContent = 'Login';
    }
    hideMessages();
}

// === Event Handlers ===

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const user = await login(username, password);
        showSuccess('Login successful!');
        setTimeout(() => showUserInfo(user), 500);
    } catch (error) {
        showError(error.message);
    }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessages();

    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const user = await register(username, email, password);
        showSuccess('Registration successful!');
        setTimeout(() => showUserInfo(user), 500);
    } catch (error) {
        showError(error.message);
    }
});

toggleLink.addEventListener('click', (e) => {
    e.preventDefault();
    toggleForms();
});

document.getElementById('logout-btn').addEventListener('click', async () => {
    await logout();
    showAuthForms();
    showSuccess('Logged out successfully');
});

document.getElementById('logout-all-btn').addEventListener('click', async () => {
    if (confirm('This will log you out from all devices. Continue?')) {
        await logoutAll();
        showAuthForms();
        showSuccess('Logged out from all devices');
    }
});

// === Initialization ===

async function init() {
    // Check if user is already logged in
    if (hasToken()) {
        try {
            const user = await getCurrentUser();
            showUserInfo(user);
        } catch (error) {
            // Token expired or invalid, try refresh
            try {
                const user = await refreshAccessToken();
                showUserInfo(user);
            } catch (refreshError) {
                // Refresh failed, clear tokens and show login
                clearTokens();
                showAuthForms();
            }
        }
    } else {
        showAuthForms();
    }
}

// Initialize on page load
init();
