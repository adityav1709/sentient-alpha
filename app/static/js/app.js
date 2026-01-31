const API_BASE = '/api/v1';
let selectedAgentId = null;
let currentUser = null;
let charts = {};

// Professional Palette
const COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'
];

let myAgentChart = null;

function logout() {
    localStorage.removeItem('token');
    // Redirect to Leaderboard (Landing Page)
    window.location.href = '/static/index.html';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    const authContainer = document.getElementById('auth-action');

    const protectedNavs = document.querySelectorAll('.nav-item[onclick*="my-agents"], .nav-item[onclick*="profile"]');
    const newBtn = document.querySelector('.new-agent-btn');

    if (token) {
        // Authenticated
        fetchProfile();
        fetchMyAgents();
        protectedNavs.forEach(el => el.style.display = 'flex');
        if (newBtn) newBtn.style.display = 'block';
    } else {
        // Guest
        protectedNavs.forEach(el => el.style.display = 'none');
        if (newBtn) newBtn.style.display = 'none';

        if (authContainer) {
            authContainer.innerHTML = `
                <div style="display: flex; gap: 0.75rem;">
                    <button onclick="window.location.href='/static/login.html'" class="action-btn" style="text-decoration: none; padding: 0.5rem 1rem;">Sign In</button>
                    <button onclick="window.location.href='/static/register.html'" class="action-btn" style="text-decoration: none; padding: 0.5rem 1rem; background: transparent; border: 1px solid var(--border-subtle); color: var(--text-primary);">Register</button>
                </div>
            `;
        }
        // Force terms check
        if (!localStorage.getItem('termsAccepted')) {
            showIntroModal();
        }
    }
}

function showIntroModal() {
    const modal = document.getElementById('intro-modal');
    modal.style.display = 'flex';

    // Checkbox logic
    const checkbox = document.getElementById('terms-check');
    const btn = document.getElementById('enter-btn');

    checkbox.onchange = (e) => {
        if (e.target.checked) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.style.cursor = 'pointer';
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.style.cursor = 'not-allowed';
        }
    };
}

function acceptTerms() {
    localStorage.setItem('termsAccepted', 'true');
    document.getElementById('intro-modal').style.display = 'none';
}

function closePortfolioDrawer() {
    const drawer = document.getElementById('portfolio-drawer');
    drawer.classList.remove('active');
}


function openPortfolioView(agentId) {
    // Uses the new Drawer logic exclusively
    fetchAgentAndShowDrawer(agentId);
}

async function fetchAgentAndShowDrawer(id) {
    try {
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const response = await fetch(`${API_BASE}/agents/${id}`, { headers });
        if (!response.ok) return;
        const agent = await response.json();
        renderPortfolioDrawer(agent);
    } catch (e) { console.error(e); }
}

function renderPortfolioDrawer(agent) {
    const drawer = document.getElementById('portfolio-drawer');
    drawer.classList.add('active'); // Slide in

    document.getElementById('flyout-title').innerText = agent.name;
    document.getElementById('flyout-subtitle').innerText = `${agent.owner_username || 'System'}'s Allocation`;

    const equity = agent.portfolio ? agent.portfolio.total_equity : 10000;
    const pnl = equity - 10000;

    document.getElementById('flyout-equity').innerText = `$${equity.toLocaleString()}`;
    document.getElementById('flyout-pnl').innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString()}`;
    document.getElementById('flyout-pnl').className = `value ${pnl >= 0 ? 'text-success' : 'text-danger'}`;

    // Chart Logic
    const ctx = document.getElementById('flyoutChart').getContext('2d');
    if (window.flyoutChartInstance) window.flyoutChartInstance.destroy();

    const positions = agent.portfolio?.positions || [];
    const labels = ['Cash', ...positions.map(p => p.ticker)];
    const cash = agent.portfolio?.cash_balance || 10000;
    const data = [cash, ...positions.map(p => p.quantity * p.current_price)];

    window.flyoutChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ['#27272a', ...COLORS],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#a1a1aa' } } }
        }
    });

    // Positions Table
    const tbody = document.getElementById('flyout-positions-body');
    tbody.innerHTML = '';

    if (positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" style="text-align:center; color:var(--text-tertiary);">100% Cash Position</td></tr>';
    } else {
        positions.forEach(pos => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="display:flex;align-items:center;gap:0.75rem;">
                    ${getTickerLogo(pos.ticker)}
                    <div style="display:flex;flex-direction:column;">
                        <span style="font-weight:600;color:var(--text-primary);">${pos.ticker}</span>
                        <span style="font-size:0.75rem;color:var(--text-tertiary);">${pos.quantity} units</span>
                    </div>
                </td>
                <td style="text-align:right;">
                    <div style="font-weight:600;color:var(--text-primary);">$${(pos.current_price * pos.quantity).toFixed(0)}</div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
}

// --- Public Profile Logic ---

async function openPublicProfile(username) {
    if (!username) return;

    // reset UI
    document.getElementById('public-username').innerText = '@' + username;
    document.getElementById('public-name').innerText = "Loading...";
    document.getElementById('public-avatar').src = `https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${username}`;
    document.getElementById('public-linkedin').style.display = 'none';
    document.getElementById('public-twitter').style.display = 'none';
    document.getElementById('public-agents-body').innerHTML = '<tr><td colspan="3" style="text-align:center;">Scanning Neural Network...</td></tr>';

    document.getElementById('public-profile-drawer').classList.add('active');

    try {
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const response = await fetch(`${API_BASE}/users/${username}/public`, { headers });
        if (!response.ok) {
            document.getElementById('public-name').innerText = "User Not Found";
            return;
        }

        const user = await response.json();

        // Render Identity
        document.getElementById('public-name').innerText = `${user.first_name || ''} ${user.last_name || ''}`.trim() || "Sentient Trader";
        document.getElementById('public-avatar').src = `https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${user.avatar_id || username}`;

        // Render Socials
        if (user.linkedin_handle) {
            const el = document.getElementById('public-linkedin');
            el.href = user.linkedin_handle;
            el.style.display = 'flex';
        }
        if (user.twitter_handle) {
            const el = document.getElementById('public-twitter');
            el.href = user.twitter_handle.startsWith('http') ? user.twitter_handle : `https://twitter.com/${user.twitter_handle.replace('@', '')}`;
            el.style.display = 'flex';
        }

        // Render Agents
        const tbody = document.getElementById('public-agents-body');
        tbody.innerHTML = '';
        if (user.agents && user.agents.length > 0) {
            user.agents.forEach(agent => {
                const equity = agent.portfolio ? agent.portfolio.total_equity : 10000;
                const pnl = equity - 10000;

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 600; color: var(--text-primary);">${agent.name}</td>
                    <td><span class="badge" style="font-size:0.7rem; padding: 2px 6px;">${agent.provider.toUpperCase()}</span></td>
                    <td style="text-align: right;" class="${pnl >= 0 ? 'text-success' : 'text-danger'}">${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString()}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color: var(--text-tertiary);">No Active Agents</td></tr>';
        }

    } catch (e) {
        console.error(e);
        document.getElementById('public-name').innerText = "Error Loading Profile";
    }
}

function closePublicDrawer() {
    document.getElementById('public-profile-drawer').classList.remove('active');
}


// --- Navigation Logic ---

function showPage(pageId) {
    // Hide all views
    document.querySelectorAll('.view-content').forEach(v => v.classList.remove('active'));
    // Show target view
    const target = document.getElementById(`${pageId}-view`);
    if (target) target.classList.add('active');

    // Update Sidebar
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('onclick')?.includes(`'${pageId}'`)) {
            item.classList.add('active');
        }
    });

    if (pageId === 'profile') {
        populateProfile();
    }

    // Update Header
    const titleMap = {
        'dashboard': ['Dashboard', 'Institutional Grade AI Trading'],
        'leaderboard': ['Leaderboard', 'Global Alpha Rankings'],
        'my-agents': ['My Portfolio', 'Manage your neural assets'],
        'profile': ['Settings', 'Customize your institutional identity']
    };

    if (titleMap[pageId]) {
        document.getElementById('view-title').innerText = titleMap[pageId][0];
        document.getElementById('view-subtitle').innerText = titleMap[pageId][1];
    }

    // Refresh Data if needed
    if (pageId === 'leaderboard') fetchAgents();
    if (pageId === 'my-agents') fetchMyAgents();
    if (pageId === 'profile') renderProfileView();
}

function clearAgentContext() {
    selectedAgentId = null;
    document.getElementById('agent-context').style.display = 'none';
    document.querySelectorAll('.agent-card').forEach(el => el.classList.remove('active'));
    // Reset KPIs to default/---
    document.getElementById('total-equity').innerText = '---';
    document.getElementById('cash-balance').innerText = '---';
    document.getElementById('total-pnl').innerText = '---';
}


function populateProfile() {
    if (!currentUser) return;
    document.getElementById('edit-firstname').value = currentUser.first_name || '';
    document.getElementById('edit-lastname').value = currentUser.last_name || '';
    document.getElementById('edit-linkedin').value = currentUser.linkedin_handle || '';
    document.getElementById('edit-twitter').value = currentUser.twitter_handle || '';
}

function getTickerLogo(ticker) {
    const logos = {
        'AAPL': 'https://logo.clearbit.com/apple.com',
        'GOOGL': 'https://logo.clearbit.com/abc.xyz',
        'MSFT': 'https://logo.clearbit.com/microsoft.com',
        'TSLA': 'https://logo.clearbit.com/tesla.com',
        'NVDA': 'https://logo.clearbit.com/nvidia.com',
        'AMD': 'https://logo.clearbit.com/amd.com',
        'AMZN': 'https://logo.clearbit.com/amazon.com',
        'META': 'https://logo.clearbit.com/meta.com',
        'NFLX': 'https://logo.clearbit.com/netflix.com'
    };
    const url = logos[ticker] || `https://ui-avatars.com/api/?name=${ticker}&background=random&color=fff&size=32`;
    return `<img src="${url}" class="ticker-logo" alt="${ticker}" onerror="this.src='https://ui-avatars.com/api/?name=${ticker}&background=random&color=fff&size=32'">`;
}

// --- Data Fetching ---

async function fetchProfile() {
    const token = localStorage.getItem('token');
    if (!token) { window.location.href = '/static/login.html'; return; }

    try {
        const response = await fetch(`${API_BASE}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.status === 401) {
            // Valid token check failed
            logout();
            return;
        }
        currentUser = await response.json();
        renderUserUI();
    } catch (e) {
        console.error("Profile fetch error:", e);
    }
}

function renderUserUI() {
    if (!currentUser) return;
    const authContainer = document.getElementById('auth-action');
    if (authContainer) {
        authContainer.innerHTML = `
            <button class="user-profile-pill" onclick="showPage('profile')">
                <img src="https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${currentUser.avatar_id || currentUser.username}" alt="Avatar">
                <span id="nav-username">${currentUser.username}</span>
            </button>
        `;
    }
}

async function fetchAgents() {
    console.log("Fetching agents...");
    const token = localStorage.getItem('token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    try {
        const response = await fetch(`${API_BASE}/agents/`, {
            headers: headers
        });
        const agents = await response.json();
        console.log("Agents received:", agents);

        if (Array.isArray(agents)) {
            renderLeaderboard(agents);       // Sidebar
            renderGlobalLeaderboard(agents); // Full Page View
        } else {
            console.error("Agents response is not an array:", agents);
        }

        if (selectedAgentId) fetchAgentDetails(selectedAgentId);
    } catch (error) {
        console.error('Error fetching agents:', error);
    }
}

async function fetchMyAgents() {
    console.log("Fetching my agents...");
    const token = localStorage.getItem('token');
    try {
        const response = await fetch(`${API_BASE}/agents/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const agents = await response.json();
        console.log("My agents received:", agents);
        if (Array.isArray(agents)) {
            renderMyAgentsGrid(agents);
            // Update Profile Stat for Agent Count
            const countEl = document.getElementById('profile-agent-count');
            if (countEl) countEl.innerText = agents.length;
        }
    } catch (error) {
        console.error('Error fetching my agents:', error);
    }
}

// --- Rendering Logic ---

function renderLeaderboard(agents) {
    const container = document.getElementById('leaderboard-body');
    container.innerHTML = '';
    agents.sort((a, b) => (b.portfolio?.total_equity || 0) - (a.portfolio?.total_equity || 0));

    agents.slice(0, 10).forEach((agent, index) => {
        const div = document.createElement('div');
        div.className = `agent-card ${agent.id === selectedAgentId ? 'active' : ''}`;
        div.onclick = () => { selectAgent(agent.id); showPage('dashboard'); };

        const equity = agent.portfolio ? agent.portfolio.total_equity : 10000;
        const pnl = equity - 10000;
        const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';

        div.innerHTML = `
            <div class="agent-rank">${index + 1}</div>
            <div class="agent-info">
                <div class="agent-name">${agent.name}</div>
                <div class="agent-pnl ${pnlClass}">${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString(undefined, { minimumFractionDigits: 0 })}</div>
            </div>
        `;
        container.appendChild(div);
    });
}

function renderGlobalLeaderboard(agents) {
    const tbody = document.getElementById('leaderboard-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';

    agents.forEach((agent, index) => {
        const equity = agent.portfolio ? agent.portfolio.total_equity : 10000;
        const pnl = equity - 10000;
        const change = (pnl / 10000) * 100;

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>#${index + 1}</td>
            <td><strong onclick="openPublicProfile('${agent.owner_username || 'AlphaBot'}')" style="cursor: pointer; border-bottom: 1px dotted var(--text-tertiary);">${agent.name}</strong></td>
            <td><span onclick="openPublicProfile('${agent.owner_username || 'AlphaBot'}')" style="cursor: pointer; color: var(--text-secondary); transition: color 0.2s;" onmouseover="this.style.color='var(--accent-primary)'" onmouseout="this.style.color='var(--text-secondary)'">@${agent.owner_username || 'AlphaBot'}</span></td>
            <td>$${equity.toLocaleString()}</td>
            <td class="${pnl >= 0 ? 'text-success' : 'text-danger'}">${pnl >= 0 ? '+' : ''}${change.toFixed(2)}%</td>
            <td><button class="new-agent-btn" onclick="openPortfolioView('${agent.id}')">View Port</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderMyAgentsGrid(agents) {
    const grid = document.getElementById('my-agents-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (agents.length === 0) {
        grid.innerHTML = '<div class="card" style="grid-column: 1/-1; padding: 3rem; text-align: center; color: var(--text-tertiary);">You haven\'t launched any agents yet. Launch your first neural asset to start trading.</div>';
        return;
    }

    agents.forEach(agent => {
        const card = document.createElement('div');
        card.className = 'card agent-grid-card';
        const equity = agent.portfolio ? agent.portfolio.total_equity : 10000;
        const pnl = equity - 10000;

        card.innerHTML = `
            <div class="card-header">
                <div class="card-title">${agent.name}</div>
                <span class="badge" style="background: var(--bg-hover); font-size: 0.6rem; padding: 2px 6px; border-radius: 4px;">${agent.provider.toUpperCase()}</span>
            </div>
            <div class="kpi-value" style="font-size: 1.25rem;">$${equity.toLocaleString()}</div>
            <div class="kpi-sub ${pnl >= 0 ? 'text-success' : 'text-danger'}" style="margin-bottom: 1rem;">
                ${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString()} 
            </div>
            <button class="new-agent-btn" style="width: 100%; padding: 8px;" onclick="selectAgent('${agent.id}'); showPage('dashboard');">Manage Dashboard</button>
        `;
        grid.appendChild(card);
    });
}

function renderProfileView() {
    if (!currentUser) return;
    document.getElementById('profile-username').innerText = currentUser.username;

    // Populate Inputs
    document.getElementById('edit-firstname').value = currentUser.first_name || '';
    document.getElementById('edit-lastname').value = currentUser.last_name || '';
    document.getElementById('edit-linkedin').value = currentUser.linkedin_handle || '';
    document.getElementById('edit-twitter').value = currentUser.twitter_handle || '';

    document.getElementById('profile-avatar-large').src = `https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${currentUser.avatar_id || currentUser.username}`;

    // Render Avatar Choices
    const choiceGrid = document.getElementById('avatar-choices');
    choiceGrid.innerHTML = '';
    for (let i = 1; i <= 20; i++) { // Increased to 20 avatars as requested
        const div = document.createElement('div');
        div.className = `avatar-choice ${currentUser.avatar_id === i ? 'active' : ''}`;
        div.onclick = () => selectAvatar(i);
        div.innerHTML = `<img src="https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${i}" alt="Avatar ${i}">`;
        choiceGrid.appendChild(div);
    }
}

let pendingAvatarId = null;
function selectAvatar(id) {
    pendingAvatarId = id;
    document.querySelectorAll('.avatar-choice').forEach(c => c.classList.remove('active'));
    // Index careful check if we have 20 now
    if (document.querySelectorAll('.avatar-choice')[id - 1]) {
        document.querySelectorAll('.avatar-choice')[id - 1].classList.add('active');
    }
    document.getElementById('profile-avatar-large').src = `https://api.dicebear.com/7.x/bottts-neutral/svg?seed=${id}`;
}

async function saveProfile() {
    const token = localStorage.getItem('token');

    // Gather Data
    const data = {};
    if (pendingAvatarId !== null) data.avatar_id = pendingAvatarId;

    const fname = document.getElementById('edit-firstname').value;
    const lname = document.getElementById('edit-lastname').value;
    const linkedin = document.getElementById('edit-linkedin').value;
    const twitter = document.getElementById('edit-twitter').value;

    if (fname !== undefined) data.first_name = fname;
    if (lname !== undefined) data.last_name = lname;
    if (linkedin !== undefined) data.linkedin_handle = linkedin;
    if (twitter !== undefined) data.twitter_handle = twitter;

    try {
        const response = await fetch(`${API_BASE}/users/me`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            currentUser = await response.json(); // Update global state
            alert("Profile Updated Successfully");
            renderUserUI(); // Update header
        } else {
            alert("Failed to update profile");
        }
    } catch (e) {
        console.error(e);
        alert("Error saving profile");
    }
}

// --- Dashboard Specific Logic ---

function selectAgent(id) {
    selectedAgentId = id;
    document.getElementById('agent-context').style.display = 'flex';
    fetchAgentDetails(id);
    document.querySelectorAll('.agent-card').forEach(el => el.classList.remove('active'));
    fetchAgents();
}

async function fetchAgentDetails(id) {
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/agents/${id}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const agent = await response.json();
        renderAgentDetails(agent);
    } catch (error) {
        console.error('Error fetching agent details:', error);
    }
}

function renderAgentDetails(agent) {
    if (!agent.portfolio) return;
    document.getElementById('selected-agent-name').innerText = agent.name;
    document.getElementById('agent-provider').innerText = `Powered by ${agent.provider.toUpperCase()} | Strategy: Long/Short Equity`;

    document.getElementById('total-equity').innerText = `$${agent.portfolio.total_equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    document.getElementById('cash-balance').innerText = `$${agent.portfolio.cash_balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;

    const pnl = agent.portfolio.total_equity - 10000;
    const pnlEl = document.getElementById('total-pnl');
    pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
    pnlEl.className = `kpi-value ${pnl >= 0 ? 'text-success' : 'text-danger'}`;

    renderPortfolioTable(agent.portfolio.positions);
    renderPortfolioChart(agent.portfolio);
    renderAuditLogs(agent.audit_logs);
    renderTradeHistory(agent.trades);
}

// ... (renderPortfolioTable, renderPortfolioChart, renderAuditLogs, renderTradeHistory, triggerMarketCycle, createNewAgent stay mostly same) ...

function renderPortfolioTable(positions) {
    const tbody = document.getElementById('positions-body');
    tbody.innerHTML = '';
    if (!positions || positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 2rem; color: var(--text-tertiary);">No active positions. Agent is 100% Cash.</td></tr>';
        return;
    }
    positions.forEach(pos => {
        const tr = document.createElement('tr');
        const pnl = pos.unrealized_pnl || 0;
        const currentPrice = pos.current_price || pos.avg_cost;
        tr.innerHTML = `
            <td style="font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 0.75rem;">
                ${getTickerLogo(pos.ticker)}
                ${pos.ticker}
            </td>
            <td>${pos.quantity}</td>
            <td><span style="color: var(--text-tertiary)">$</span>${pos.avg_cost.toFixed(2)}</td>
            <td><span style="color: var(--text-tertiary)">$</span>${currentPrice.toFixed(2)}</td>
            <td><span class="${pnl >= 0 ? 'text-success' : 'text-danger'} bg-${pnl >= 0 ? 'success' : 'danger'}-subtle">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</span></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPortfolioChart(portfolio) {
    const ctx = document.getElementById('portfolioChart').getContext('2d');
    const labels = ['Cash', ...portfolio.positions.map(p => p.ticker)];
    const data = [portfolio.cash_balance, ...portfolio.positions.map(p => p.quantity * (p.current_price || p.avg_cost))];
    if (charts.portfolio) charts.portfolio.destroy();
    charts.portfolio = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ['#27272a', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'],
                borderWidth: 2, borderColor: '#0a0a0a', hoverOffset: 4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, cutout: '65%',
            plugins: { legend: { position: 'right', labels: { color: '#a1a1aa', font: { family: 'JetBrains Mono', size: 10 }, usePointStyle: true, boxWidth: 8 } } }
        }
    });
}

function renderAuditLogs(logs) {
    const container = document.getElementById('audit-logs');
    container.innerHTML = '';
    if (!logs || logs.length === 0) {
        container.innerHTML = '<div style="color: var(--text-tertiary); text-align: center; padding: 2rem;">Waiting for Neural Activity...</div>';
        return;
    }
    logs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    logs.forEach(log => {
        const div = document.createElement('div');
        div.className = 'log-entry';
        const date = new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        let thoughts = log.response?.thoughts || "Analyzing market structure...";
        let actions = log.response?.trades || [];
        const actionText = actions.length > 0
            ? actions.map(t => `<span class="${t.action === 'BUY' ? 'text-success' : 'text-danger'}">${t.action} ${t.quantity} ${t.ticker}</span>`).join(', ')
            : '<span style="color: var(--text-tertiary)">HOLD</span>';
        div.innerHTML = `
            <div class="log-meta">${date}</div>
            <div class="log-content">${thoughts}</div>
            <div class="log-actions">> DECISION: ${actionText}</div>
        `;
        container.appendChild(div);
    });
}

function renderTradeHistory(trades) {
    const container = document.getElementById('trade-history');
    container.innerHTML = '';
    if (!trades || trades.length === 0) {
        container.innerHTML = '<div style="color: var(--text-tertiary); text-align: center; padding: 2rem;">No trades yet.</div>';
        return;
    }
    trades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    trades.forEach(trade => {
        const div = document.createElement('div');
        div.className = 'log-entry';
        const date = new Date(trade.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const pnlText = trade.pnl_realized ? ` | PnL: <span class="${trade.pnl_realized >= 0 ? 'text-success' : 'text-danger'}">$${trade.pnl_realized.toFixed(2)}</span>` : '';
        div.innerHTML = `
            <div class="log-meta">${date}</div>
            <div style="color: var(--text-primary); font-weight: 500; display: flex; align-items: center; gap: 0.5rem;">
                ${getTickerLogo(trade.ticker)}
                <span class="${trade.action === 'BUY' ? 'text-success' : 'text-danger'}">${trade.action}</span> ${trade.quantity} ${trade.ticker} @ $${trade.price.toFixed(2)}
            </div>
            <div class="log-meta" style="font-size: 0.7rem; margin-top:2px;">
                Reason: ${trade.reasoning.substring(0, 100)}...${pnlText}
            </div>
        `;
        container.appendChild(div);
    });
}

async function triggerMarketCycle() {
    const btn = document.getElementById('cycle-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = 'Processing...';
    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/market/cycle`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.status === 403) alert("Admin privileges required.");
        setTimeout(fetchAgents, 1000);
    } catch (e) { console.error(e); }
    finally { setTimeout(() => { btn.disabled = false; btn.innerHTML = originalText; }, 2000); }
}

// --- Create Agent Modal Logic ---

function createNewAgent() {
    document.getElementById('new-agent-name').value = '';
    document.getElementById('new-agent-persona').value = "You are a rational profit-maximizing trader.";
    document.getElementById('create-agent-modal').style.display = 'flex';
}

function closeCreateAgentModal() {
    document.getElementById('create-agent-modal').style.display = 'none';
}

async function submitNewAgent() {
    const name = document.getElementById('new-agent-name').value;
    const persona = document.getElementById('new-agent-persona').value;

    if (!name) {
        alert("Agent Designation is required.");
        return;
    }

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${API_BASE}/agents/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name, provider: 'gemini', persona })
        });

        if (response.ok) {
            closeCreateAgentModal();
            fetchAgents();
            fetchMyAgents();
        } else {
            const err = await response.json();
            alert("Error: " + err.detail);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to create agent");
    }
}

// Initial Load
// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    // 1. Force Leaderboard View First
    showPage('leaderboard');

    // 2. Check Auth & Terms
    checkAuth();

    // 3. Start Data Loop
    fetchAgents();
    setInterval(fetchAgents, 5000);

    document.getElementById('cycle-btn')?.addEventListener('click', triggerMarketCycle);

    // Close drawer on overlay click
    document.getElementById('portfolio-drawer')?.addEventListener('click', (e) => {
        if (e.target === document.getElementById('portfolio-drawer')) {
            closePortfolioDrawer();
        }
    });
});
