// Toast Notification System
// Add to app.js

class ToastNotification {
    constructor() {
        this.container = this.createContainer();
        document.body.appendChild(this.container);
    }

    createContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        `;
        return container;
    }

    show(message, type = 'info', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icon = this.getIcon(type);
        toast.innerHTML = `
            <span class="toast-icon">${icon}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        this.container.appendChild(toast);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                toast.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    }

    getIcon(type) {
        const icons = {
            info: 'ℹ️',
            success: '✅',
            warning: '⚠️',
            error: '❌',
            loading: '⏳'
        };
        return icons[type] || icons.info;
    }

    loading(message) {
        const toast = this.show(message, 'loading', 0);
        toast.classList.add('breathing');
        return toast;
    }

    success(message) {
        return this.show(message, 'success', 4000);
    }

    error(message) {
        return this.show(message, 'error', 6000);
    }

    warning(message) {
        return this.show(message, 'warning', 5000);
    }
}

// Initialize toast system
window.toast = new ToastNotification();

// Replace sync button handler (not add to it)
document.addEventListener('DOMContentLoaded', () => {
    const syncBtn = document.getElementById('sync-btn');
    if (syncBtn) {
        // Clone and replace to strip ALL existing event listeners
        const newSyncBtn = syncBtn.cloneNode(true);
        syncBtn.parentNode.replaceChild(newSyncBtn, syncBtn);

        // Add new handler with toast
        newSyncBtn.addEventListener('click', async () => {
            console.log('Sync button clicked');
            const loadingToast = window.toast.loading('Syncing portfolio from Zerodha...');
            try {
                // Verify fetchPortfolio is available (global scope from app.js)
                if (typeof fetchPortfolio !== 'function') {
                    console.error('fetchPortfolio is not defined');
                    // Fallback or retry? app.js might not be loaded yet? 
                    // It should be loaded by the time user clicks.
                }

                const res = await fetch('/api/sync', { method: 'POST' });
                if (!res.ok) throw new Error('Sync failed');
                loadingToast.remove();
                window.toast.success('Portfolio synced successfully!');

                if (typeof fetchPortfolio === 'function') await fetchPortfolio();
                if (typeof fetchStocks === 'function') await fetchStocks();

            } catch (err) {
                loadingToast.remove();
                window.toast.error('Failed to sync portfolio');
                console.error(err);
            }
        });
    }

    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        // Remove any existing onclick
        refreshBtn.onclick = null;

        // Add new handler with toast
        refreshBtn.addEventListener('click', async () => {
            const loadingToast = window.toast.loading('Scraping news & generating insights...');
            try {
                const res = await fetch('/api/refresh', { method: 'POST' });
                const data = await res.json();
                loadingToast.remove();
                window.toast.success(`Refreshed! Added ${data.articles_added || 0} news articles`);
                setTimeout(() => {
                    renderDashboardLLMWidgets();
                    if (window.location.hash === '#news') renderNews();
                }, 500);
            } catch (err) {
                loadingToast.remove();
                window.toast.error('Failed to refresh insights');
                console.error(err);
            }
        });
    }
});

// Enhance theme creation/editing
const originalSubmitTheme = window.submitTheme;
window.submitTheme = async () => {
    const loadingToast = window.toast.loading('Saving theme...');
    try {
        await originalSubmitTheme();
        loadingToast.remove();
        window.toast.success('Theme saved successfully!');
    } catch (err) {
        loadingToast.remove();
        window.toast.error('Failed to save theme');
    }
}
