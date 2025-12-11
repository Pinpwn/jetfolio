// V7: Frontend JavaScript - News, Settings, Dashboard LLM Widgets
// Append this to the end of app.js

// Update switchTab to handle news and settings
const originalSwitchTab = window.switchTab;
window.switchTab = (tabName) => {
    const dashboardView = document.getElementById('dashboard-view');
    const portfolioView = document.getElementById('portfolio-view');
    const analyticsView = document.getElementById('analytics-view');
    const newsView = document.getElementById('news-view');
    const settingsView = document.getElementById('settings-view');

    const navDashboard = document.getElementById('nav-dashboard');
    const navPortfolio = document.getElementById('nav-portfolio');
    const navAnalytics = document.getElementById('nav-analytics');
    const navNews = document.getElementById('nav-news');
    const navSettings = document.getElementById('nav-settings');

    // Hide all
    [dashboardView, portfolioView, analyticsView, newsView, settingsView].forEach(v => v?.classList.add('hidden'));
    [navDashboard, navPortfolio, navAnalytics, navNews, navSettings].forEach(n => n?.classList.remove('active'));

    // Show selected
    if (tabName === 'dashboard') {
        dashboardView.classList.remove('hidden');
        navDashboard.classList.add('active');
        renderDashboardLLMWidgets();
    } else if (tabName === 'portfolio') {
        portfolioView.classList.remove('hidden');
        navPortfolio.classList.add('active');
    } else if (tabName === 'analytics') {
        analyticsView.classList.remove('hidden');
        navAnalytics.classList.add('active');
        renderAnalytics();
    } else if (tabName === 'news') {
        newsView.classList.remove('hidden');
        navNews.classList.add('active');
        renderNews();
    } else if (tabName === 'settings') {
        settingsView.classList.remove('hidden');
        navSettings.classList.add('active');
        loadSettings();
    }
}

// News Rendering
async function renderNews() {
    const newsList = document.getElementById('news-list');
    newsList.innerHTML = '<p style="color:var(--text-muted)">Loading news...</p>';

    try {
        const res = await fetch('/api/news?days=1');
        const news = await res.json();

        if (news.length === 0) {
            newsList.innerHTML = '<p style="color:var(--text-muted)">No news available. Click "Refresh Insights" to scrape latest news.</p>';
            return;
        }

        newsList.innerHTML = '';
        news.forEach(article => {
            const div = document.createElement('div');
            div.className = 'list-item';
            div.style.cursor = 'pointer';
            div.onclick = () => window.open(article.url, '_blank');

            const dateStr = article.published_date ? new Date(article.published_date).toLocaleString() : 'Recently';

            div.innerHTML = `
                <div class="item-info">
                    <h4>${article.title}</h4>
                    <p style="margin-top:0.5rem">${article.summary || 'Click to read more'}</p>
                    <small style="color:var(--text-muted); display:block; margin-top:0.5rem">
                        ${article.source} • ${dateStr}
                    </small>
                </div>
            `;
            newsList.appendChild(div);
        });
    } catch (err) {
        newsList.innerHTML = '<p style="color:var(--danger)">Error loading news</p>';
        console.error(err);
    }
}

// Dashboard LLM Widgets
async function renderDashboardLLMWidgets() {
    // Portfolio Summary
    const summaryDiv = document.getElementById('dashboard-portfolio-summary');
    summaryDiv.innerHTML = '<p style="color:var(--text-muted)">Loading AI summary...</p>';

    try {
        const res = await fetch('/api/llm/portfolio-summary');
        const data = await res.json();

        summaryDiv.innerHTML = `
            <p style="margin-bottom:1rem">${data.summary}</p>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin-top:1rem">
                <div>
                    <strong style="color:var(--success)">✓ Positives</strong>
                    <ul style="margin-top:0.5rem; padding-left:1.5rem">
                        ${data.positives.map(p => `<li style="font-size:0.9rem; margin-bottom:0.3rem">${p}</li>`).join('')}
                    </ul>
                </div>
                <div>
                    <strong style="color:var(--danger)">⚠ Watch</strong>
                    <ul style="margin-top:0.5rem; padding-left:1.5rem">
                        ${data.negatives.map(n => `<li style="font-size:0.9rem; margin-bottom:0.3rem">${n}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `;
    } catch (err) {
        summaryDiv.innerHTML = '<p style="color:var(--text-muted)">Configure API key in Settings to enable AI insights</p>';
    }

    // Theme Insights
    const themeGrid = document.getElementById('theme-insights-grid');
    themeGrid.innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';

    try {
        const res = await fetch('/api/llm/theme-summaries');
        const summaries = await res.json();

        if (summaries.length === 0) {
            themeGrid.innerHTML = '<p style="color:var(--text-muted)">No themes to analyze</p>';
            return;
        }

        themeGrid.innerHTML = '';
        summaries.forEach(theme => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h4 style="margin-bottom:0.5rem">${theme.theme}</h4>
                <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:1rem">${theme.summary.substring(0, 150)}...</p>
                <div style="font-size:0.85rem">
                    <div style="color:var(--success); margin-bottom:0.5rem">
                        <strong>+</strong> ${theme.positives[0] || 'N/A'}
                    </div>
                    <div style="color:var(--danger)">
                        <strong>-</strong> ${theme.negatives[0] || 'N/A'}
                    </div>
                </div>
            `;
            themeGrid.appendChild(card);
        });
    } catch (err) {
        themeGrid.innerHTML = '<p style="color:var(--text-muted)">Configure API key to enable</p>';
    }
}

// Settings Management
async function loadSettings() {
    try {
        const res = await fetch('/api/config/perplexity_api_key');
        const data = await res.json();
        if (data.value) {
            document.getElementById('perplexity-api-key-input').value = '••••••••'; // Masked
        }
    } catch (err) {
        console.error(err);
    }
}

window.saveApiKey = async () => {
    const input = document.getElementById('perplexity-api-key-input');
    const key = input.value;

    if (!key || key === '••••••••') {
        alert('Please enter a valid API key');
        return;
    }

    try {
        await fetch(`/api/config/perplexity_api_key?value=${encodeURIComponent(key)}`, {
            method: 'PUT'
        });
        alert('API Key saved successfully!');
        input.value = '••••••••';
    } catch (err) {
        alert('Error saving API key');
        console.error(err);
    }
}

window.refreshLogs = async () => {
    const viewer = document.getElementById('logs-viewer');
    viewer.value = 'Loading logs...';

    try {
        const res = await fetch('/api/logs?lines=200');
        const data = await res.json();
        viewer.value = data.logs || 'No logs available';
        viewer.scrollTop = viewer.scrollHeight; // Scroll to bottom
    } catch (err) {
        viewer.value = 'Error loading logs';
        console.error(err);
    }
}

// Auto-refresh Dashboard LLM on refresh button
const originalRefreshBtn = document.getElementById('refresh-btn');
if (originalRefreshBtn) {
    originalRefreshBtn.addEventListener('click', () => {
        setTimeout(renderDashboardLLMWidgets, 2000); // Wait for refresh to complete
    });
}
