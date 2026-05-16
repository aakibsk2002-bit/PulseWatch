# PulseWatch NOC - Real-time Network Monitoring Dashboard

## 📊 Overview

PulseWatch is a professional Network Operations Center (NOC) monitoring software built for enterprise-grade network management. Monitor 5000+ devices in real-time with intelligent alerts, dependency mapping, and automated discovery.

## ✨ Features

- **Real-time Monitoring**: Monitor 5000+ network devices simultaneously
- **Network Topology Map**: Visualize device relationships with vis.js
- **Server/Viewer Mode**: Single application, dual operation modes
- **Auto Discovery**: Automatically scan and discover network devices
- **Intelligent Alerts**: Event correlation and dependency-based alerting
- **Device Grouping**: Organize devices by zones, locations, or custom groups
- **Responsive Dashboard**: Dark/Light theme support
- **Drag & Drop Layout**: Customize topology map and save positions
- **Event Logs**: Complete audit trail of all system events
- **Portable**: Single .exe file, no installation required

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ with FastAPI
- **Async**: asyncio for concurrent monitoring
- **Database**: SQLite (embedded, portable)
- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **Topology**: vis.js Network Library
- **Real-time**: WebSocket for live updates
- **Packaging**: PyInstaller for .exe

## 📁 Project Structure

```
PulseWatch/
├── src/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI server + WebSocket
│   │   ├── database.py          # SQLite setup & queries
│   │   ├── monitor.py           # Async monitoring engine
│   │   ├── discovery.py         # Auto discovery (future)
│   │   ├── dependency.py        # Dependency engine (future)
│   │   └── alerts.py            # Alert system (future)
│   │
│   └── frontend/
│       ├── index.html           # Start screen
│       ├── dashboard.html       # Main NOC dashboard
│       ├── css/
│       │   ├── main.css         # Dark/Light theme
│       │   └── responsive.css
│       ├── js/
│       │   ├── app.js           # Main app logic
│       │   ├── topology.js      # vis.js network
│       │   ├── devices.js       # Device grid
│       │   ├── alerts.js        # Alert panel
│       │   └── websocket.js     # Real-time updates
│       └── icons/
│           ├── router.png
│           ├── switch.png
│           ├── server.png
│           ├── camera.png
│           ├── printer.png
│           └── pc.png
│
├── data/
│   └── pulsewatch.db           # SQLite database
├── logs/
├── requirements.txt
├── setup.py                     # EXE packaging config
└── README.md
```

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.11+
npm or pip (for frontend dependencies)
```

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/aakibsk2002-bit/PulseWatch.git
cd PulseWatch
```

2. **Create Virtual Environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Run Application**
```bash
python src/backend/main.py
```

5. **Open in Browser**
```
http://localhost:8000
```

## 📖 Development Phases

- **Phase 1**: Backend foundation ✅
- **Phase 2**: Frontend dashboard
- **Phase 3**: Topology visualization
- **Phase 4**: Device management
- **Phase 5**: Alerts & logs
- **Phase 6**: Auto discovery
- **Phase 7**: Settings & configuration
- **Phase 8**: EXE packaging

## 🔧 Configuration

Create `config.json`:
```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "monitoring": {
    "interval": 10,
    "timeout": 5,
    "batch_size": 100
  },
  "ui": {
    "theme": "dark",
    "devices_per_page": 48
  }
}
```

## 📝 License

MIT License - See LICENSE file

## 👤 Author

Netraix Technologies (Aakib's Startup)

## 📞 Support

For issues and feature requests, please create an GitHub issue.

---

**Made with ❤️ for Network Operations Teams**