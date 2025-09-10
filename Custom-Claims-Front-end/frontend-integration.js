// frontend-integration.js
// Custom Claims Provider Integration Library for Microsoft Entra

class CustomClaimsIntegration {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.authUrl = "https://login.microsoftonline.com/b8e62cd3-6661-4faa-91f3-ffe016db96e8/oauth2/v2.0/authorize";
        this.clientId = "813cd2eb-5858-4f25-b0bc-c13602fc6e7f";
        this.redirectUri = "http://localhost:3000/auth/callback";
    }

    // Main method to start authentication with custom claims
    async authenticateWithCustomClaims(userEmail, frontendData) {
        try {
            console.log('Starting authentication with custom claims...');
            
            // 1. Store frontend data in backend
            const success = await this.storeFrontendData(userEmail, frontendData);
            
            if (success) {
                // 2. Redirect to Entra for authentication
                this.redirectToAuth();
            } else {
                throw new Error('Failed to store frontend data');
            }
            
        } catch (error) {
            console.error('Error in authentication process:', error);
            alert('Error starting authentication. Please try again.');
        }
    }

    // Store frontend data in backend before authentication
    async storeFrontendData(userEmail, frontendData) {
        try {
            const payload = {
                user_id: userEmail,
                business_unit: frontendData.businessUnit || 'Unknown',
                device_info: this.getDeviceInfo(),
                custom_data: frontendData.customData || '',
                timestamp: Date.now() / 1000
            };

            console.log('Sending frontend data:', payload);

            const response = await fetch(`${this.apiBaseUrl}/api/store-frontend-data`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('Frontend data stored successfully:', result);
            return true;

        } catch (error) {
            console.error('❌ Error storing frontend data:', error);
            return false;
        }
    }

    // Get device and browser information
    getDeviceInfo() {
        const userAgent = navigator.userAgent;
        let deviceInfo = 'Unknown';

        // Detect browser
        if (userAgent.includes('Chrome')) {
            deviceInfo = 'Chrome';
        } else if (userAgent.includes('Firefox')) {
            deviceInfo = 'Firefox';
        } else if (userAgent.includes('Safari')) {
            deviceInfo = 'Safari';
        } else if (userAgent.includes('Edge')) {
            deviceInfo = 'Edge';
        }

        // Detect operating system
        if (userAgent.includes('Windows')) {
            deviceInfo += '-Windows';
        } else if (userAgent.includes('Mac')) {
            deviceInfo += '-macOS';
        } else if (userAgent.includes('Linux')) {
            deviceInfo += '-Linux';
        }

        return deviceInfo;
    }

    // Redirect to Microsoft Entra for authentication
    redirectToAuth() {
        const state = this.generateState();
        const nonce = this.generateNonce();

        const authUrlWithParams = new URL(this.authUrl);
        authUrlWithParams.searchParams.set('client_id', this.clientId);
        authUrlWithParams.searchParams.set('response_type', 'id_token');
        authUrlWithParams.searchParams.set('redirect_uri', this.redirectUri);
        authUrlWithParams.searchParams.set('response_mode', 'fragment');
        authUrlWithParams.searchParams.set('scope', 'openid profile email');
        authUrlWithParams.searchParams.set('state', state);
        authUrlWithParams.searchParams.set('nonce', nonce);

        console.log('🔄 Redirecting to:', authUrlWithParams.toString());
        window.location.href = authUrlWithParams.toString();
    }

    // Generate unique state for security
    generateState() {
        return Math.random().toString(36).substring(2, 15) + 
               Math.random().toString(36).substring(2, 15);
    }

    // Generate unique nonce for security
    generateNonce() {
        return Math.random().toString(36).substring(2, 15) + 
               Date.now().toString();
    }

    // Test connection to the API
    async testConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            console.log('API Health Check:', data);
            return true;
        } catch (error) {
            console.error('API Connection Error:', error);
            return false;
        }
    }

    // Debug: View stored data in backend
    async viewStoredData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/debug/stored-data`);
            const data = await response.json();
            console.log('Stored data:', data);
            return data;
        } catch (error) {
            console.error('Error fetching stored data:', error);
            return null;
        }
    }
}

// Authentication Demo Class - Example implementation
class AuthenticationDemo {
    constructor() {
        this.claimsIntegration = new CustomClaimsIntegration();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Authentication form submission
        const form = document.getElementById('auth-form');
        if (form) {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        }

        // Test connection button
        const testBtn = document.getElementById('test-connection');
        if (testBtn) {
            testBtn.addEventListener('click', this.testAPIConnection.bind(this));
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const userEmail = formData.get('email');
        const businessUnit = formData.get('businessUnit');
        const customData = formData.get('customData');

        const frontendData = {
            businessUnit: businessUnit,
            customData: customData
        };

        console.log('📋 Form data collected:', { userEmail, frontendData });

        // Start authentication with custom claims
        await this.claimsIntegration.authenticateWithCustomClaims(userEmail, frontendData);
    }

    async testAPIConnection() {
        const isConnected = await this.claimsIntegration.testConnection();
        const status = isConnected ? 'Connected' : 'Failed';
        
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
        }
        
        return isConnected;
    }

    // Process authentication callback from Entra
    handleAuthCallback() {
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const idToken = params.get('id_token');
        
        if (idToken) {
            console.log('Authentication successful!');
            console.log('Token received:', idToken);
            
            // Decode token to view custom claims
            try {
                const tokenPayload = JSON.parse(atob(idToken.split('.')[1]));
                console.log('Token payload:', tokenPayload);
                
                // Extract custom claims
                const customClaims = {
                    businessUnit: tokenPayload.businessUnit,
                    deviceInfo: tokenPayload.deviceInfo,
                    customData: tokenPayload.customData,
                    apiVersion: tokenPayload.apiVersion,
                    source: tokenPayload.source,
                    dataSource: tokenPayload.dataSource
                };
                
                console.log('Custom Claims found:', customClaims);
                this.displayCustomClaims(customClaims);
                
            } catch (error) {
                console.error('Error decoding token:', error);
            }
        }
    }

    displayCustomClaims(claims) {
        const container = document.getElementById('custom-claims-display');
        if (container) {
            container.innerHTML = `
                <h3>Custom Claims Received:</h3>
                <pre>${JSON.stringify(claims, null, 2)}</pre>
            `;
        }
    }
}

// Utility functions
const ClaimsUtils = {
    // Parse JWT token without validation
    parseJWT: function(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            return JSON.parse(jsonPayload);
        } catch (error) {
            console.error('Error parsing JWT:', error);
            return null;
        }
    },

    // Extract custom claims from token
    extractCustomClaims: function(token) {
        const payload = this.parseJWT(token);
        if (!payload) return null;

        return {
            businessUnit: payload.businessUnit,
            deviceInfo: payload.deviceInfo,
            customData: payload.customData,
            apiVersion: payload.apiVersion,
            source: payload.source,
            dataSource: payload.dataSource,
            timestamp: payload.timestamp
        };
    },

    // Check if we're on a callback page
    isCallbackPage: function() {
        return window.location.hash.includes('id_token');
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize demo if auth form exists
    if (document.getElementById('auth-form')) {
        window.authDemo = new AuthenticationDemo();
    }
    
    // Handle callback if we're on the callback page
    if (ClaimsUtils.isCallbackPage()) {
        const demo = window.authDemo || new AuthenticationDemo();
        demo.handleAuthCallback();
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        CustomClaimsIntegration, 
        AuthenticationDemo, 
        ClaimsUtils 
    };
}