<?javascript
// ADA-Pi Web Dashboard - Main Application
class AdaPiApp {
    constructor() {
        this.apiUrl = window.location.origin;
        this.wsUrl = `ws://${window.location.hostname}:9000`;
        this.ws = null;
        this.currentPage = 'dashboard';
        this.data = {};
        this.lastUpdate = 0;
        this.updateThrottle = 1000; // Only update once per second

        this.init();
    }

    init() {
        console.log('ADA-Pi Web Dashboard Starting...');
        this.setupNavigation();
        this.connectWebSocket();
        this.loadPage('dashboard');

        // Poll API every 30 seconds as backup (reduced from 5s to prevent overload)
        setInterval(() => this.refreshData(), 30000);
    }

    // Navigation
    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const page = item.dataset.page;
                this.loadPage(page);

                // Update active state
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }

    loadPage(page) {
        this.currentPage = page;
        const content = document.getElementById('content');

        switch(page) {
            case 'dashboard':
                content.innerHTML = this.renderDashboard();
                break;
            case 'gps':
                content.innerHTML = this.renderGPS();
                break;
            case 'obd':
                content.innerHTML = this.renderOBD();
                break;
            case 'system':
                content.innerHTML = this.renderSystem();
                break;
            case 'ups':
                content.innerHTML = this.renderUPS();
                break;
            case 'network':
                content.innerHTML = this.renderNetwork();
                break;
            case 'modem':
                content.innerHTML = this.renderModem();
                break;
            case 'bluetooth':
                content.innerHTML = this.renderBluetooth();
                break;
            case 'tacho':
                content.innerHTML = this.renderTacho();
                break;
            case 'logs':
                content.innerHTML = this.renderLogs();
                this.loadLogs();
                break;
            case 'settings':
                content.innerHTML = this.renderSettings();
                break;
        }

        // Initial data load only when page first loads
        if (!this.data[page]) {
            this.refreshData();
        }
    }

    // WebSocket Connection
    connectWebSocket() {
        console.log('Connecting to WebSocket:', this.wsUrl);

        this.ws = new WebSocket(this.wsUrl);

        this.ws.onopen = () => {
            console.log('✓ WebSocket connected successfully');
            this.updateConnectionStatus(true);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log('WebSocket received:', message);
                this.handleWebSocketMessage(message);
            } catch(e) {
                console.error('WebSocket message parse error:', e, 'Raw:', event.data);
            }
        };

        this.ws.onerror = (error) => {
            console.error('✗ WebSocket error:', error);
            this.updateConnectionStatus(false);
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed, will reconnect in 3 seconds...');
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }

    handleWebSocketMessage(message) {
        const { event, payload } = message;

        // Map WebSocket events to data keys that match the render functions
        const eventMapping = {
            'gps_update': 'gps',
            'system_update': 'system',
            'ups_update': 'ups',
            'network_update': 'network',
            'modem_update': 'modem',
            'obd_update': 'obd',
            'bt_update': 'bluetooth',
            'bluetooth_update': 'bluetooth',
            'tacho_update': 'tacho',
            'fan_update': 'fan',
            'logs_update': 'logs'
        };

        // Store data with the correct key
        if (event && eventMapping[event]) {
            this.data[eventMapping[event]] = payload;
            console.log(`WebSocket: ${event} →`, payload);
        } else if (event) {
            // Store with original event name if no mapping exists
            this.data[event] = payload;
            console.log(`WebSocket: ${event} (unmapped) →`, payload);
        }

        // Throttled update - only update once per second max
        const now = Date.now();
        if (now - this.lastUpdate > this.updateThrottle) {
            this.lastUpdate = now;
            this.updateCurrentPage();
        }
    }

    updateConnectionStatus(connected) {
        const dot = document.getElementById('statusDot');
        const text = document.getElementById('statusText');

        if (connected) {
            dot.classList.add('connected');
            text.textContent = 'Connected';
        } else {
            dot.classList.remove('connected');
            text.textContent = 'Disconnected';
        }
    }

    // API Calls
    async apiGet(endpoint) {
        try {
            console.log(`API GET: ${endpoint}`);
            const response = await fetch(`${this.apiUrl}${endpoint}`);
            const data = await response.json();
            console.log(`API GET ${endpoint} →`, data);
            return data;
        } catch(e) {
            console.error('API GET error:', endpoint, e);
            return null;
        }
    }

    async apiPost(endpoint, data) {
        try {
            const response = await fetch(`${this.apiUrl}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch(e) {
            console.error('API POST error:', endpoint, e);
            return null;
        }
    }

    async refreshData() {
        // Fetch data based on current page
        switch(this.currentPage) {
            case 'dashboard':
                await Promise.all([
                    this.fetchSystemInfo(),
                    this.fetchGPS(),
                    this.fetchUPS(),
                    this.fetchNetwork()
                ]);
                break;
            case 'gps':
                await this.fetchGPS();
                break;
            case 'system':
                await this.fetchSystemInfo();
                break;
            case 'ups':
                await this.fetchUPS();
                break;
            case 'network':
                await this.fetchNetwork();
                break;
            case 'modem':
                await this.fetchModem();
                break;
            case 'bluetooth':
                await this.fetchBluetooth();
                break;
            case 'tacho':
                await this.fetchTacho();
                break;
            case 'obd':
                await this.fetchOBD();
                break;
            case 'logs':
                await this.loadLogs();
                break;
        }

        this.updateCurrentPage();
    }

    async fetchSystemInfo() {
        const data = await this.apiGet('/api/system/info');
        if (data) this.data.system = data.data;
    }

    async fetchGPS() {
        const data = await this.apiGet('/api/gps');
        if (data) this.data.gps = data.data;
    }

    async fetchUPS() {
        const data = await this.apiGet('/api/ups');
        if (data) this.data.ups = data.data;
    }

    async fetchNetwork() {
        const data = await this.apiGet('/api/network');
        if (data) this.data.network = data.data;
    }

    async fetchModem() {
        const data = await this.apiGet('/api/modem');
        if (data) this.data.modem = data.data;
    }

    async fetchBluetooth() {
        const data = await this.apiGet('/api/bluetooth');
        if (data) this.data.bluetooth = data.data;
    }

    async fetchTacho() {
        const data = await this.apiGet('/api/tacho');
        if (data) this.data.tacho = data.data;
    }

    async fetchOBD() {
        const data = await this.apiGet('/api/obd');
        if (data) this.data.obd = data.data;
    }

    async loadLogs() {
        const data = await this.apiGet('/api/logs/recent?limit=100');
        if (data && data.data) {
            this.renderLogsTable(data.data);
        }
    }

    updateCurrentPage() {
    // Re-render current page with updated data WITHOUT calling loadPage
    const content = document.getElementById('content');
    const scrollPosition = content.scrollTop;

    // Render directly based on current page
    switch(this.currentPage) {
        case 'dashboard':
            content.innerHTML = this.renderDashboard();
            break;
        case 'gps':
            content.innerHTML = this.renderGPS();
            break;
        case 'obd':
            content.innerHTML = this.renderOBD();
            break;
        case 'system':
            content.innerHTML = this.renderSystem();
            break;
        case 'ups':
            content.innerHTML = this.renderUPS();
            break;
        case 'network':
            content.innerHTML = this.renderNetwork();
            break;
        case 'modem':
            content.innerHTML = this.renderModem();
            break;
        case 'bluetooth':
            content.innerHTML = this.renderBluetooth();
            break;
        case 'tacho':
            content.innerHTML = this.renderTacho();
            break;
        case 'logs':
            content.innerHTML = this.renderLogs();
            this.loadLogs();
            break;
        case 'settings':
            content.innerHTML = this.renderSettings();
            break;
         }

        content.scrollTop = scrollPosition;
    }

    // Page Renderers
    renderDashboard() {
        const system = this.data.system || {};
        const gps = this.data.gps || {};
        const ups = this.data.ups || {};
        const network = this.data.network || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Dashboard</h1>
                <p class="page-subtitle">System Overview</p>
            </div>

            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="card-header">
                        <span class="card-icon">🗺️</span>
                        <span class="card-title">GPS</span>
                    </div>
                    <div class="stat-value text-primary">${gps.speed || 0} km/h</div>
                    <div class="stat-label">${gps.satellites || 0} satellites</div>
                </div>

                <div class="stat-card">
                    <div class="card-header">
                        <span class="card-icon">🔋</span>
                        <span class="card-title">Battery</span>
                    </div>
                    <div class="stat-value ${this.getBatteryColor(ups.battery_percent)}">${ups.battery_percent || 0}%</div>
                    <div class="stat-label">${ups.charging ? 'Charging' : 'Discharging'}</div>
                </div>

                <div class="stat-card">
                    <div class="card-header">
                        <span class="card-icon">💻</span>
                        <span class="card-title">CPU</span>
                    </div>
                    <div class="stat-value text-info">${(system.cpu?.usage || 0).toFixed(1)}%</div>
                    <div class="stat-label">${(system.cpu?.temp || 0).toFixed(1)}°C</div>
                </div>
            </div>

            <div class="grid grid-2">
                <div class="card">
                    <h3 class="card-title mb-2">System Resources</h3>
                    <div class="mb-2">
                        <div class="flex-between mb-1">
                            <span>CPU Usage</span>
                            <span>${(system.cpu?.usage || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${system.cpu?.usage || 0}%"></div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="flex-between mb-1">
                            <span>Memory</span>
                            <span>${(system.memory?.percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${system.memory?.percent || 0}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex-between mb-1">
                            <span>Disk</span>
                            <span>${(system.disk?.percent || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${system.disk?.percent || 0}%"></div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3 class="card-title mb-2">Network Status</h3>
                    <div class="flex-between mb-2">
                        <span>Status</span>
                        <span class="badge ${network.connected ? 'badge-success' : 'badge-error'}">
                            ${network.connected ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                    <div class="flex-between mb-2">
                        <span>IP Address</span>
                        <span>${network.ip || 'N/A'}</span>
                    </div>
                    <div class="flex-between">
                        <span>Interface</span>
                        <span>${network.interface || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;
    }

    renderGPS() {
        const gps = this.data.gps || {};

        return `
            <div class="page-header">
                <h1 class="page-title">GPS Tracker</h1>
                <p class="page-subtitle">Real-time location and speed data</p>
            </div>

            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Speed</div>
                    <div class="stat-value text-primary">${gps.speed || 0} km/h</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Satellites</div>
                    <div class="stat-value text-info">${gps.satellites || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Altitude</div>
                    <div class="stat-value text-success">${gps.altitude || 0} m</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">HDOP</div>
                    <div class="stat-value">${gps.hdop || 0}</div>
                </div>
            </div>

            <div class="card mb-3">
                <h3 class="card-title mb-2">Position</h3>
                <div class="grid grid-2">
                    <div>
                        <div class="stat-label">Latitude</div>
                        <div class="stat-value">${gps.latitude || 0}</div>
                    </div>
                    <div>
                        <div class="stat-label">Longitude</div>
                        <div class="stat-value">${gps.longitude || 0}</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">GPS Details</h3>
                <table class="table">
                    <tr>
                        <td>Fix Quality</td>
                        <td><span class="badge ${gps.fix ? 'badge-success' : 'badge-error'}">${gps.fix ? 'Fixed' : 'No Fix'}</sp
an></td>
                    </tr>
                    <tr>
                        <td>Heading</td>
                        <td>${gps.heading || 0}°</td>
                    </tr>
                    <tr>
                        <td>Timestamp</td>
                        <td>${gps.timestamp || 'N/A'}</td>
                    </tr>
                </table>
            </div>
        `;
    }

    renderSystem() {
        const system = this.data.system || {};

        return `
            <div class="page-header">
                <h1 class="page-title">System Information</h1>
                <p class="page-subtitle">Hardware and software status</p>
            </div>

            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">CPU Usage</div>
                    <div class="stat-value text-primary">${(system.cpu?.usage || 0).toFixed(1)}%</div>
                    <div class="stat-label">${(system.cpu?.temp || 0).toFixed(1)}°C</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Memory</div>
                    <div class="stat-value text-info">${(system.memory?.percent || 0).toFixed(1)}%</div>
                    <div class="stat-label">${this.formatBytes(system.memory?.used || 0)} / ${this.formatBytes(system.memory?.to
tal || 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Disk</div>
                    <div class="stat-value text-warning">${(system.disk?.percent || 0).toFixed(1)}%</div>
                    <div class="stat-label">${this.formatBytes(system.disk?.used || 0)} / ${this.formatBytes(system.disk?.total
|| 0)}</div>
                </div>
            </div>

            <div class="card mb-3">
                <h3 class="card-title mb-2">System Details</h3>
                <table class="table">
                    <tr>
...
    getLogLevelColor(level) {
        switch(level.toLowerCase()) {
            case 'error': return 'error';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return 'info';
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adaPi = new AdaPiApp();
});
