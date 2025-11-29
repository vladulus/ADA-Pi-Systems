// ADA-Pi Web Dashboard - Main Application (adasystems.uk Auth)
class AdaPiApp {
    constructor() {
        this.apiUrl = window.location.origin;
        this.wsUrl = `ws://${window.location.hostname}:9000`;
        this.ws = null;
        this.currentPage = 'dashboard';
        this.data = {};
        this.lastUpdate = 0;
        this.updateThrottle = 500; // Update every 500ms
        this.settings = {}; // Store settings
        
        // External authentication via adasystems.uk
        this.authApiUrl = 'https://www.adasystems.uk/api';
        this.jwtToken = sessionStorage.getItem('ada_pi_token');
        this.userData = null;
        this.isAuthenticated = false; // Always false until validateToken() runs
     
        this.init();
    }
    
    async init() {
        console.log('ADA-Pi Web Dashboard Starting...');
        
        // Validate existing token if present
        if (this.jwtToken) {
            const isValid = await this.validateToken();
            if (isValid) {
                this.isAuthenticated = true;
                this.userData = JSON.parse(sessionStorage.getItem('ada_pi_user') || "null");
            }else{
                this.jwtToken = null;
                this.userData = null;
                this.isAuthenticated = false;
                sessionStorage.removeItem('ada_pi_token');
                sessionStorage.removeItem('ada_pi_user');
            } 
        }
        
        this.setupNavigation();
        this.connectWebSocket();
        this.loadPage('dashboard');
        
        // Initial data load
        if (this.isAuthenticated) {
            this.refreshAllData();
        }
        
        // Poll API every 10 seconds as backup
        setInterval(() => {
            if (this.isAuthenticated) {
                this.refreshAllData();
            }
        }, 10000);
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
        
        // Check if authenticated - if not, show login screen
        if (!this.isAuthenticated) {
            content.innerHTML = this.renderLogin();
            return;
        }
        
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
                this.setupSettingsHandlers();
                this.loadSettings();
                break;
        }
        
        // Load data for current page
        this.refreshCurrentPageData();
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
                this.handleWebSocketMessage(message);
            } catch(e) {
                console.error('WebSocket message parse error:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('✗ WebSocket error:', error);
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
        
        // Map WebSocket events to data keys
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
        
        if (event && eventMapping[event]) {
            this.data[eventMapping[event]] = payload;
            console.log(`WS: ${event} →`, payload);
        }
        
        // Throttled update
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
    
    // API Calls to Pi Backend
    async apiGet(endpoint) {
        try {
            const headers = {};
            if (this.jwtToken) {
                headers['Authorization'] = `Bearer ${this.jwtToken}`;
            }
            
            const response = await fetch(`${this.apiUrl}${endpoint}`, { headers });
            
            if (response.status === 401) {
                console.log('401 Unauthorized - token expired or invalid');

                // Fully clear session
                this.jwtToken = null;
                this.userData = null;
                this.isAuthenticated = false;
                sessionStorage.removeItem('ada_pi_token');
                sessionStorage.removeItem('ada_pi_user');

                // Redirect to login (load dashboard → login will show)
                this.loadPage('dashboard');

                return null;

            }
            
            const data = await response.json();
            return data;
        } catch(e) {
            console.error('API GET error:', endpoint, e);
            return null;
        }
    }
    
    async apiPost(endpoint, data) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (this.jwtToken) {
                headers['Authorization'] = `Bearer ${this.jwtToken}`;
            }
            
            const response = await fetch(`${this.apiUrl}${endpoint}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(data)
            });
            
            if (response.status === 401) {
                console.log('401 Unauthorized - token expired or invalid');

                // Fully clear session
                this.jwtToken = null;
                this.userData = null;
                this.isAuthenticated = false;
                sessionStorage.removeItem('ada_pi_token');
                sessionStorage.removeItem('ada_pi_user');

                // Redirect to login (load dashboard → login will show)
                this.loadPage('dashboard');

                return null;

            }
            
            return await response.json();
        } catch(e) {
            console.error('API POST error:', endpoint, e);
            return null;
        }
    }
    
    async refreshAllData() {
        await Promise.all([
            this.fetchSystemInfo(),
            this.fetchGPS(),
            this.fetchUPS(),
            this.fetchNetwork(),
            this.fetchModem(),
            this.fetchBluetooth(),
            this.fetchTacho(),
            this.fetchOBD()
        ]);
        this.updateCurrentPage();
    }
    
    async refreshCurrentPageData() {
        switch(this.currentPage) {
            case 'dashboard':
                await this.refreshAllData();
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
            case 'settings':
                await this.loadSettings();
                break;
        }
        this.updateCurrentPage();
    }
    
    async fetchSystemInfo() {
        const data = await this.apiGet('/api/system/info');
        if (data && data.data) this.data.system = data.data;
    }
    
    async fetchGPS() {
        const data = await this.apiGet('/api/gps');
        if (data && data.data) this.data.gps = data.data;
    }
    
    async fetchUPS() {
        const data = await this.apiGet('/api/ups');
        if (data && data.data) this.data.ups = data.data;
    }
    
    async fetchNetwork() {
        const data = await this.apiGet('/api/network');
        if (data && data.data) this.data.network = data.data;
    }

    async fetchModem() {
        const data = await this.apiGet('/api/modem');
        if (data && data.data) this.data.modem = data.data;
    }

    async fetchBluetooth() {
        const data = await this.apiGet('/api/bluetooth');
        if (data && data.data) this.data.bluetooth = data.data;
    }

    async fetchTacho() {
        const data = await this.apiGet('/api/tacho');
        if (data && data.data) this.data.tacho = data.data;
    }

    async fetchOBD() {
        const data = await this.apiGet('/api/obd');
        if (data && data.data) this.data.obd = data.data;
    }
    
    async loadLogs() {
        const data = await this.apiGet('/api/logs/live');
        if (data && data.data && data.data.recent) {
            this.renderLogsTable(data.data.recent);
        }
    }
    
    async loadSettings() {
        const data = await this.apiGet('/api/settings');
        if (data && data.data) {
            this.settings = data.data;
            this.populateSettings();
        }
    }
    
    updateCurrentPage() {
        const content = document.getElementById('content');
        const scrollPosition = content.scrollTop;
        
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
                // Don't re-render logs page
                break;
            case 'settings':
                // Don't re-render settings page
                break;
        }
        
        content.scrollTop = scrollPosition;
    }
    
    // Page Renderers
    renderLogin() {
        return `
            <div class="page-header">
                <h1 class="page-title">🔐 ADA-Pi Dashboard Login</h1>
                <p class="page-subtitle">Authenticate via ADA Systems</p>
            </div>
            
            <div class="card" style="max-width: 500px; margin: 0 auto;">
                <h3 class="card-title mb-2">Login Required</h3>
                <p class="text-muted mb-3">Enter your ADA Systems credentials to access this dashboard</p>
                
                <div class="mb-2">
                    <label class="stat-label">Username or Email</label>
                    <input type="text" id="loginUsername" class="form-input" placeholder="Enter username or email" autocomplete="username" onkeypress="if(event.key==='Enter') window.adaPi.handleLogin()">
                </div>
                
                <div class="mb-3">
                    <label class="stat-label">Password</label>
                    <input type="password" id="loginPassword" class="form-input" placeholder="Enter password" autocomplete="current-password" onkeypress="if(event.key==='Enter') window.adaPi.handleLogin()">
                </div>
                
                <div id="loginError" class="text-error mb-2" style="display: none;"></div>
                
                <button class="btn btn-primary" onclick="window.adaPi.handleLogin()" style="width: 100%;">
                    Login
                </button>
                
                <p class="text-muted mt-3" style="font-size: 13px; text-align: center;">
                    🔒 Secure authentication via www.adasystems.uk
                </p>
            </div>
            
            <style>
                .form-input {
                    width: 100%;
                    padding: 10px;
                    background: var(--bg-light);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    color: var(--text);
                    font-size: var(--font-base);
                    margin-bottom: 8px;
                }
                .form-input:focus {
                    outline: none;
                    border-color: var(--primary);
                }
            </style>
        `;
    }
    
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
                    <div class="stat-value text-primary">${gps.speed || 0} ${gps.unit || 'km/h'}</div>
                    <div class="stat-label">${gps.satellites || 0} satellites • ${gps.fix ? 'Fixed' : 'No Fix'}</div>
                </div>
                
                <div class="stat-card">
                    <div class="card-header">
                        <span class="card-icon">🔋</span>
                        <span class="card-title">Battery</span>
                    </div>
                    <div class="stat-value ${this.getBatteryColor(ups.percent)}">${ups.percent || 0}%</div>
                    <div class="stat-label">${ups.charging ? '⚡ Charging' : '🔌 Discharging'} • ${(ups.voltage || 0).toFixed(2)}V</div>
                </div>
                
                <div class="stat-card">
                    <div class="card-header">
                        <span class="card-icon">💻</span>
                        <span class="card-title">CPU</span>
                    </div>
                    <div class="stat-value text-info">${((system.cpu && system.cpu.usage) || 0).toFixed(1)}%</div>
                    <div class="stat-label">${((system.cpu && system.cpu.temp) || 0).toFixed(1)}°C</div>
                </div>
            </div>
            
            <div class="grid grid-2">
                <div class="card">
                    <h3 class="card-title mb-2">System Resources</h3>
                    <div class="mb-2">
                        <div class="flex-between mb-1">
                            <span>CPU Usage</span>
                            <span>${((system.cpu && system.cpu.usage) || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${(system.cpu && system.cpu.usage) || 0}%"></div>
                        </div>
                    </div>
                    <div class="mb-2">
                        <div class="flex-between mb-1">
                            <span>Memory</span>
                            <span>${((system.memory && system.memory.percent) || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${(system.memory && system.memory.percent) || 0}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex-between mb-1">
                            <span>Disk</span>
                            <span>${((system.disk && system.disk.percent) || 0).toFixed(1)}%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" style="width: ${(system.disk && system.disk.percent) || 0}%"></div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3 class="card-title mb-2">Network Status</h3>
                    <div class="flex-between mb-2">
                        <span>Active Interface</span>
                        <span class="badge ${network.active !== 'none' ? 'badge-success' : 'badge-error'}">
                            ${network.active || 'None'}
                        </span>
                    </div>
                    <div class="flex-between mb-2">
                        <span>IP Address</span>
                        <span>${network.ip || 'N/A'}</span>
                    </div>
                    ${network.wifi && network.wifi.connected ? `
                    <div class="flex-between">
                        <span>WiFi SSID</span>
                        <span>${network.wifi.ssid || 'N/A'}</span>
                    </div>
                    ` : ''}
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
                    <div class="stat-value text-primary">${gps.speed || 0} ${gps.unit || 'km/h'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Satellites</div>
                    <div class="stat-value text-info">${gps.satellites || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Altitude</div>
                    <div class="stat-value text-success">${(gps.altitude || 0).toFixed(1)} m</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">HDOP</div>
                    <div class="stat-value">${(gps.hdop || 0).toFixed(2)}</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Position</h3>
                <div class="grid grid-2">
                    <div>
                        <div class="stat-label">Latitude</div>
                        <div class="stat-value">${(gps.latitude || 0).toFixed(6)}</div>
                    </div>
                    <div>
                        <div class="stat-label">Longitude</div>
                        <div class="stat-value">${(gps.longitude || 0).toFixed(6)}</div>
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
                        <td>${(gps.heading || 0).toFixed(1)}°</td>
                    </tr>
                    <tr>
                        <td>Unit Mode</td>
                        <td>${gps.unit || 'km/h'}</td>
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
        const cpu = system.cpu || {};
        const memory = system.memory || {};
        const disk = system.disk || {};
        const gpu = system.gpu || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">System Information</h1>
                <p class="page-subtitle">Hardware and software status</p>
            </div>
            
            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">CPU Usage</div>
                    <div class="stat-value text-primary">${(cpu.usage || 0).toFixed(1)}%</div>
                    <div class="stat-label">${(cpu.temp || 0).toFixed(1)}°C • ${cpu.freq || 0} MHz</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Memory</div>
                    <div class="stat-value text-info">${(memory.percent || 0).toFixed(1)}%</div>
                    <div class="stat-label">${this.formatBytes(memory.used || 0)} / ${this.formatBytes(memory.total || 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Disk</div>
                    <div class="stat-value text-warning">${(disk.percent || 0).toFixed(1)}%</div>
                    <div class="stat-label">${this.formatBytes(disk.used || 0)} / ${this.formatBytes(disk.total || 0)}</div>
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
                    <tr>
                        <td>Throttled</td>
                        <td><span class="badge ${system.throttled ? 'badge-warning' : 'badge-success'}">${system.throttled ? 'Yes' : 'No'}</span></td>
                    </tr>
                </table>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Temperature</h3>
                <div class="grid grid-2">
                    <div>
                        <div class="stat-label">CPU</div>
                        <div class="stat-value ${this.getTempColor(cpu.temp)}">${(cpu.temp || 0).toFixed(1)}°C</div>
                    </div>
                    <div>
                        <div class="stat-label">GPU</div>
                        <div class="stat-value ${this.getTempColor(gpu.temp)}">${(gpu.temp || 0).toFixed(1)}°C</div>
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
                    <div class="stat-value ${this.getBatteryColor(ups.percent)}">${ups.percent || 0}%</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Voltage</div>
                    <div class="stat-value text-info">${(ups.voltage || 0).toFixed(2)}V</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Model</div>
                    <div class="stat-value text-primary">${ups.model || 'Unknown'}</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Battery Status</h3>
                <div class="progress mb-2" style="height: 30px;">
                    <div class="progress-bar" style="width: ${ups.percent || 0}%"></div>
                </div>
                <div class="grid grid-2 mt-2">
                    <div class="flex-between">
                        <span>Status</span>
                        <span class="badge ${ups.charging ? 'badge-success' : 'badge-warning'}">
                            ${ups.charging ? '⚡ Charging' : '🔌 Discharging'}
                        </span>
                    </div>
                    <div class="flex-between">
                        <span>Input Power</span>
                        <span class="badge ${ups.input_power ? 'badge-success' : 'badge-error'}">
                            ${ups.input_power ? 'Connected' : 'Disconnected'}
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">UPS Information</h3>
                <table class="table">
                    <tr>
                        <td>Model</td>
                        <td>${ups.model || 'Auto-detect'}</td>
                    </tr>
                    <tr>
                        <td>Last Updated</td>
                        <td>${this.formatTimestamp(ups.updated)}</td>
                    </tr>
                </table>
            </div>
        `;
    }
    
    renderNetwork() {
        const network = this.data.network || {};
        const wifi = network.wifi || {};
        const ethernet = network.ethernet || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">Network</h1>
                <p class="page-subtitle">Network connectivity and interfaces</p>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Active Connection</h3>
                <table class="table">
                    <tr>
                        <td>Active Interface</td>
                        <td><span class="badge ${network.active !== 'none' ? 'badge-success' : 'badge-error'}">${network.active || 'None'}</span></td>
                    </tr>
                    <tr>
                        <td>IP Address</td>
                        <td>${network.ip || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Last Updated</td>
                        <td>${this.formatTimestamp(network.updated)}</td>
                    </tr>
                </table>
            </div>
            
            <div class="grid grid-2 mb-3">
                <div class="card">
                    <h3 class="card-title mb-2">WiFi</h3>
                    <table class="table">
                        <tr>
                            <td>Status</td>
                            <td><span class="badge ${wifi.connected ? 'badge-success' : 'badge-error'}">${wifi.connected ? 'Connected' : 'Disconnected'}</span></td>
                        </tr>
                        ${wifi.connected ? `
                        <tr>
                            <td>SSID</td>
                            <td>${wifi.ssid || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td>Signal Strength</td>
                            <td>${wifi.strength || 0}%</td>
                        </tr>
                        <tr>
                            <td>Frequency</td>
                            <td>${wifi.frequency || 0} MHz</td>
                        </tr>
                        <tr>
                            <td>IP Address</td>
                            <td>${wifi.ip || 'N/A'}</td>
                        </tr>
                        ` : ''}
                    </table>
                </div>
                
                <div class="card">
                    <h3 class="card-title mb-2">Ethernet</h3>
                    <table class="table">
                        <tr>
                            <td>Status</td>
                            <td><span class="badge ${ethernet.connected ? 'badge-success' : 'badge-error'}">${ethernet.connected ? 'Connected' : 'Disconnected'}</span></td>
                        </tr>
                        ${ethernet.connected ? `
                        <tr>
                            <td>IP Address</td>
                            <td>${ethernet.ip || 'N/A'}</td>
                        </tr>
                        ` : ''}
                    </table>
                </div>
            </div>
        `;
    }
    
    renderModem() {
        const modem = this.data.modem || {};
        const signal = modem.signal || {};
        
        return `
            <div class="page-header">
                <h1 class="page-title">Modem</h1>
                <p class="page-subtitle">Cellular modem status</p>
            </div>
            
            ${!modem.connected ? `
            <div class="card mb-3" style="background: var(--bg-card); border-left: 4px solid var(--error);">
                <h3 class="card-title mb-2">⚠️ Modem Not Detected</h3>
                <p class="text-warning mb-2">The modem is not connected or not recognized.</p>
                <p class="text-muted mb-2"><strong>Troubleshooting steps:</strong></p>
                <ol class="text-muted" style="margin-left: 20px; line-height: 1.8;">
                    <li>Check if modem is plugged into USB port</li>
                    <li>Check backend logs: <code style="background: var(--bg-light); padding: 2px 6px; border-radius: 4px;">sudo journalctl -u ada-pi-backend -f</code></li>
                    <li>List USB devices: <code style="background: var(--bg-light); padding: 2px 6px; border-radius: 4px;">lsusb</code></li>
                    <li>Check for ttyUSB ports: <code style="background: var(--bg-light); padding: 2px 6px; border-radius: 4px;">ls /dev/ttyUSB*</code></li>
                    <li>Check ModemManager: <code style="background: var(--bg-light); padding: 2px 6px; border-radius: 4px;">mmcli -L</code></li>
                    <li>Restart ModemManager: <code style="background: var(--bg-light); padding: 2px 6px; border-radius: 4px;">sudo systemctl restart ModemManager</code></li>
                </ol>
                ${modem.error ? `<p class="text-error mt-2"><strong>Error:</strong> ${modem.error}</p>` : ''}
            </div>
            ` : ''}
            
            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Network</div>
                    <div class="stat-value text-info">${modem.network_mode || 'N/A'}</div>
                    <div class="stat-label">${modem.band || 'Unknown Band'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Operator</div>
                    <div class="stat-value text-primary">${modem.operator || 'N/A'}</div>
                    <div class="stat-label">${modem.registration || 'Unknown'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Signal</div>
                    <div class="stat-value ${this.getSignalColor(signal.rssi)}">${signal.rssi || 'N/A'} dBm</div>
                    <div class="stat-label">RSSI</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Modem Information</h3>
                <table class="table">
                    <tr>
                        <td>Status</td>
                        <td><span class="badge ${modem.connected ? 'badge-success' : 'badge-error'}">${modem.connected ? 'Connected' : 'Disconnected'}</span></td>
                    </tr>
                    <tr>
                        <td>Brand</td>
                        <td>${modem.brand || 'Unknown'}</td>
                    </tr>
                    <tr>
                        <td>Model</td>
                        <td>${modem.model || 'Unknown'}</td>
                    </tr>
                    <tr>
                        <td>IMEI</td>
                        <td>${modem.imei || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>ICCID (SIM)</td>
                        <td>${modem.iccid || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>IMSI</td>
                        <td>${modem.imsi || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>AT Port</td>
                        <td>${modem.at_port || 'N/A'}</td>
                    </tr>
                </table>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Signal Quality</h3>
                <table class="table">
                    <tr>
                        <td>RSSI (Signal Strength)</td>
                        <td>${signal.rssi || 'N/A'} dBm</td>
                    </tr>
                    <tr>
                        <td>RSRP (LTE Power)</td>
                        <td>${signal.rsrp || 'N/A'} dBm</td>
                    </tr>
                    <tr>
                        <td>RSRQ (LTE Quality)</td>
                        <td>${signal.rsrq || 'N/A'} dB</td>
                    </tr>
                    <tr>
                        <td>SINR (Signal/Noise)</td>
                        <td>${signal.sinr || 'N/A'} dB</td>
                    </tr>
                </table>
            </div>
        `;
    }
    
    renderBluetooth() {
        const bt = this.data.bluetooth || {};
        const paired = bt.paired || [];
        const available = bt.available || [];

        return `
            <div class="page-header">
                <h1 class="page-title">Bluetooth</h1>
                <p class="page-subtitle">Bluetooth devices and connections</p>
            </div>

            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Adapter</div>
                    <div class="stat-value ${bt.powered ? 'text-success' : 'text-error'}">${bt.powered ? 'Powered' : 'Off'}</div>
                    <div class="stat-label">${bt.mac || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Discoverable</div>
                    <div class="stat-value ${bt.discoverable ? 'text-success' : 'text-warning'}">${bt.discoverable ? 'Yes' : 'No'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Paired Devices</div>
                    <div class="stat-value text-info">${paired.length}</div>
                </div>
            </div>

            <div class="card mb-3">
                <h3 class="card-title mb-2">Paired Devices</h3>
                ${paired.length ? `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>MAC</th>
                                <th>Connected</th>
                                <th>RSSI</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${paired.map(dev => `
                                <tr>
                                    <td>${dev.name || 'Unknown'}</td>
                                    <td>${dev.mac}</td>
                                    <td><span class="badge ${dev.connected ? 'badge-success' : 'badge-error'}">${dev.connected ? 'Yes' : 'No'}</span></td>
                                    <td>${dev.rssi ?? 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="text-muted text-center" style="padding: 20px;">No paired devices found.</p>'}
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Available Devices</h3>
                ${available.length ? `
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>MAC</th>
                                <th>RSSI</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${available.map(dev => `
                                <tr>
                                    <td>${dev.name || 'Unknown'}</td>
                                    <td>${dev.mac}</td>
                                    <td>${dev.rssi ?? 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                ` : '<p class="text-muted text-center" style="padding: 20px;">No available devices detected.</p>'}
            </div>
        `;
    }
    
    renderOBD() {
        const obd = this.data.obd || {};
        const values = obd.values || {};
        const dtc = obd.dtc || [];
        
        return `
            <div class="page-header">
                <h1 class="page-title">OBD Diagnostics</h1>
                <p class="page-subtitle">Vehicle diagnostic data</p>
            </div>
            
            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">RPM</div>
                    <div class="stat-value text-primary">${values.rpm || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Speed</div>
                    <div class="stat-value text-info">${values.speed || 0} km/h</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Coolant</div>
                    <div class="stat-value ${this.getTempColor(values.coolant)}">${values.coolant || 0}°C</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Throttle</div>
                    <div class="stat-value text-success">${values.throttle || 0}%</div>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Connection Status</h3>
                <table class="table">
                    <tr>
                        <td>Status</td>
                        <td><span class="badge ${obd.connected ? 'badge-success' : 'badge-error'}">${obd.connected ? 'Connected' : 'Disconnected'}</span></td>
                    </tr>
                    <tr>
                        <td>Port</td>
                        <td>${obd.port || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Protocol</td>
                        <td>${obd.protocol || 'N/A'}</td>
                    </tr>
                    ${obd.error ? `
                    <tr>
                        <td>Error</td>
                        <td class="text-error">${obd.error}</td>
                    </tr>
                    ` : ''}
                </table>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Engine Data</h3>
                <div class="grid grid-2">
                    <table class="table">
                        <tr>
                            <td>Engine Load</td>
                            <td>${values.load || 0}%</td>
                        </tr>
                        <tr>
                            <td>Fuel Level</td>
                            <td>${values.fuel_level || 0}%</td>
                        </tr>
                        <tr>
                            <td>Intake Temp</td>
                            <td>${values.intake_temp || 0}°C</td>
                        </tr>
                        <tr>
                            <td>MAF</td>
                            <td>${(values.maf || 0).toFixed(2)} g/s</td>
                        </tr>
                    </table>
                    <table class="table">
                        <tr>
                            <td>MAP</td>
                            <td>${values.map || 0} kPa</td>
                        </tr>
                        <tr>
                            <td>Voltage</td>
                            <td>${(values.voltage || 0).toFixed(1)}V</td>
                        </tr>
                        <tr>
                            <td>Boost Pressure</td>
                            <td>${values.boost_pressure || 0} kPa</td>
                        </tr>
                        <tr>
                            <td>Rail Pressure</td>
                            <td>${values.rail_pressure || 0}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            ${dtc.length > 0 ? `
            <div class="card">
                <h3 class="card-title mb-2">Diagnostic Trouble Codes</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Code</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${dtc.map(code => `
                            <tr>
                                <td><span class="badge badge-error">${code}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                <div class="mt-2">
                    <button class="btn btn-primary" onclick="window.adaPi.clearDTC()">Clear Codes</button>
                </div>
            </div>
            ` : ''}
        `;
    }
    
    async clearDTC() {
        const result = await this.apiPost('/api/obd/clear', {});
        if (result && result.status === 'ok') {
            alert('DTC codes cleared successfully');
            await this.fetchOBD();
            this.updateCurrentPage();
        }
    }
    
    renderTacho() {
        const tacho = this.data.tacho || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Tachograph</h1>
                <p class="page-subtitle">Driver hours and speed logging</p>
            </div>

            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Current Speed</div>
                    <div class="stat-value text-primary">${(tacho.speed || 0).toFixed(1)} km/h</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Latitude</div>
                    <div class="stat-value">${(tacho.latitude || 0).toFixed(6)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Longitude</div>
                    <div class="stat-value">${(tacho.longitude || 0).toFixed(6)}</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Tachograph Status</h3>
                <table class="table">
                    <tr>
                        <td>Logging Enabled</td>
                        <td><span class="badge ${tacho.enabled ? 'badge-success' : 'badge-error'}">${tacho.enabled ? 'On' : 'Off'}</span></td>
                    </tr>
                    <tr>
                        <td>Upload Interval</td>
                        <td>${tacho.upload_interval || 5} minutes</td>
                    </tr>
                    <tr>
                        <td>Last Upload</td>
                        <td>${this.formatTimestamp(tacho.last_upload)}</td>
                    </tr>
                </table>
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
                <h3 class="card-title mb-2">Live Logs</h3>
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
        if (!logs || logs.length === 0) {
            document.getElementById('logsTable').innerHTML = '<p class="text-center text-muted" style="padding: 20px;">No logs available</p>';
            return;
        }
        
        const table = `
            <div style="max-height: 600px; overflow-y: auto;">
                <table class="table">
                    <tbody>
                        ${logs.map(log => `
                            <tr>
                                <td style="font-family: monospace; font-size: 12px;">${log}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        document.getElementById('logsTable').innerHTML = table;
    }
    
    renderSettings() {
        return `
            <div class="page-header">
                <h1 class="page-title">Settings</h1>
                <p class="page-subtitle">System configuration</p>
            </div>
            
            <div class="grid grid-2 mb-3">
                <div class="card">
                    <h3 class="card-title mb-2">Device Settings</h3>
                    <div class="mb-2">
                        <label class="stat-label">Device ID</label>
                        <input type="text" id="deviceId" class="form-input" placeholder="ada-pi-001">
                    </div>
                    <button class="btn btn-primary" onclick="window.adaPi.saveDeviceId()">Save Device ID</button>
                </div>
                
                <div class="card">
                    <h3 class="card-title mb-2">GPS Settings</h3>
                    <div class="mb-2">
                        <label class="stat-label">Unit Mode</label>
                        <select id="gpsUnit" class="form-input">
                            <option value="auto">Auto (GPS-based)</option>
                            <option value="kmh">Kilometers per hour (km/h)</option>
                            <option value="mph">Miles per hour (mph)</option>
                        </select>
                    </div>
                    <button class="btn btn-primary" onclick="window.adaPi.saveGPSUnit()">Save GPS Unit</button>
                </div>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Authentication</h3>
                <p class="text-warning mb-2">⚠️ Warning: Changing credentials will require re-login</p>
                <div class="grid grid-2 mb-2">
                    <div>
                        <label class="stat-label">Username</label>
                        <input type="text" id="authUsername" class="form-input" placeholder="admin">
                    </div>
                    <div>
                        <label class="stat-label">Password</label>
                        <input type="password" id="authPassword" class="form-input" placeholder="••••••">
                    </div>
                </div>
                <button class="btn btn-primary" onclick="window.adaPi.saveAuth()">Update Credentials</button>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">Cloud Upload</h3>
                <div class="mb-2">
                    <label class="stat-label">Upload URL</label>
                    <input type="text" id="cloudUrl" class="form-input" placeholder="https://api.example.com/upload">
                </div>
                <div class="mb-2">
                    <label class="stat-label">Logs URL</label>
                    <input type="text" id="logsUrl" class="form-input" placeholder="https://api.example.com/logs">
                </div>
                <button class="btn btn-primary" onclick="window.adaPi.saveCloud()">Save Cloud Settings</button>
            </div>
            
            <div class="card mb-3">
                <h3 class="card-title mb-2">UPS Settings</h3>
                <div class="mb-2">
                    <label class="stat-label">Auto-Shutdown Percentage</label>
                    <input type="number" id="upsShutdown" class="form-input" placeholder="10" min="5" max="50">
                    <small class="text-muted">System will shutdown when battery reaches this level</small>
                </div>
                <button class="btn btn-primary" onclick="window.adaPi.saveUPS()">Save UPS Settings</button>
            </div>
            
            <div class="card">
                <h3 class="card-title mb-2">Modem / APN Settings</h3>
                <p class="text-muted mb-2">Configure cellular modem Access Point Name (APN) for data connection</p>
                <div class="mb-2">
                    <label class="stat-label">APN (Access Point Name)</label>
                    <input type="text" id="modemApn" class="form-input" placeholder="e.g., three.co.uk, giffgaff.com, internet">
                    <small class="text-muted">Common UK: three.co.uk, giffgaff.com, pp.vodafone.co.uk, mobile.o2.co.uk</small>
                </div>
                <div class="grid grid-2 mb-2">
                    <div>
                        <label class="stat-label">Username (optional)</label>
                        <input type="text" id="modemUsername" class="form-input" placeholder="Usually blank">
                    </div>
                    <div>
                        <label class="stat-label">Password (optional)</label>
                        <input type="password" id="modemPassword" class="form-input" placeholder="Usually blank">
                    </div>
                </div>
                <div class="grid grid-2">
                    <button class="btn btn-primary" onclick="window.adaPi.saveModemAPN()">Save APN Settings</button>
                    <button class="btn btn-secondary" onclick="window.adaPi.resetModem()">Reset Modem</button>
                </div>
            </div>
            
            <style>
                .form-input {
                    width: 100%;
                    padding: 10px;
                    background: var(--bg-light);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-sm);
                    color: var(--text);
                    font-size: var(--font-base);
                    margin-bottom: 8px;
                }
                .form-input:focus {
                    outline: none;
                    border-color: var(--primary);
                }
            </style>
        `;
    }
    
    setupSettingsHandlers() {
        // Already using onclick in HTML
    }
    
    populateSettings() {
        const settings = this.settings;
        
        // Device ID
        const deviceIdInput = document.getElementById('deviceId');
        if (deviceIdInput && settings.device_id) {
            deviceIdInput.value = settings.device_id;
        }
        
        // GPS Unit
        const gpsUnitSelect = document.getElementById('gpsUnit');
        if (gpsUnitSelect && settings.gps && settings.gps.unit_mode) {
            gpsUnitSelect.value = settings.gps.unit_mode;
        }
        
        // Auth
        const authUsername = document.getElementById('authUsername');
        if (authUsername && settings.auth && settings.auth.username) {
            authUsername.value = settings.auth.username;
        }
        
        // Cloud
        const cloudUrl = document.getElementById('cloudUrl');
        const logsUrl = document.getElementById('logsUrl');
        if (cloudUrl && settings.cloud) {
            cloudUrl.value = settings.cloud.upload_url || '';
            logsUrl.value = settings.cloud.logs_url || '';
        }
        
        // UPS
        const upsShutdown = document.getElementById('upsShutdown');
        if (upsShutdown && settings.ups && settings.ups.shutdown_pct) {
            upsShutdown.value = settings.ups.shutdown_pct;
        }
        
        // Modem APN
        const modemApn = document.getElementById('modemApn');
        const modemUsername = document.getElementById('modemUsername');
        const modemPassword = document.getElementById('modemPassword');
        if (modemApn && settings.modem) {
            modemApn.value = settings.modem.apn || '';
            if (modemUsername) modemUsername.value = settings.modem.username || '';
            if (modemPassword) modemPassword.value = settings.modem.password || '';
        }
    }
    
    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const errorDiv = document.getElementById('loginError');
        
        if (!username || !password) {
            errorDiv.textContent = 'Please enter both username and password';
            errorDiv.style.display = 'block';
            return;
        }
        
        try {
            // Authenticate against adasystems.uk
            const response = await fetch(`${this.authApiUrl}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    password: password,
                    device_id: 'ada-pi-001' // TODO: Get from config
                })
            });
            
            const result = await response.json();
            
            if (result.success && result.data.token) {
                // Authentication successful
                this.jwtToken = result.data.token;
                this.userData = result.data.user;
                this.isAuthenticated = true;
                
                // Store token in sessionStorage
                sessionStorage.setItem('ada_pi_token', this.jwtToken);
                sessionStorage.setItem('ada_pi_user', JSON.stringify(this.userData));
                
                errorDiv.style.display = 'none';
                
                console.log('✓ Login successful as:', this.userData.name);
                console.log('✓ Role:', this.userData.role);
                console.log('✓ Permissions:', this.userData.permissions);
                
                // Load Dashboard page and start refreshing data
                this.loadPage('dashboard');
                this.refreshAllData();
                
            } else {
                // Authentication failed
                this.jwtToken = null;
                this.userData = null;
                this.isAuthenticated = false;
                
                errorDiv.textContent = result.message || '✗ Invalid credentials. Please try again.';
                errorDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('Login error:', error);
            errorDiv.textContent = '✗ Connection error. Please check your internet connection.';
            errorDiv.style.display = 'block';
        }
    }
    
    async validateToken() {
        if (!this.jwtToken) return false;
        
        try {
            const response = await fetch(`${this.authApiUrl}/auth/validate`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.jwtToken}`,
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            return result.success === true;
        } catch (error) {
            console.error('Token validation error:', error);
            return false;
        }
    }
    
    logout(redirect = true) {
        // Clear token and user data
        this.jwtToken = null;
        this.userData = null;
        this.isAuthenticated = false;
        
        sessionStorage.removeItem('ada_pi_token');
        sessionStorage.removeItem('ada_pi_user');
        
        console.log('✓ Logged out');
        
        if (redirect) {
            // Reload page to show login screen
            this.loadPage('dashboard');
        }
    }
    
    async saveDeviceId() {
        const deviceId = document.getElementById('deviceId').value;
        const result = await this.apiPost('/api/settings/device', { device_id: deviceId });
        if (result && result.status === 'ok') {
            alert('Device ID saved successfully');
        } else {
            alert('Failed to save Device ID');
        }
    }
    
    async saveGPSUnit() {
        const mode = document.getElementById('gpsUnit').value;
        const result = await this.apiPost('/api/gps/unit', { mode });
        if (result && result.status === 'ok') {
            alert('GPS unit mode saved successfully');
            await this.fetchGPS();
            this.updateCurrentPage();
        } else {
            alert('Failed to save GPS unit mode');
        }
    }
    
    async saveAuth() {
        const username = document.getElementById('authUsername').value;
        const password = document.getElementById('authPassword').value;
        
        if (!username || !password) {
            alert('Please enter both username and password');
            return;
        }
        
        const result = await this.apiPost('/api/settings', {
            auth: { username, password }
        });
        
        if (result && result.status === 'ok') {
            alert('Credentials updated successfully. Please re-login if accessing remotely.');
        } else {
            alert('Failed to update credentials');
        }
    }
    
    async saveCloud() {
        const uploadUrl = document.getElementById('cloudUrl').value;
        const logsUrl = document.getElementById('logsUrl').value;
        
        const result = await this.apiPost('/api/settings/cloud', {
            upload_url: uploadUrl,
            logs_url: logsUrl
        });
        
        if (result && result.status === 'ok') {
            alert('Cloud settings saved successfully');
        } else {
            alert('Failed to save cloud settings');
        }
    }
    
    async saveUPS() {
        const shutdownPct = parseInt(document.getElementById('upsShutdown').value);
        
        if (isNaN(shutdownPct) || shutdownPct < 5 || shutdownPct > 50) {
            alert('Please enter a value between 5 and 50');
            return;
        }
        
        const result = await this.apiPost('/api/settings/ups', {
            shutdown_pct: shutdownPct
        });
        
        if (result && result.status === 'ok') {
            alert('UPS settings saved successfully');
        } else {
            alert('Failed to save UPS settings');
        }
    }
    
    async saveModemAPN() {
        const apn = document.getElementById('modemApn').value;
        const username = document.getElementById('modemUsername').value;
        const password = document.getElementById('modemPassword').value;
        
        if (!apn) {
            alert('Please enter an APN');
            return;
        }
        
        const result = await this.apiPost('/api/settings', {
            modem: {
                apn: apn,
                username: username || '',
                password: password || ''
            }
        });
        
        if (result && result.status === 'ok') {
            alert('APN settings saved successfully. Modem will reconnect with new settings.');
        } else {
            alert('Failed to save APN settings');
        }
    }
    
    async resetModem() {
        if (!confirm('Are you sure you want to reset the modem? This will disconnect and reconnect the cellular connection.')) {
            return;
        }
        
        const result = await this.apiPost('/api/modem/reset', {});
        
        if (result && result.status === 'ok') {
            alert('Modem reset initiated. Please wait 30-60 seconds for reconnection.');
        } else {
            alert('Failed to reset modem');
        }
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
    
    getSignalColor(rssi) {
        if (rssi > -70) return 'text-success';
        if (rssi > -85) return 'text-warning';
        return 'text-error';
    }

    formatTimestamp(ts) {
        if (!ts) return 'Never';
        try {
            if (typeof ts === 'number') {
                return new Date(ts * 1000).toLocaleString();
            }
            return new Date(ts).toLocaleString();
        } catch (e) {
            return 'Invalid date';
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adaPi = new AdaPiApp();
});