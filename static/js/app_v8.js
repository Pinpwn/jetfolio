// V8: Zerodha Integration Functions
// Append to app.js

// Update loadSettings to include Zerodha status
async function loadSettings() {
    // Perplexity API key
    try {
        const res = await fetch('/api/config/perplexity_api_key');
        const data = await res.json();
        if (data.value) {
            document.getElementById('perplexity-api-key-input').value = '••••••••';
        }
    } catch (err) {
        console.error(err);
    }

    // V8: Check Zerodha status
    checkZerodhaStatus();
}

async function checkZerodhaStatus() {
    const statusDiv = document.getElementById('zerodha-status');
    try {
        const res = await fetch('/api/zerodha/status');
        const data = await res.json();

        if (data.authenticated && data.user_id) {
            statusDiv.innerHTML = `<span style="color:var(--success)">✓ Connected as ${data.user_id}</span>`;
        } else if (data.api_key_configured) {
            statusDiv.innerHTML = '<span style="color:var(--warning)">⚠ API key configured. Click "Connect Zerodha" to authenticate.</span>';
        } else {
            statusDiv.innerHTML = '<span style="color:var(--text-muted)">Not configured. Add your API credentials above.</span>';
        }
    } catch (err) {
        statusDiv.innerHTML = '<span style="color:var(--danger)">Error checking status</span>';
    }
}

window.saveZerodhaCredentials = async () => {
    const apiKey = document.getElementById('zerodha-api-key-input').value;
    const apiSecret = document.getElementById('zerodha-api-secret-input').value;

    if (!apiKey || !apiSecret) {
        alert('Please enter both API key and secret');
        return;
    }

    try {
        await fetch(`/api/config/zerodha_api_key?value=${encodeURIComponent(apiKey)}`, {
            method: 'PUT'
        });
        await fetch(`/api/config/zerodha_api_secret?value=${encodeURIComponent(apiSecret)}`, {
            method: 'PUT'
        });

        alert('Zerodha credentials saved! Now click "Connect Zerodha" to authenticate.');
        document.getElementById('zerodha-api-key-input').value = '';
        document.getElementById('zerodha-api-secret-input').value = '';
        checkZerodhaStatus();
    } catch (err) {
        alert('Error saving credentials');
        console.error(err);
    }
}

window.connectZerodha = () => {
    // Open OAuth flow in new window or redirect
    window.location.href = '/api/zerodha/login';
}

// Check for OAuth callback success
if (window.location.search.includes('zerodha=connected')) {
    alert('Zerodha connected successfully! You can now sync your portfolio.');
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
    // Switch to settings if not already there
    switchTab('settings');
}
