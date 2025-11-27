// ADA-Pi Web Dashboard - Main Application
class AdaPiApp {
    constructor() {
        this.apiUrl = window.location.origin;
        this.wsUrl = `ws://${window.location.hostname}:9000`;
        this.ws = null;
        this.currentPage = 'dashboard';
        this.data = {};
        
        this.init();
    }
    
    init() {
        console.log('ADA-Pi Web Dashboard Starting...');
        this.setupNavigation();
        this.connectWebSocket();
        this.loadPage('dashboard');
        
        // Poll API every 10 seconds as backup
        setInterval(() => this.refreshData(), 10000);
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
        
        // Refresh data for current page
        this.refreshData();
    }
    
    // WebSocket Connection
    connectWebSocket() {
        console.log('Connecting to WebSocket:', this.wsUrl);
        
        this.ws = new WebSocket(this.wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };
        
        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            } catch(e) {
                console.error('WebSocket message parse error:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed, reconnecting...');
            this.updateConnectionStatus(false);
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    handleWebSocketMessage(message) {
        const { event, payload } = message;
        
        // Store data
        if (event) {
            this.data[event] = payload;
        }
        
        // Update current page if relevant
        this.updateCurrentPage();
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
            const response = await fetch(`${this.apiUrl}${endpoint}`);
            return await response.json();
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
            case 'obd':
                await this.fetchOBD();
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
        // Re-render current page with updated data
        const content = document.getElementById('content');
        const scrollPosition = content.scrollTop;
        
        this.loadPage(this.currentPage);
        
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
                        <td><span class="badge ${gps.fix ? 'badge-success' : 'badge-error'}">${gps.fix ? 'Fixed' : 'No Fix'}</span></td>
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
                    <div class="stat-label">${this.formatBytes(system.memory?.used || 0)} / ${this.formatBytes(system.memory?.total || 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Disk</div>
                    <div class="stat-value text-warning">${(system.disk?.percent || 0).toFixed(1)}%</div>
                    <div class="stat-label">${this.formatBytes(system.disk?.used || 0)} / ${this.formatBytes(system.disk?.total || 0)}</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">System Details</h3>
                <table class="table">
                    <tr>
                        <td>OS Version</td>
                        <td>${system.os_version || 'Unknown'}</td>
                    </tr>
                    <tr>
                        <td>Kernel</td>
                        <td>${system.kernel || 'Unknown'}</td>
                    </tr>
                    <tr>
                        <td>Uptime</td>
                        <td>${this.formatUptime(system.uptime || 0)}</td>
                    </tr>
                    <tr>
                        <td>Load Average</td>
                        <td>${(system.load || [0,0,0]).join(', ')}</td>
                    </tr>
                </table>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Temperature</h3>
                <div class="grid grid-2">
                    <div>
                        <div class="stat-label">CPU</div>
                        <div class="stat-value ${this.getTempColor(system.cpu?.temp)}">${(system.cpu?.temp || 0).toFixed(1)}°C</div>
                    </div>
                    <div>
                        <div class="stat-label">GPU</div>
                        <div class="stat-value ${this.getTempColor(system.gpu?.temp)}">${(system.gpu?.temp || 0).toFixed(1)}°C</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderUPS() {
        const ups = this.data.ups || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">UPS Monitor</h1>
                <p class="page-subtitle">Battery and power status</p>
            </div>
            
            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Battery Level</div>
                    <div class="stat-value ${this.getBatteryColor(ups.battery_percent)}">${ups.battery_percent || 0}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Voltage</div>
                    <div class="stat-value text-info">${(ups.voltage || 0).toFixed(2)}V</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Current</div>
                    <div class="stat-value text-primary">${(ups.current || 0).toFixed(2)}A</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Battery Status</h3>
                <div class="progress mb-2" style="height: 30px;">
                    <div class="progress-bar" style="width: ${ups.battery_percent || 0}%"></div>
                </div>
                <div class="flex-between">
                    <span>Status</span>
                    <span class="badge ${ups.charging ? 'badge-success' : 'badge-warning'}">
                        ${ups.charging ? 'Charging' : 'Discharging'}
                    </span>
                </div>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Power Details</h3>
                <table class="table">
                    <tr>
                        <td>Power</td>
                        <td>${(ups.power || 0).toFixed(2)}W</td>
                    </tr>
                    <tr>
                        <td>Capacity</td>
                        <td>${ups.capacity || 0} mAh</td>
                    </tr>
                    <tr>
                        <td>External Power</td>
                        <td><span class="badge ${ups.external_power ? 'badge-success' : 'badge-error'}">${ups.external_power ? 'Connected' : 'Disconnected'}</span></td>
                    </tr>
                </table>
            </div>
        `;
    }
    
    renderNetwork() {
        const network = this.data.network || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">Network</h1>
                <p class="page-subtitle">Network connectivity and interfaces</p>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Connection Status</h3>
                <table class="table">
                    <tr>
                        <td>Status</td>
                        <td><span class="badge ${network.connected ? 'badge-success' : 'badge-error'}">${network.connected ? 'Connected' : 'Disconnected'}</span></td>
                    </tr>
                    <tr>
                        <td>IP Address</td>
                        <td>${network.ip || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Interface</td>
                        <td>${network.interface || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Subnet Mask</td>
                        <td>${network.netmask || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Gateway</td>
                        <td>${network.gateway || 'N/A'}</td>
                    </tr>
                </table>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Network Statistics</h3>
                <div class="grid grid-2">
                    <div>
                        <div class="stat-label">Bytes Sent</div>
                        <div class="stat-value text-primary">${this.formatBytes(network.bytes_sent || 0)}</div>
                    </div>
                    <div>
                        <div class="stat-label">Bytes Received</div>
                        <div class="stat-value text-info">${this.formatBytes(network.bytes_recv || 0)}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderModem() {
        const modem = this.data.modem || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">Modem</h1>
                <p class="page-subtitle">Cellular modem status</p>
            </div>
            
            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Signal Strength</div>
                    <div class="stat-value text-success">${modem.signal_strength || 0}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Network</div>
                    <div class="stat-value text-info">${modem.network_type || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Operator</div>
                    <div class="stat-value">${modem.operator || 'N/A'}</div>
                </div>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Modem Details</h3>
                <table class="table">
                    <tr>
                        <td>Status</td>
                        <td><span class="badge ${modem.connected ? 'badge-success' : 'badge-error'}">${modem.connected ? 'Connected' : 'Disconnected'}</span></td>
                    </tr>
                    <tr>
                        <td>IMEI</td>
                        <td>${modem.imei || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>IP Address</td>
                        <td>${modem.ip || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>APN</td>
                        <td>${modem.apn || 'N/A'}</td>
                    </tr>
                </table>
            </div>
        `;
    }
    
    renderBluetooth() {
        return `
            <div class="page-header">
                <h1 class="page-title">Bluetooth</h1>
                <p class="page-subtitle">Bluetooth devices and connections</p>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Bluetooth Status</h3>
                <p class="text-center" style="padding: 40px;">Bluetooth management coming soon...</p>
            </div>
        `;
    }
    
    renderOBD() {
        const obd = this.data.obd || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">OBD Diagnostics</h1>
                <p class="page-subtitle">Vehicle diagnostic data</p>
            </div>
            
            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">RPM</div>
                    <div class="stat-value text-primary">${obd.rpm || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Speed</div>
                    <div class="stat-value text-info">${obd.speed || 0} km/h</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Coolant Temp</div>
                    <div class="stat-value ${this.getTempColor(obd.coolant_temp)}">${obd.coolant_temp || 0}°C</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Throttle</div>
                    <div class="stat-value text-success">${obd.throttle || 0}%</div>
                </div>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Vehicle Status</h3>
                <table class="table">
                    <tr>
                        <td>Engine Load</td>
                        <td>${obd.engine_load || 0}%</td>
                    </tr>
                    <tr>
                        <td>Fuel Level</td>
                        <td>${obd.fuel_level || 0}%</td>
                    </tr>
                    <tr>
                        <td>Intake Temp</td>
                        <td>${obd.intake_temp || 0}°C</td>
                    </tr>
                    <tr>
                        <td>Connected</td>
                        <td><span class="badge ${obd.connected ? 'badge-success' : 'badge-error'}">${obd.connected ? 'Yes' : 'No'}</span></td>
                    </tr>
                </table>
            </div>
        `;
    }
    
    renderTacho() {
        return `
            <div class="page-header">
                <h1 class="page-title">Tachograph</h1>
                <p class="page-subtitle">Driver hours and compliance</p>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Tachograph Data</h3>
                <p class="text-center" style="padding: 40px;">Tachograph data coming soon...</p>
            </div>
        `;
    }
    
    renderLogs() {
        return `
            <div class="page-header">
                <h1 class="page-title">System Logs</h1>
                <p class="page-subtitle">Recent system events and logs</p>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Recent Logs</h3>
                <div id="logsTable">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading logs...</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    renderLogsTable(logs) {
        const table = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Level</th>
                        <th>Module</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs.map(log => `
                        <tr>
                            <td>${log.timestamp}</td>
                            <td><span class="badge badge-${this.getLogLevelColor(log.level)}">${log.level}</span></td>
                            <td>${log.module}</td>
                            <td>${log.message}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        
        document.getElementById('logsTable').innerHTML = table;
    }
    
    renderSettings() {
        return `
            <div class="page-header">
                <h1 class="page-title">Settings</h1>
                <p class="page-subtitle">System configuration</p>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Configuration</h3>
                <p class="text-center" style="padding: 40px;">Settings panel coming soon...</p>
            </div>
        `;
    }
    
    // Helper Functions
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
    }
    
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${days}d ${hours}h ${minutes}m`;
    }
    
    getBatteryColor(percent) {
        if (percent > 50) return 'text-success';
        if (percent > 20) return 'text-warning';
        return 'text-error';
    }
    
    getTempColor(temp) {
        if (temp < 60) return 'text-success';
        if (temp < 75) return 'text-warning';
        return 'text-error';
    }
    
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
