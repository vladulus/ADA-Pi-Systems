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
                    <div class="stat-value text-primary">${gps.speed || 0} ${gps.unit || 'km/h'}</div>
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
                    <div class="stat-value">${gps.hdop ?? 'N/A'}</div>
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
                        <td>${gps.heading ?? 'N/A'}°</td>
                    </tr>
                    <tr>
                        <td>Timestamp (UTC)</td>
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
                        <td>Hostname</td>
                        <td>${system.hostname || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Uptime</td>
                        <td>${system.uptime || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>CPU Temp</td>
                        <td>${(system.cpu?.temp || 0).toFixed(1)} °C</td>
                    </tr>
                    <tr>
                        <td>GPU Temp</td>
                        <td>${(system.gpu?.temp || 0).toFixed(1)} °C</td>
                    </tr>
                    <tr>
                        <td>Fan Speed</td>
                        <td>${system.fan_speed || 0} RPM</td>
                    </tr>
                </table>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Processes</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>CPU %</th>
                            <th>Mem %</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(system.processes || []).map(p => `
                            <tr>
                                <td>${p.name}</td>
                                <td>${p.cpu}</td>
                                <td>${p.mem}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderUPS() {
        const ups = this.data.ups || {};

        return `
            <div class="page-header">
                <h1 class="page-title">UPS Status</h1>
                <p class="page-subtitle">Battery and power supply information</p>
            </div>

            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Battery</div>
                    <div class="stat-value ${this.getBatteryColor(ups.battery_percent)}">${ups.battery_percent || 0}%</div>
                    <div class="stat-label">${ups.charging ? 'Charging' : 'Discharging'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Voltage</div>
                    <div class="stat-value text-info">${ups.voltage || 0} V</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Current</div>
                    <div class="stat-value text-warning">${ups.current || 0} A</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Temp</div>
                    <div class="stat-value text-primary">${ups.temperature || 0} °C</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Power Details</h3>
                <table class="table">
                    <tr>
                        <td>Input</td>
                        <td>${ups.input_voltage || 0} V</td>
                    </tr>
                    <tr>
                        <td>Output</td>
                        <td>${ups.output_voltage || 0} V</td>
                    </tr>
                    <tr>
                        <td>Capacity</td>
                        <td>${ups.capacity || 0} mAh</td>
                    </tr>
                    <tr>
                        <td>Health</td>
                        <td>${ups.health || 'N/A'}</td>
                    </tr>
                </table>
            </div>
        `;
    }

    renderNetwork() {
        const net = this.data.network || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Network</h1>
                <p class="page-subtitle">Interfaces and connectivity</p>
            </div>

            <div class="grid grid-3 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Status</div>
                    <div class="stat-value ${net.connected ? 'text-success' : 'text-error'}">${net.connected ? 'Online' : 'Offline'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">IP Address</div>
                    <div class="stat-value">${net.ip || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Interface</div>
                    <div class="stat-value text-info">${net.interface || 'N/A'}</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Interfaces</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>MAC</th>
                            <th>Speed</th>
                            <th>State</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(net.interfaces || []).map(iface => `
                            <tr>
                                <td>${iface.name}</td>
                                <td>${iface.mac}</td>
                                <td>${iface.speed || 'N/A'}</td>
                                <td>${iface.state}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderModem() {
        const modem = this.data.modem || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Modem</h1>
                <p class="page-subtitle">Cellular connectivity</p>
            </div>

            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Status</div>
                    <div class="stat-value ${modem.connected ? 'text-success' : 'text-error'}">${modem.connected ? 'Connected' : 'Disconnected'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Signal</div>
                    <div class="stat-value text-info">${modem.signal || 0} dBm</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Network</div>
                    <div class="stat-value text-primary">${modem.network || 'N/A'}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Mode</div>
                    <div class="stat-value">${modem.mode || 'N/A'}</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Connection Details</h3>
                <table class="table">
                    <tr>
                        <td>Operator</td>
                        <td>${modem.operator || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>APN</td>
                        <td>${modem.apn || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>IP</td>
                        <td>${modem.ip || 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>IMEI</td>
                        <td>${modem.imei || 'N/A'}</td>
                    </tr>
                </table>
            </div>
        `;
    }

    renderBluetooth() {
        const bt = this.data.bluetooth || {};

        const paired = bt.paired_devices || [];
        const available = bt.available_devices || [];

        return `
            <div class="page-header">
                <h1 class="page-title">Bluetooth</h1>
                <p class="page-subtitle">Adapters, paired devices, and scanning</p>
            </div>

            <div class="grid grid-2 mb-3">
                <div class="card">
                    <h3 class="card-title mb-2">Adapter</h3>
                    <table class="table">
                        <tr>
                            <td>Name</td>
                            <td>${bt.adapter?.name || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td>Address</td>
                            <td>${bt.adapter?.address || 'N/A'}</td>
                        </tr>
                        <tr>
                            <td>Powered</td>
                            <td>${bt.adapter?.powered ? 'Yes' : 'No'}</td>
                        </tr>
                        <tr>
                            <td>Discoverable</td>
                            <td>${bt.adapter?.discoverable ? 'Yes' : 'No'}</td>
                        </tr>
                    </table>
                </div>

                <div class="card">
                    <h3 class="card-title mb-2">Actions</h3>
                    <div class="button-group">
                        <button class="btn" onclick="window.adaPi.scanBluetooth()">Scan</button>
                        <button class="btn" onclick="window.adaPi.toggleBluetooth()">Toggle Power</button>
                        <button class="btn" onclick="window.adaPi.toggleDiscoverable()">Toggle Discoverable</button>
                    </div>
                </div>
            </div>

            <div class="card mb-3">
                <h3 class="card-title mb-2">Paired Devices</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Address</th>
                            <th>Connected</th>
                            <th>RSSI</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${paired.map(dev => `
                            <tr>
                                <td>${dev.name || 'Unknown'}</td>
                                <td>${dev.address}</td>
                                <td>${dev.connected ? 'Yes' : 'No'}</td>
                                <td>${dev.rssi || 'N/A'}</td>
                                <td><button class="btn btn-small" onclick="window.adaPi.disconnectBluetooth('${dev.address}')">Disconnect</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Available Devices</h3>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Address</th>
                            <th>RSSI</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        ${available.map(dev => `
                            <tr>
                                <td>${dev.name || 'Unknown'}</td>
                                <td>${dev.address}</td>
                                <td>${dev.rssi || 'N/A'}</td>
                                <td><button class="btn btn-small" onclick="window.adaPi.pairBluetooth('${dev.address}')">Pair</button></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderTacho() {
        const tacho = this.data.tacho || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Tachograph</h1>
                <p class="page-subtitle">Vehicle speed and location data</p>
            </div>

            <div class="grid grid-4 mb-3">
                <div class="stat-card">
                    <div class="stat-label">Speed</div>
                    <div class="stat-value text-primary">${tacho.speed || 0} km/h</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Latitude</div>
                    <div class="stat-value">${tacho.latitude || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Longitude</div>
                    <div class="stat-value">${tacho.longitude || 0}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Altitude</div>
                    <div class="stat-value text-info">${tacho.altitude || 0} m</div>
                </div>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Tachograph Details</h3>
                <table class="table">
                    <tr>
                        <td>Log Enabled</td>
                        <td>${tacho.logging_enabled ? 'Yes' : 'No'}</td>
                    </tr>
                    <tr>
                        <td>Last Update</td>
                        <td>${tacho.last_timestamp || 'N/A'}</td>
                    </tr>
                </table>
            </div>
        `;
    }

    renderOBD() {
        const obd = this.data.obd || {};

        return `
            <div class="page-header">
                <h1 class="page-title">OBD-II</h1>
                <p class="page-subtitle">Vehicle diagnostics and live data</p>
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
                    <div class="stat-label">Coolant</div>
                    <div class="stat-value text-warning">${obd.coolant_temp || 0} °C</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Load</div>
                    <div class="stat-value">${obd.engine_load || 0}%</div>
                </div>
            </div>

            <div class="card mb-3">
                <h3 class="card-title mb-2">Fuel & Air</h3>
                <table class="table">
                    <tr>
                        <td>Fuel Level</td>
                        <td>${obd.fuel_level || 0}%</td>
                    </tr>
                    <tr>
                        <td>Fuel Rate</td>
                        <td>${obd.fuel_rate || 0} L/h</td>
                    </tr>
                    <tr>
                        <td>Air Temp</td>
                        <td>${obd.intake_air_temp || 0} °C</td>
                    </tr>
                    <tr>
                        <td>MAF</td>
                        <td>${obd.maf || 0} g/s</td>
                    </tr>
                </table>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">Error Codes</h3>
                <div class="button-group mb-2">
                    <button class="btn" onclick="window.adaPi.clearOBD()">Clear Codes</button>
                </div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Code</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(obd.dtc || []).map(code => `
                            <tr>
                                <td>${code.code}</td>
                                <td>${code.desc}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderLogs() {
        return `
            <div class="page-header">
                <h1 class="page-title">Logs</h1>
                <p class="page-subtitle">Recent system logs</p>
            </div>
            <div class="card">
                <h3 class="card-title mb-2">Recent Logs</h3>
                <div id="logsTable"></div>
            </div>
        `;
    }

    renderSettings() {
        const gps = this.data.gps || {};

        return `
            <div class="page-header">
                <h1 class="page-title">Settings</h1>
                <p class="page-subtitle">Configure units and preferences</p>
            </div>

            <div class="card">
                <h3 class="card-title mb-2">GPS Speed Units</h3>
                <div class="button-group">
                    <button class="btn ${gps.unit === 'kmh' ? 'active' : ''}" onclick="window.adaPi.setGPSUnit('kmh')">km/h</button>
                    <button class="btn ${gps.unit === 'mph' ? 'active' : ''}" onclick="window.adaPi.setGPSUnit('mph')">mph</button>
                    <button class="btn ${gps.unit === 'auto' ? 'active' : ''}" onclick="window.adaPi.setGPSUnit('auto')">Auto</button>
                </div>
                <p class="text-muted mt-2">Auto selects km/h or mph based on your location.</p>
            </div>
        `;
    }

    // Data Formatting Helpers
    formatBytes(bytes) {
        if (!bytes) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
    }

    getBatteryColor(percent) {
        if (percent >= 80) return 'text-success';
        if (percent >= 50) return 'text-warning';
        return 'text-error';
    }

    // API Interactions (Button Handlers)
    async setGPSUnit(mode) {
        const res = await this.apiPost('/api/gps/unit', { mode });
        if (res && res.data) {
            this.data.gps = this.data.gps || {};
            this.data.gps.unit = res.data.unit_mode;
            this.updateCurrentPage();
        }
    }

    async clearOBD() {
        await this.apiPost('/api/obd/clear', {});
    }

    async scanBluetooth() {
        await this.apiPost('/api/bluetooth/scan', {});
    }

    async toggleBluetooth() {
        await this.apiPost('/api/bluetooth/toggle_power', {});
    }

    async toggleDiscoverable() {
        await this.apiPost('/api/bluetooth/toggle_discoverable', {});
    }

    async pairBluetooth(address) {
        await this.apiPost('/api/bluetooth/pair', { address });
    }

    async disconnectBluetooth(address) {
        await this.apiPost('/api/bluetooth/disconnect', { address });
    }

    // Logs rendering
    renderLogsTable(logs) {
        const logsHtml = `
            <table class="table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Level</th>
                        <th>Source</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    ${logs.map(log => `
                        <tr>
                            <td>${log.timestamp}</td>
                            <td><span class="badge badge-${this.getLogLevelColor(log.level)}">${log.level}</span></td>
                            <td>${log.source}</td>
                            <td>${log.message}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
        const logsTable = document.getElementById('logsTable');
        if (logsTable) logsTable.innerHTML = logsHtml;
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
