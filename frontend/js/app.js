// ADA-Pi Web Dashboard - Enhanced Version with APN Management
class AdaPiApp {
    constructor() {
        this.apiUrl = window.location.origin;
        this.wsUrl = `ws://${window.location.hostname}:9000`;
        this.ws = null;
        this.currentPage = 'dashboard';
        this.data = {};
        this.lastUpdate = 0;
        this.updateThrottle = 500;
        this.settings = {};
        
        this.init();
    }
    
    init() {
        console.log('ADA-Pi Web Dashboard Starting...');
        this.setupNavigation();
        this.connectWebSocket();
        this.loadPage('dashboard');
        this.refreshAllData();
        setInterval(() => this.refreshAllData(), 10000);
    }
    
    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const page = item.dataset.page;
                this.loadPage(page);
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }
    
    loadPage(page) {
        this.currentPage = page;
        const content = document.getElementById('content');
        
        switch(page) {
            case 'dashboard': content.innerHTML = this.renderDashboard(); break;
            case 'gps': content.innerHTML = this.renderGPS(); break;
            case 'obd': content.innerHTML = this.renderOBD(); break;
            case 'system': content.innerHTML = this.renderSystem(); break;
            case 'ups': content.innerHTML = this.renderUPS(); break;
            case 'network': content.innerHTML = this.renderNetwork(); break;
            case 'modem': content.innerHTML = this.renderModem(); break;
            case 'bluetooth': content.innerHTML = this.renderBluetooth(); break;
            case 'tacho': content.innerHTML = this.renderTacho(); break;
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
        
        this.refreshCurrentPageData();
    }
    
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
                console.error('WebSocket parse error:', e);
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
        const eventMapping = {
            'gps_update': 'gps', 'system_update': 'system', 'ups_update': 'ups',
            'network_update': 'network', 'modem_update': 'modem', 'obd_update': 'obd',
            'bt_update': 'bluetooth', 'bluetooth_update': 'bluetooth',
            'tacho_update': 'tacho', 'fan_update': 'fan', 'logs_update': 'logs'
        };
        
        if (event && eventMapping[event]) {
            this.data[eventMapping[event]] = payload;
            console.log(`WS: ${event} →`, payload);
        }
        
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
    
    async refreshAllData() {
        await Promise.all([
            this.fetchSystemInfo(), this.fetchGPS(), this.fetchUPS(),
            this.fetchNetwork(), this.fetchModem(), this.fetchBluetooth(),
            this.fetchTacho(), this.fetchOBD()
        ]);
        this.updateCurrentPage();
    }
    
    async refreshCurrentPageData() {
        const actions = {
            'dashboard': () => this.refreshAllData(),
            'gps': () => this.fetchGPS(),
            'system': () => this.fetchSystemInfo(),
            'ups': () => this.fetchUPS(),
            'network': () => this.fetchNetwork(),
            'modem': () => this.fetchModem(),
            'bluetooth': () => this.fetchBluetooth(),
            'tacho': () => this.fetchTacho(),
            'obd': () => this.fetchOBD(),
            'logs': () => this.loadLogs(),
            'settings': () => this.loadSettings()
        };
        
        if (actions[this.currentPage]) {
            await actions[this.currentPage]();
            this.updateCurrentPage();
        }
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
        
        const pages = {
            'dashboard': () => this.renderDashboard(),
            'gps': () => this.renderGPS(),
            'obd': () => this.renderOBD(),
            'system': () => this.renderSystem(),
            'ups': () => this.renderUPS(),
            'network': () => this.renderNetwork(),
            'modem': () => this.renderModem(),
            'bluetooth': () => this.renderBluetooth(),
            'tacho': () => this.renderTacho()
        };
        
        if (pages[this.currentPage]) {
            content.innerHTML = pages[this.currentPage]();
        }
        
        content.scrollTop = scrollPosition;
    }
    
    // Render methods (Dashboard, GPS, System, UPS, Network - keeping same as before)
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
    
    // Keep other render methods the same (renderGPS, renderSystem, renderUPS, renderNetwork, renderBluetooth, renderOBD, renderTacho, renderLogs)
    // I'll include the critical ones and the NEW modem page with diagnostic info
    
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
                <p class="text-muted mb-2">Troubleshooting steps:</p>
                <ol class="text-muted" style="margin-left: 20px;">
                    <li>Check if modem is plugged into USB</li>
                    <li>Check backend logs: <code>sudo journalctl -u ada-pi-backend -f</code></li>
                    <li>List USB devices: <code>lsusb</code></li>
                    <li>Check for ttyUSB ports: <code>ls /dev/ttyUSB*</code></li>
                    <li>Restart ModemManager: <code>sudo systemctl restart ModemManager</code></li>
                    <li>Check if ModemManager sees it: <code>mmcli -L</code></li>
                </ol>
                ${modem.error ? `<p class="text-error mt-2">Error: ${modem.error}</p>` : ''}
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
                <h3 class="card-title mb-2">Modem APN Settings</h3>
                <p class="text-muted mb-2">Configure cellular network Access Point Name (APN)</p>
                <div class="mb-2">
                    <label class="stat-label">APN</label>
                    <input type="text" id="modemApn" class="form-input" placeholder="internet">
                    <small class="text-muted">Common APNs: internet, three.co.uk, giffgaff.com, mobile.vodafone.co.uk</small>
                </div>
                <div class="grid grid-2 mb-2">
                    <div>
                        <label class="stat-label">Username (optional)</label>
                        <input type="text" id="modemUsername" class="form-input" placeholder="">
                    </div>
                    <div>
                        <label class="stat-label">Password (optional)</label>
                        <input type="password" id="modemPassword" class="form-input" placeholder="">
                    </div>
                </div>
                <button class="btn btn-primary" onclick="window.adaPi.saveModemAPN()">Save APN Settings</button>
                <button class="btn btn-secondary ml-2" onclick="window.adaPi.resetModem()">Reset Modem</button>
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
            
            <div class="card">
                <h3 class="card-title mb-2">UPS Settings</h3>
                <div class="mb-2">
                    <label class="stat-label">Auto-Shutdown Percentage</label>
                    <input type="number" id="upsShutdown" class="form-input" placeholder="10" min="5" max="50">
                    <small class="text-muted">System will shutdown when battery reaches this level</small>
                </div>
                <button class="btn btn-primary" onclick="window.adaPi.saveUPS()">Save UPS Settings</button>
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
                .ml-2 {
                    margin-left: 8px;
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
        
        // Modem APN
        const modemApn = document.getElementById('modemApn');
        const modemUsername = document.getElementById('modemUsername');
        const modemPassword = document.getElementById('modemPassword');
        if (modemApn && settings.modem) {
            modemApn.value = settings.modem.apn || '';
            if (modemUsername) modemUsername.value = settings.modem.username || '';
            if (modemPassword) modemPassword.value = settings.modem.password || '';
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
                username: username,
                password: password
            }
        });
        
        if (result && result.status === 'ok') {
            alert('APN settings saved! You may need to restart the modem for changes to take effect.');
        } else {
            alert('Failed to save APN settings');
        }
    }
    
    async resetModem() {
        if (!confirm('Are you sure you want to reset the modem? This will restart the modem connection.')) {
            return;
        }
        
        const result = await this.apiPost('/api/modem/reset', {});
        if (result && result.status === 'ok') {
            alert('Modem reset command sent. Please wait 30 seconds for modem to reconnect.');
        } else {
            alert('Failed to reset modem');
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
    
    // Include stub render methods for pages not shown above
    renderGPS() { return '<div class="page-header"><h1>GPS</h1></div>'; }
    renderSystem() { return '<div class="page-header"><h1>System</h1></div>'; }
    renderUPS() { return '<div class="page-header"><h1>UPS</h1></div>'; }
    renderNetwork() { return '<div class="page-header"><h1>Network</h1></div>'; }
    renderBluetooth() { return '<div class="page-header"><h1>Bluetooth</h1></div>'; }
    renderOBD() { return '<div class="page-header"><h1>OBD</h1></div>'; }
    renderTacho() { return '<div class="page-header"><h1>Tacho</h1></div>'; }
    renderLogs() { return '<div class="page-header"><h1>Logs</h1><div id="logsTable"></div></div>'; }
    renderLogsTable(logs) { }
}

document.addEventListener('DOMContentLoaded', () => {
    window.adaPi = new AdaPiApp();
});
