document.addEventListener('DOMContentLoaded', () => {
    fetchPortfolio();
    fetchStocks();
    fetchThemes();
    fetchInsights();

    // Default Tab
    switchTab('dashboard');

    document.getElementById('refresh-btn').addEventListener('click', async () => {
        const loadingToast = window.toast.loading('Scraping news & generating insights...');
        try {
            const res = await fetch('/api/refresh', { method: 'POST' });
            const data = await res.json();
            loadingToast.remove();
            window.toast.success(`Refreshed! Added ${data.articles_added || 0} news articles`);
            refreshAll();
        } catch (err) {
            loadingToast.remove();
            window.toast.error('Failed to refresh insights');
            console.error(err);
        }
    });

    const syncBtn = document.getElementById('sync-btn');
    if (syncBtn) {
        syncBtn.addEventListener('click', async () => {
            const loadingToast = window.toast.loading('Syncing portfolio from broker...');
            try {
                const res = await fetch('/api/sync', { method: 'POST' });
                if (!res.ok) throw new Error('Sync failed');
                loadingToast.remove();
                window.toast.success('Portfolio synced successfully!');
                refreshAll();
            } catch (err) {
                loadingToast.remove();
                window.toast.error('Failed to sync portfolio');
                console.error(err);
            }
        });
    }

    document.getElementById('create-theme-btn').addEventListener('click', () => {
        openCreateTheme();
    });
    // Start polling for background status
    pollBackgroundStatus();
});

// Polling for Sync Status
async function pollBackgroundStatus() {
    const pill = document.getElementById('sync-status-pill');
    const text = document.getElementById('sync-status-text');

    // Poll every 2 seconds
    setInterval(async () => {
        try {
            const res = await fetch('/api/background-status');
            const status = await res.json();

            // Logic: If any task is running (sync or refresh)
            const isRunning = status.sync_running || status.refresh_running;

            if (isRunning) {
                pill.classList.remove('hidden');
                if (status.sync_running) text.textContent = "Syncing Portfolio...";
                else if (status.refresh_running) text.textContent = "Refreshing News...";
            } else {
                // If it was visible, hide it and maybe refresh data once
                if (!pill.classList.contains('hidden')) {
                    pill.classList.add('hidden');
                    // Optional: Auto refresh view when done
                    refreshAll();
                    showToast("Sync Complete", "success");
                }
            }
        } catch (e) {
            console.error("Status poll failed", e);
        }
    }, 2000);
}

window.closeModal = (modalId) => {
    document.getElementById(modalId).classList.add('hidden');
    if (modalId === 'theme-modal') {
        document.getElementById('theme-name-input').value = '';
        document.getElementById('theme-desc-input').value = '';
        currentEditingThemeId = null; // Reset
        document.getElementById('theme-modal-title').textContent = "Create New Theme";
        document.getElementById('theme-submit-btn').textContent = "Create";
    }
}

let currentEditingThemeId = null;

window.openCreateTheme = () => {
    currentEditingThemeId = null;
    document.getElementById('theme-name-input').value = '';
    document.getElementById('theme-desc-input').value = '';
    document.getElementById('theme-modal-title').textContent = "Create New Theme";
    document.getElementById('theme-submit-btn').textContent = "Create";
    document.getElementById('theme-modal').classList.remove('hidden');
}

window.openEditTheme = (id, name, desc) => {
    currentEditingThemeId = id;
    document.getElementById('theme-name-input').value = name;
    document.getElementById('theme-desc-input').value = desc;
    document.getElementById('theme-modal-title').textContent = "Edit Theme";
    document.getElementById('theme-submit-btn').textContent = "Save";
    document.getElementById('theme-modal').classList.remove('hidden');
}

window.submitTheme = async () => {
    const name = document.getElementById('theme-name-input').value;
    const desc = document.getElementById('theme-desc-input').value;

    if (name) {
        const loadingToast = window.toast.loading('Saving theme...');
        try {
            if (currentEditingThemeId) {
                // Update
                await fetch(`/api/themes/${currentEditingThemeId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, description: desc })
                });
            } else {
                // Create
                await fetch('/api/themes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name, description: desc || "User created theme" })
                });
            }
            loadingToast.remove();
            window.toast.success('Theme saved successfully!');
            refreshAll(); // Auto-refresh everything
            closeModal('theme-modal');
        } catch (err) {
            loadingToast.remove();
            window.toast.error("Failed to save theme");
        }
    }
}

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
    const views = [dashboardView, portfolioView, analyticsView, newsView, settingsView];
    const navs = [navDashboard, navPortfolio, navAnalytics, navNews, navSettings];

    views.forEach(el => el && el.classList.add('hidden'));
    navs.forEach(el => el && el.classList.remove('active'));

    // Show selected
    if (tabName === 'dashboard') {
        dashboardView.classList.remove('hidden');
        navDashboard.classList.add('active');
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
        renderNews(); // Refresh news when tab opens
    } else if (tabName === 'settings') {
        settingsView.classList.remove('hidden');
        navSettings.classList.add('active');
    }
}

function refreshAll() {
    fetchPortfolio();
    fetchStocks();
    fetchThemes();
    fetchInsights();
}

async function fetchThemes() {
    const grid = document.getElementById('themes-grid');
    if (!grid) return;
    grid.innerHTML = '';

    try {
        const res = await fetch('/api/themes');
        const themes = await res.json();

        if (themes.length === 0) {
            grid.innerHTML = '<p style="color:var(--text-muted)">No themes created yet.</p>';
            return;
        }

        themes.forEach(theme => {
            const div = document.createElement('div');
            div.className = 'theme-card';
            // Pencil Icon for Edit
            div.innerHTML = `
                <div class="theme-header">
                    <span class="theme-name">${theme.name}
                        <button class="icon-btn" onclick="openEditTheme(${theme.id}, '${theme.name}', '${theme.description || ''}')" title="Edit Theme">✎</button>
                    </span>
                    <span class="theme-stocks">${theme.stock_count} Stocks</span>
                </div>
                <div>
                   <small style="color:var(--text-muted)">${theme.description || 'No description'}</small>
                </div>
                <div style="margin-top:0.5rem; display:flex; gap:0.5rem">
                    <button onclick="openManageStocks(${theme.id}, '${theme.name}')" class="btn-small">Manage Stocks</button>
                </div>
            `;
            grid.appendChild(div);
        });
    } catch (err) {
        console.error(err);
    }
}

// New V5: Edit Description
window.editThemeDesc = async (id) => {
    const newDesc = prompt("Update Description:");
    if (newDesc) {
        await fetch(`/api/themes/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: newDesc })
        });
        fetchThemes();
    }
}

// V6: Analytics Rendering
let themeAllocationChartInstance = null;

async function renderAnalytics() {
    try {
        const res = await fetch('/api/themes');
        const themes = await res.json();

        // Filter out themes with no value
        const themesWithValue = themes.filter(t => t.total_value > 0);

        if (themesWithValue.length === 0) {
            // No data to display
            const canvas = document.getElementById('themeAllocationChart');
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.font = '14px Outfit';
            ctx.fillStyle = '#a1a1aa';
            ctx.textAlign = 'center';
            ctx.fillText('No theme data available', canvas.width / 2, canvas.height / 2);
            return;
        }

        const labels = themesWithValue.map(t => t.name);
        const data = themesWithValue.map(t => t.total_value);
        const total = data.reduce((sum, val) => sum + val, 0);

        // Color palette
        const colors = [
            '#6366f1', // primary
            '#10b981', // success  
            '#f59e0b', // warning
            '#ef4444', // danger
            '#8b5cf6', // purple
            '#ec4899', // pink
            '#14b8a6', // teal
        ];

        const canvas = document.getElementById('themeAllocationChart');

        // Destroy existing chart if present
        if (themeAllocationChartInstance) {
            themeAllocationChartInstance.destroy();
        }

        themeAllocationChartInstance = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#18181f'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 12,
                                family: 'Outfit'
                            },
                            padding: 15
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(context.parsed);
                                }
                                return label;
                            }
                        }
                    }
                },
                onClick: (evt, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const clickedLabel = labels[index];
                        // Trigger filter
                        window.filterAnalytics(clickedLabel);
                    }
                },
                onHover: (event, chartElement) => {
                    if (event.native) {
                        event.native.target.style.cursor = chartElement.length ? 'pointer' : 'default';
                    }
                }
            }
        });

        // Populate Filter Dropdown
        const filterSelect = document.getElementById('theme-filter-select');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">All Themes</option>';
            // Sort themes alphabetically (use copy to avoid mutating labels array)
            [...labels].sort().forEach(label => {
                const option = document.createElement('option');
                option.value = label;
                option.textContent = label;
                filterSelect.appendChild(option);
            });

            // Re-select if active
            if (currentThemeFilter) {
                filterSelect.value = currentThemeFilter;
            }
        }
    } catch (err) {
        console.error('Error rendering analytics:', err);
    }
}

// Helper for Reference Links
function renderReferenceIcon(citations) {
    if (!citations) return '';
    // Handle JSON string if passed directly (for timeline) or object
    let list = citations;
    if (typeof citations === 'string') {
        try { list = JSON.parse(citations); } catch (e) { return ''; }
    }

    if (!list || list.length === 0) return '';

    const linksHtml = list.map(url => {
        try {
            const domain = new URL(url).hostname.replace('www.', '');
            return `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${domain}</a></li>`;
        } catch (e) { return ''; }
    }).join('');

    if (!linksHtml) return '';

    return `
        <span class="ref-icon">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <div class="ref-tooltip">
                <strong>Sources:</strong>
                <ul>${linksHtml}</ul>
            </div>
        </span>
    `;
}

// Inject CSS for Tooltip
const style = document.createElement('style');
style.textContent = `
    .ref-icon {
        position: relative;
        display: inline-flex;
        align-items: center;
        margin-left: 6px;
        cursor: help;
        color: var(--text-muted);
        vertical-align: middle;
    }
    .ref-icon:hover { color: var(--accent); }
    .ref-tooltip {
        visibility: hidden;
        position: absolute;
        bottom: 140%;
        left: 50%;
        transform: translateX(-50%);
        background: #1f2937;
        border: 1px solid #374151;
        padding: 0.75rem;
        border-radius: 0.5rem;
        width: 220px;
        z-index: 50;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        opacity: 0;
        transition: opacity 0.2s;
        text-align: left;
    }
    .ref-icon:hover .ref-tooltip {
        visibility: visible;
        opacity: 1;
    }
    .ref-tooltip ul { padding: 0; margin: 0.25rem 0 0 0; list-style: none; }
    .ref-tooltip li { margin-bottom: 0.25rem; font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ref-tooltip a { color: var(--accent); text-decoration: none; }
    .ref-tooltip a:hover { text-decoration: underline; }
    
    /* Small Arrow */
    .ref-tooltip::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #1f2937 transparent transparent transparent;
    }
`;
document.head.appendChild(style);


async function fetchInsights(refresh = false) {
    try {
        if (refresh) {
            const list = document.getElementById('portfolio-insights-list');
            if (list) list.innerHTML = '<p style="color:var(--text-muted)">Refreshing insights...</p>';
        }
        const res = await fetch(`/api/insights${refresh ? '?refresh=true' : ''}`);
        const data = await res.json();

        const allInsights = [...data.insights.winners, ...data.insights.losers];

        // 1. Dashboard Top 5
        const dashList = document.getElementById('dashboard-insights-list');
        if (dashList) {
            dashList.innerHTML = '';
            // Sort by absolute move magnitude
            allInsights.sort((a, b) => Math.abs(b.pct_change) - Math.abs(a.pct_change));
            const top5 = allInsights.slice(0, 5);

            top5.forEach(item => {
                const div = document.createElement('div');
                div.className = 'list-item';
                const color = item.pct_change >= 0 ? 'var(--success)' : 'var(--danger)';

                const refHtml = renderReferenceIcon(item.citations);

                div.innerHTML = `
                    <div class="item-info">
                        <h4 style="color:${color}">${item.symbol} (${item.pct_change.toFixed(2)}%)</h4>
                        <p style="display:inline-block">${item.reason || 'No specific news.'} ${refHtml}</p>
                    </div>
                `;
                dashList.appendChild(div);
            });
        }

        // 2. Portfolio All Insights
        const portList = document.getElementById('portfolio-insights-list');
        if (portList) {
            portList.innerHTML = '';
            allInsights.forEach(item => {
                const div = document.createElement('div');
                div.className = 'list-item';
                const color = item.pct_change >= 0 ? 'var(--success)' : 'var(--danger)';
                const refHtml = renderReferenceIcon(item.citations);

                div.innerHTML = `
                    <div class="item-info">
                        <h4 style="color:${color}">${item.symbol} (${item.pct_change.toFixed(2)}%)</h4>
                        <p>${item.reason || '-'} ${refHtml}</p>
                    </div>
                    <div style="font-weight:600">${item.current_price.toFixed(2)}</div>
                `;
                portList.appendChild(div);
            });
        }

        // 3. Timeline
        const timelineList = document.getElementById('timeline-list');
        if (timelineList) {
            timelineList.innerHTML = '';
            data.timeline.forEach(event => {
                const div = document.createElement('div');
                div.className = 'timeline-item';

                const refHtml = renderReferenceIcon(event.references);

                div.innerHTML = `
                    <div class="timeline-date">${new Date(event.date).toLocaleDateString()}</div>
                    <strong>${event.title}</strong>
                    <p style="font-size:0.85rem; color:var(--text-muted)">${event.description} ${refHtml}</p>
                `;
                timelineList.appendChild(div);
            });
        }

    } catch (err) {
        console.error("Insights Error:", err);
        const list = document.getElementById('portfolio-insights-list');
        if (list) list.innerHTML = `<p style="color:var(--danger)">Error loading insights: ${err.message}</p>`;
    }
}

async function fetchPortfolio() {
    try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();

        // Update Metrics
        document.getElementById('total-value').textContent = formatCurrency(data.total_value_inr);
        document.getElementById('invested-value').textContent = formatCurrency(data.invested_value_inr);
        document.getElementById('day-change').textContent = formatCurrency(data.day_change_inr);

        // Growth / Percentage
        const growthEl = document.getElementById('overall-growth');
        const growthValEl = document.getElementById('growth-value');
        growthEl.textContent = `${data.overall_growth_percentage >= 0 ? '+' : ''}${data.overall_growth_percentage.toFixed(2)}%`;
        growthEl.className = `trend ${data.overall_growth_percentage >= 0 ? 'positive' : 'negative'}`;
        growthValEl.textContent = `${data.overall_growth_inr >= 0 ? '+' : ''}${formatCurrency(data.overall_growth_inr)}`;
        // Color for value too? Maybe keep text muted usually, or color match trend.
        growthValEl.style.color = data.overall_growth_inr >= 0 ? 'var(--success)' : 'var(--danger)';

        // Day Change %
        const dayPctEl = document.getElementById('day-change-pct');
        dayPctEl.textContent = `${data.day_change_percentage >= 0 ? '+' : ''}${data.day_change_percentage.toFixed(2)}%`;
        dayPctEl.className = `trend ${data.day_change_percentage >= 0 ? 'positive' : 'negative'}`;

        // Render Chart
        renderAllocationChart(data.allocation);
    } catch (err) {
        console.error("Failed to fetch portfolio data", err);
    }
}

// Holdings Table V5
// Global variable for current filter
let currentThemeFilter = null;

// Holdings Table V6: Added Filtering
async function fetchStocks(filterTheme = null) {
    try {
        const res = await fetch('/api/stocks');
        const stocks = await res.json();

        // Update global filter if provided (or reset if explicitly null passed for clear)
        // Actually, let's keep it simple: we use a global state `currentThemeFilter`
        // If argument is provided, we update state.
        if (filterTheme !== undefined) {
            currentThemeFilter = filterTheme;
        }

        const tbody = document.getElementById('holdings-table-body');
        if (!tbody) return; // Guard clause if element not found

        tbody.innerHTML = '';

        // Filter logic
        let displayStocks = stocks;
        if (currentThemeFilter) {
            displayStocks = stocks.filter(stock =>
                stock.themes && stock.themes.some(t => t.name === currentThemeFilter)
            );
        }

        displayStocks.forEach(stock => {
            // Calc value
            let value = stock.quantity * stock.current_price;
            let currencySymbol = stock.currency === 'USD' ? '$' : '₹';

            // Baskets HTML
            let basketsHtml = '';
            if (stock.themes && stock.themes.length > 0) {
                stock.themes.forEach(t => {
                    basketsHtml += `<span class="basket-tag">${t.name}</span>`;
                });
            } else {
                basketsHtml = '<span style="color:#666; font-size:0.8rem">-</span>';
            }

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${stock.symbol}</td>
                <td>${stock.name}</td>
                <td><span style="text-transform: capitalize;">${stock.platform}</span></td>
                <td>${basketsHtml}</td>
                <td>${currencySymbol}${value.toFixed(2)}</td>
                <td>
                    <div class="row-actions">
                         <button class="btn-small" onclick="showAnalysis(${stock.id}, '${stock.symbol}', ${stock.quantity}, ${stock.current_price}, '${currencySymbol}')">Analysis</button>
                         <button class="btn-small btn-secondary" onclick="openManageStock(${stock.id}, '${stock.symbol}')" title="Manage Holding">Edit</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (displayStocks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:1rem; color:var(--text-muted)">No stocks found for this filter.</td></tr>';
        }

    } catch (err) {
        console.error("Failed to fetch stocks", err);
    }
}

window.clearFilter = () => {
    window.filterAnalytics('');
}

window.filterAnalytics = (themeName) => {
    // If empty string passed (e.g. from dropdown "All Themes"), treat as null/reset
    const filterVal = themeName === '' ? null : themeName;
    fetchStocks(filterVal);

    // Sync Dropdown
    const select = document.getElementById('theme-filter-select');
    if (select) {
        select.value = themeName;
    }

    // Scroll to table only if filter is active
    if (themeName) {
        const tableSection = document.querySelector('.holdings-section');
        if (tableSection) {
            tableSection.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

// --- V4 New Functions ---

// Analysis V5: Includes Qty/Price
window.showAnalysis = async (id, symbol, qty, price, curr) => {
    const modal = document.getElementById('analysis-modal');
    const content = document.getElementById('analysis-content');
    const title = document.getElementById('analysis-title');

    modal.classList.remove('hidden');
    title.textContent = `Analysis: ${symbol}`;
    content.innerHTML = '<p>Loading latest data...</p>';

    try {
        const res = await fetch(`/api/stocks/${symbol}/analysis`);
        const data = await res.json();

        const ratings = data.analyst_ratings;
        const sentimentColor = ratings.consensus === 'Bullish' ? 'var(--success)' : (ratings.consensus === 'Bearish' ? 'var(--danger)' : 'var(--warning)');

        let newsHtml = '';
        data.latest_news.forEach(n => {
            // Mock URL if missing (scraper v5 requirement said make them clickable)
            const url = n.url || `https://www.google.com/search?q=${encodeURIComponent(n.title)}`;
            newsHtml += `
                <div style="margin-bottom:0.8rem; border-bottom:1px solid #333; padding-bottom:0.5rem">
                    <a href="${url}" target="_blank" style="font-weight:600; color:var(--text-main); text-decoration:none; display:block; margin-bottom:0.2rem">${n.title} ↗</a>
                    <div style="font-size:0.8rem; color:var(--text-muted)">${n.source} • ${n.time}</div>
                </div>
            `;
        });

        let linksHtml = '';
        data.links.forEach(l => {
            linksHtml += `<a href="${l.url}" target="_blank">${l.name} ↗</a>`;
        });

        // Inject Qty/Price info at top of modal
        // Note: passing qty/price/curr from button click args
        const holdingsInfo = (qty !== undefined) ? `
            <div style="background:var(--bg-dark); padding:1.5rem; border-radius:8px; margin-bottom:1.5rem; display:flex; gap:2rem;">
                <div>
                    <small style="color:#aaa">Quantity</small>
                    <div style="font-size:1.2rem; font-weight:600">${qty}</div>
                </div>
                <div>
                    <small style="color:#aaa">Current Price</small>
                    <div style="font-size:1.2rem; font-weight:600">${curr}${price.toFixed(2)}</div>
                </div>
                <div>
                     <small style="color:#aaa">Total Value</small>
                     <div style="font-size:1.2rem; font-weight:600">${curr}${(qty * price).toFixed(2)}</div>
                </div>
            </div>
        ` : '';

        content.innerHTML = `
            ${holdingsInfo}
            <div class="analyst-ratings">
                <div class="rating-item">
                    <strong>${ratings.buy}</strong>
                    <span>Buy</span>
                </div>
                <div class="rating-item">
                    <strong>${ratings.hold}</strong>
                    <span>Hold</span>
                </div>
                <div class="rating-item">
                    <strong>${ratings.sell}</strong>
                    <span>Sell</span>
                </div>
                <div class="rating-item">
                    <strong style="color:${sentimentColor}">${ratings.consensus}</strong>
                    <span>Consensus</span>
                </div>
            </div>
            
            <h4>Latest News</h4>
            <div style="margin-bottom:1.5rem">${newsHtml}</div>
            
            <div class="external-links">
                <h4>External Resources</h4>
                <div class="news-links">${linksHtml}</div>
            </div>
            </div>
        `;

        // V5.3: Add Manage Baskets Dropdown
        const themesRes = await fetch('/api/themes');
        const themes = await themesRes.json();

        let basketsDropdown = `
            <div style="margin-top:1.5rem; border-top:1px solid var(--border); padding-top:1rem;">
                <details>
                    <summary style="cursor:pointer; font-weight:600; color:var(--text-main)">Manage Baskets</summary>
                    <div style="margin-top:1rem; display:flex; flex-direction:column; gap:0.5rem">
        `;

        // We need to know which themes this stock is in.
        // We can fetch stock details or check themes list if we had it.
        // Let's rely on checking if stock ID is in theme.stocks (but theme.stocks might not be fully populated in this view? api returns stock_count).
        // Actually /api/themes returns ThemeRead which has stock_count but not stock list.
        // We need to know if stock is in theme.
        // Best way: Fetch stock details or iterate.
        // Let's fetch the stock again or use a helper. 
        // Simple: Fetch /api/stocks (cached?) or iterate.
        // Better: /api/stocks has themes list. 
        // Let's fetch specific stock to be sure.
        // Wait, current API `GET /api/stocks` returns list. `GET /api/stocks/{id}` does not exist yet?
        // We can add `GET /api/stocks/{id}` or just fetch all and find. 
        // Or simpler: /api/themes/{id}/stocks is not available directly.
        // Let's just fetch all stocks and find this one? 
        // Actually, we are viewing analysis for a stock.
        // Let's assume we can fetch the fresh stock data to get its current themes.
        // We don't have get stock by ID.
        // Valid approach: We have the `themes` list from /api/themes.
        // We need to check if stock is in them.
        // Let's add an endpoint or just fetch all stocks and find current.

        const allStocksRes = await fetch('/api/stocks');
        const allStocks = await allStocksRes.json();
        const currentStock = allStocks.find(s => s.id === id);
        const stockThemesIds = currentStock ? currentStock.themes.map(t => t.id) : [];

        themes.forEach(t => {
            const isChecked = stockThemesIds.includes(t.id) ? 'checked' : '';
            basketsDropdown += `
                <div style="display:flex; align-items:center; gap:0.5rem">
                    <input type="checkbox" id="basket-chk-${t.id}" ${isChecked} onchange="toggleStockInTheme(${id}, ${t.id}, this.checked)">
                    <label for="basket-chk-${t.id}">${t.name}</label>
                </div>
            `;
        });

        basketsDropdown += `
                    </div>
                </details>
            </div>
        `;

        content.innerHTML += basketsDropdown;

    } catch (err) {
        console.error(err);
        content.innerHTML = '<p>Failed to load analysis.</p>';
    }
}

// Manage Stocks Modal (Checkbox List)
let currentManageThemeId = null;
window.openManageStocks = async (themeId, themeName) => {
    currentManageThemeId = themeId;
    const modal = document.getElementById('manage-stocks-modal');
    const container = document.getElementById('stock-checklist');
    document.getElementById('manage-stocks-title').textContent = `Manage Stocks: ${themeName}`;

    modal.classList.remove('hidden');
    container.innerHTML = 'Loading...';

    try {
        const stockRes = await fetch('/api/stocks');
        const stocks = await stockRes.json();

        container.innerHTML = '';

        stocks.forEach(stock => {
            // Check if stock is in this theme
            // API V5: StockRead has themes list
            const inTheme = stock.themes.some(t => t.id === themeId);
            const checked = inTheme ? 'checked' : '';

            const div = document.createElement('div');
            div.className = 'checkbox-row';
            div.style.padding = '0.5rem';
            div.style.borderBottom = '1px solid #333';
            div.style.display = 'flex';
            div.style.alignItems = 'center';

            div.innerHTML = `
                <input type="checkbox" id="manage-chk-${stock.id}" ${checked} onchange="toggleStockInTheme(${stock.id}, ${themeId}, this.checked)">
                <label for="manage-chk-${stock.id}" style="margin-left:0.5rem; flex:1; cursor:pointer">
                    <strong>${stock.symbol}</strong> <span style="color:#666">(${stock.name})</span>
                </label>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        container.innerHTML = 'Error loading stocks';
    }
}

window.toggleStockInTheme = async (stockId, themeId, isChecked) => {
    try {
        if (isChecked) {
            await fetch(`/api/themes/${themeId}/stocks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stock_ids: [stockId] })
            });
        } else {
            await fetch(`/api/themes/${themeId}/stocks/${stockId}`, { method: 'DELETE' });
        }
        refreshAll(); // Refresh all widgets (Themes count, Holdings baskets)
    } catch (e) { console.error(e); }
}

window.filterStocks = () => {
    const input = document.getElementById('stock-search-input');
    const filter = input.value.toUpperCase();
    const container = document.getElementById('stock-checklist');
    const divs = container.getElementsByClassName('checkbox-row');

    for (let i = 0; i < divs.length; i++) {
        const label = divs[i].getElementsByTagName("label")[0];
        const txtValue = label.textContent || label.innerText;
        if (txtValue.toUpperCase().indexOf(filter) > -1) {
            divs[i].style.display = "flex";
        } else {
            divs[i].style.display = "none";
        }
    }
}

let currentStockIdForBasket = null;

window.openEditBasket = async (stockId, symbol) => {
    currentStockIdForBasket = stockId;
    const modal = document.getElementById('edit-basket-modal');
    const container = document.getElementById('basket-checkboxes');
    document.getElementById('edit-basket-title').textContent = `Edit Basket: ${symbol}`;

    modal.classList.remove('hidden');
    container.innerHTML = 'Loading...';

    try {
        const themeRes = await fetch('/api/themes');
        const themes = await themeRes.json();

        container.innerHTML = '';

        themes.forEach(theme => {
            const div = document.createElement('div');
            div.style.display = 'flex';
            div.style.justifyContent = 'space-between';
            div.style.alignItems = 'center';
            div.style.padding = '0.5rem';
            div.style.borderBottom = '1px solid #333';

            div.innerHTML = `
                <span>${theme.name}</span>
                <div>
                    <button class="btn-small" onclick="addStockToThemeDirect(${theme.id}, ${stockId})">Add</button>
                    <button class="btn-small" style="background:var(--danger); margin-left:5px" onclick="removeStockFromTheme(${theme.id}, ${stockId})">Remove</button>
                </div>
            `;
            container.appendChild(div);
        });

    } catch (err) {
        console.error(err);
        container.innerHTML = 'Error loading baskets';
    }
}

window.addStockToThemeDirect = async (themeId, stockId) => {
    try {
        await fetch(`/api/themes/${themeId}/stocks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stock_ids: [stockId] })
        });
        alert("Added to Basket");
        refreshAll();
    } catch (e) { alert("Error adding"); }
}

window.removeStockFromTheme = async (themeId, stockId) => {
    try {
        await fetch(`/api/themes/${themeId}/stocks/${stockId}`, { method: 'DELETE' });
        alert("Removed from Basket");
        refreshAll();
    } catch (e) { alert("Error removing"); }
}

function formatCurrency(num) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(num);
}

let allocationChartInstance = null;

function renderAllocationChart(allocationData) {
    const ctx = document.getElementById('allocationChart').getContext('2d');
    const labels = Object.keys(allocationData);
    const data = Object.values(allocationData);

    if (allocationChartInstance) {
        allocationChartInstance.destroy();
    }

    allocationChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#6366f1',
                    '#10b981',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#ffffff' }
                }
            }
        }
    });
}
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
        fetchStocks(); // Load holdings for the table in Analytics
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
// News Rendering (Revamped V8)
async function renderNews() {
    const newsList = document.getElementById('news-list');
    newsList.innerHTML = '<p style="color:var(--text-muted)">Loading news...</p>';
    newsList.className = 'news-grid'; // Switch to grid class

    try {
        const res = await fetch('/api/news?days=30');
        const news = await res.json();

        if (news.length === 0) {
            newsList.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1;">No news available. Click "Refresh Insights" to scrape latest news.</p>';
            return;
        }

        newsList.innerHTML = '';
        news.forEach((article, index) => {
            const div = document.createElement('div');
            div.className = 'news-card'; // Tile style
            div.style.cursor = 'pointer';
            div.onclick = () => window.open(article.url, '_blank');

            const dateStr = article.published_date ? new Date(article.published_date).toLocaleString() : 'Recently';

            // Credibility Score Logic
            const score = article.credibility_score || 5;
            let scoreColor = '#6b7280';
            if (score >= 8) scoreColor = 'var(--success)';
            else if (score >= 6) scoreColor = 'var(--warning)';
            else if (score < 5) scoreColor = 'var(--danger)';

            div.innerHTML = `
                <div class="news-header" style="display:flex; justify-content:space-between; align-items:start;">
                    <span class="stock-ticker">${article.stock_symbol || 'GEN'}</span>
                    <div style="display:flex; gap:0.5rem">
                        <!-- Credibility Badge -->
                        <span class="news-badge score" style="background:${scoreColor}" title="Source Credibility: ${score}/10">
                            ${score}/10
                        </span>
                        
                        <!-- Sentiment Badge -->
                        ${(() => {
                    const status = (article.processing_status || 'completed').toLowerCase();
                    const sent = (article.sentiment || 'neutral').toLowerCase();

                    // Pending/Processing State
                    if (status === 'pending' || status === 'processing' || !article.sentiment) {
                        return `<span class="news-badge analyzing">Analyzing...</span>`;
                    }

                    let badgeClass = 'neutral';
                    let text = 'Neutral';

                    if (sent === 'positive' || sent === 'bullish') { badgeClass = 'success'; text = 'Positive'; }
                    else if (sent === 'negative' || sent === 'bearish') { badgeClass = 'danger'; text = 'Negative'; }

                    return `<span class="news-badge ${badgeClass}">${text}</span>`;
                })()}
                    </div>
                </div>
                
                <h4 class="news-title">${article.title}</h4>
                <p class="news-summary">${article.summary || 'Click to read full article...'}</p>
                
                <div class="news-footer">
                    <span style="color:var(--primary); font-weight:600">${article.source}</span>
                    <span>${dateStr.split(',')[0]}</span>
                </div>
            `;

            // Staggered Animation
            div.style.animation = `fadeInUp 0.5s ease forwards ${index * 0.1}s`;
            div.style.opacity = '0'; // Start invisible

            newsList.appendChild(div);
        });
    } catch (err) {
        console.error("News Load Error:", err);
        newsList.innerHTML = '<p style="color:var(--danger)">Error loading news</p>';
    }
}

// Dashboard LLM Widgets
async function renderDashboardLLMWidgets() {
    fetchPortfolioSummary();
    fetchThemeSummaries();
}

async function fetchPortfolioSummary(refresh = false) {
    const summaryDiv = document.getElementById('dashboard-portfolio-summary');
    if (refresh) {
        summaryDiv.innerHTML = '<p style="color:var(--text-muted)">Refreshing AI summary...</p>';
    } else if (!summaryDiv.innerHTML.includes('Load')) {
        summaryDiv.innerHTML = '<p style="color:var(--text-muted)">Loading AI summary...</p>';
    }

    try {
        const res = await fetch(`/api/llm/portfolio-summary${refresh ? '?refresh=true' : ''}`);
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
            ${data.cached ? '<small style="color:var(--text-muted); display:block; margin-top:0.5rem">Cached response</small>' : ''}
        `;
    } catch (err) {
        summaryDiv.innerHTML = '<p style="color:var(--text-muted)">Configure API key in Settings to enable AI insights</p>';
    }
}

async function fetchThemeSummaries() {
    const themeGrid = document.getElementById('theme-insights-grid');
    themeGrid.innerHTML = '<p style="color:var(--text-muted)">Loading...</p>';
    // ... existing logic ...

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
// V8: Zerodha Integration Functions
// Append to app.js

// Update loadSettings to include all provider configs
async function loadSettings() {
    // 1. LLM Provider Selection
    try {
        const res = await fetch('/api/config/llm_provider');
        const data = await res.json();
        if (data.value) {
            const select = document.getElementById('llm-provider-select');
            if (select) {
                select.value = data.value;
                toggleProviderSettings(); // Ensure UI state matches
            }
        }
    } catch (err) { console.error(err); }

    // 2. Perplexity Config
    try {
        const res = await fetch('/api/config/perplexity_api_key');
        const data = await res.json();
        if (data.value) {
            const input = document.getElementById('perplexity-api-key-input');
            if (input) input.value = '••••••••';
        }
    } catch (err) { console.error(err); }

    // 3. Groq Config
    try {
        const resKey = await fetch('/api/config/groq_api_key');
        const dataKey = await resKey.json();
        if (dataKey.value) {
            const input = document.getElementById('groq-api-key-input');
            if (input) {
                input.value = '••••••••';
                fetchGroqModels();
            }
        }
    } catch (err) { console.error(err); }

    // 4. Local Config
    try {
        const resOllama = await fetch('/api/config/ollama_url');
        const dataOllama = await resOllama.json();
        if (dataOllama.value) {
            const input = document.getElementById('ollama-url-input');
            if (input) input.value = dataOllama.value;
        }
    } catch (err) { console.error(err); }

    // 5. Zerodha Status
    checkZerodhaStatus();
}

window.saveLLMProvider = async () => {
    const select = document.getElementById('llm-provider-select');
    const provider = select.value;

    try {
        await fetch(`/api/config/llm_provider?value=${encodeURIComponent(provider)}`, { method: 'PUT' });

        let providerName = 'Perplexity AI';
        if (provider === 'local') providerName = 'Local LLM';
        if (provider === 'groq') providerName = 'Groq Cloud';

        alert(`LLM Provider set to: ${providerName}`);
    } catch (err) {
        alert('Failed to save provider setting');
    }
}

window.saveLocalLLMConfig = async () => {
    const ollamaUrl = document.getElementById('ollama-url-input').value;

    try {
        if (ollamaUrl) {
            await fetch(`/api/config/ollama_url?value=${encodeURIComponent(ollamaUrl)}`, { method: 'PUT' });
        }
        alert('Local LLM configuration saved!');
    } catch (err) {
        alert('Failed to save local config');
    }
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

// V11: Groq Integration Functions

function toggleProviderSettings() {
    const provider = document.getElementById('llm-provider-select').value;
    const perplexitySettings = document.getElementById('perplexity-settings');
    const groqSettings = document.getElementById('groq-settings');
    const localSettings = document.getElementById('local-settings');

    // Hide all first
    if (perplexitySettings) perplexitySettings.classList.add('hidden');
    if (groqSettings) groqSettings.classList.add('hidden');
    if (localSettings) localSettings.classList.add('hidden');

    // Show selected
    if (provider === 'perplexity' && perplexitySettings) {
        perplexitySettings.classList.remove('hidden');
    } else if (provider === 'groq' && groqSettings) {
        groqSettings.classList.remove('hidden');
    } else if (provider === 'local' && localSettings) {
        localSettings.classList.remove('hidden');
    }
}

async function saveGroqKey() {
    const input = document.getElementById('groq-api-key-input');
    const key = input.value;

    if (!key || key === '••••••••') {
        alert('Please enter a valid Groq API key');
        return;
    }

    try {
        await fetch(`/api/config/groq_api_key?value=${encodeURIComponent(key)}`, { method: 'PUT' });
        alert('Groq API Key saved!\n\nThe key has been masked (••••••••) for security. You can now fetch models.');
        input.value = '••••••••';
        // Auto-fetch models if key behaves valid
        fetchGroqModels();
    } catch (err) {
        console.error(err);
        alert('Failed to save Groq Key');
    }
}

async function fetchGroqModels() {
    const select = document.getElementById('groq-model-select');
    select.innerHTML = '<option>Loading...</option>';

    try {
        const res = await fetch('/api/ai/models/groq');
        if (!res.ok) throw new Error('Failed to fetch models (Check API Key)');
        const data = await res.json();

        select.innerHTML = '<option value="" disabled>Select a model...</option>';
        data.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            select.appendChild(option);
        });

        // Restore saved selection
        const savedRes = await fetch('/api/config/groq_model');
        const savedData = await savedRes.json();
        if (savedData.value) {
            select.value = savedData.value;
        }

    } catch (err) {
        console.error(err);
        select.innerHTML = '<option value="" disabled>Error loading models</option>';
        alert('Could not fetch Groq models. Ensure API Key is saved.');
    }
}

async function saveGroqModel() {
    const model = document.getElementById('groq-model-select').value;
    if (!model) return;

    try {
        await fetch(`/api/config/groq_model?value=${encodeURIComponent(model)}`, { method: 'PUT' });
        alert(`Groq Model set to: ${model}`);
    } catch (err) {
        alert('Failed to save model config');
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
// Check for OAuth callback success
if (window.location.search.includes('zerodha=connected')) {
    alert('Zerodha connected successfully! You can now sync your portfolio.');
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
    // Switch to settings if not already there
    switchTab('settings');
}

// V9: Manual Holdings Management
window.openAddStock = () => {
    document.getElementById('add-stock-symbol').value = '';
    document.getElementById('add-stock-qty').value = '';
    document.getElementById('add-stock-price').value = '';
    document.getElementById('add-stock-modal').classList.remove('hidden');
}

window.submitNewStock = async () => {
    const symbol = document.getElementById('add-stock-symbol').value;
    const qty = parseFloat(document.getElementById('add-stock-qty').value);
    const avgPrice = parseFloat(document.getElementById('add-stock-price').value);
    const currency = document.getElementById('add-stock-currency').value;
    const type = document.getElementById('add-stock-type').value;

    if (!symbol || isNaN(qty) || isNaN(avgPrice)) {
        alert("Please fill all fields correctly");
        return;
    }

    try {
        const res = await fetch('/api/stocks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbol,
                quantity: qty,
                average_price: avgPrice,
                currency: currency,
                asset_class: type
            })
        });

        if (res.ok) {
            closeModal('add-stock-modal');
            refreshAll(); // Reload table
            // alert("Stock added successfully");
        } else {
            alert("Failed to add stock");
        }
    } catch (e) {
        console.error(e);
        alert("Error creating stock");
    }
}

let currentManageStockId = null;
let currentManageAction = 'buy'; // buy, sell, edit

window.openManageStock = (id, symbol) => {
    currentManageStockId = id;
    document.getElementById('manage-stock-title').textContent = `Manage: ${symbol}`;
    document.getElementById('manage-stock-modal').classList.remove('hidden');
    setManageAction('buy'); // Default

    // Reset inputs
    document.getElementById('manage-stock-qty').value = '';
    document.getElementById('manage-stock-price').value = '';
}

window.setManageAction = (action) => {
    currentManageAction = action;

    // Updates Buttons State
    ['buy', 'sell', 'edit'].forEach(a => {
        const btn = document.getElementById(`manage-btn-${a}`);
        if (a === action) {
            btn.classList.remove('btn-secondary');
            btn.classList.add('btn-primary');
        } else {
            btn.classList.add('btn-secondary');
            btn.classList.remove('btn-primary');
        }
    });

    // Update Labels
    const qtyLabel = document.getElementById('manage-qty-label');
    const priceLabel = document.getElementById('manage-price-label');
    const priceInput = document.getElementById('manage-stock-price');

    if (action === 'buy') {
        qtyLabel.textContent = "Quantity to Add";
        priceLabel.textContent = "Buy Price";
        priceInput.parentElement.style.display = 'block';
    } else if (action === 'sell') {
        qtyLabel.textContent = "Quantity to Trim";
        // Price not needed for trim calc (FIFO assumption usually), but maybe user wants to record sell price?
        // Backend logic doesn't use sell price for avg calc. 
        // Hide price input or keep as "Sell Price"?
        // API model expects price field. Let's keep it but label as Sell Price (optional in logic but required by Pydantic?)
        priceLabel.textContent = "Sell Price (Optional)";
        // Actually Pydantic `price` is float.
        priceInput.parentElement.style.display = 'block';
    } else if (action === 'edit') {
        qtyLabel.textContent = "Corrected Quantity";
        priceLabel.textContent = "Corrected Avg Price";
        priceInput.parentElement.style.display = 'block';
    }
}

window.submitManageStock = async () => {
    const qty = parseFloat(document.getElementById('manage-stock-qty').value);
    const price = parseFloat(document.getElementById('manage-stock-price').value || 0);

    if (isNaN(qty)) {
        alert("Please enter valid quantity");
        return;
    }

    // For Sell/Edit, logic handles price 0 if valid

    try {
        const res = await fetch(`/api/stocks/${currentManageStockId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: currentManageAction,
                quantity: qty,
                price: price
            })
        });

        if (res.ok) {
            closeModal('manage-stock-modal');
            refreshAll();
        } else {
            const err = await res.json();
            alert("Update failed: " + (err.detail || "Unknown error"));
        }
    } catch (e) {
        alert("Error updating stock");
    }
}

window.deleteStock = async () => {
    if (!confirm("Are you sure you want to completely remove this holding?")) return;

    try {
        const res = await fetch(`/api/stocks/${currentManageStockId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            closeModal('manage-stock-modal');
            refreshAll();
        } else {
            alert("Failed to delete");
        }
    } catch (e) {
        alert("Error deleting stock");
    }
}
