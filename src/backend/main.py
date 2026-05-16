"""PulseWatch Backend Server - FastAPI + WebSocket

This is the main backend server that provides:
- REST API endpoints for device management
- WebSocket for real-time updates
- Monitoring engine integration
- Database management
- Event correlation (future)
"""

import asyncio
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from pathlib import Path

from database import db
from monitor import monitor

# Initialize FastAPI app
app = FastAPI(
    title="PulseWatch NOC API",
    description="Real-time Network Monitoring Dashboard",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from frontend
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# WebSocket connections manager
class ConnectionManager:
    """Manage WebSocket connections"""
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Broadcast error: {e}")


manager = ConnectionManager()


# ===== ROOT ROUTES =====

@app.get("/")
async def root():
    """Serve main dashboard"""
    html_path = frontend_path / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return {"message": "PulseWatch NOC Backend Running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = db.get_stats()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "stats": stats
    }


# ===== DEVICE ROUTES =====

@app.get("/api/devices")
async def get_devices():
    """Get all devices"""
    devices = db.get_all_devices()
    return {"success": True, "data": devices}


@app.get("/api/devices/{device_id}")
async def get_device(device_id: int):
    """Get specific device details"""
    device = db.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True, "data": device}


@app.post("/api/devices")
async def add_device(payload: dict):
    """Add new device"""
    try:
        device_id = db.add_device(
            name=payload.get("name", "Unnamed"),
            ip=payload.get("ip"),
            device_type=payload.get("type", "Other"),
            vendor=payload.get("vendor"),
            model=payload.get("model"),
            group_name=payload.get("group_name", "Default")
        )
        
        if device_id:
            await manager.broadcast({
                "type": "DEVICE_ADDED",
                "device_id": device_id
            })
            return {"success": True, "device_id": device_id, "message": "Device added"}
        else:
            raise HTTPException(status_code=400, detail="Device IP already exists")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: int):
    """Delete device"""
    success = db.delete_device(device_id)
    if success:
        await manager.broadcast({
            "type": "DEVICE_DELETED",
            "device_id": device_id
        })
        return {"success": True, "message": "Device deleted"}
    raise HTTPException(status_code=404, detail="Device not found")


# ===== ALERT ROUTES =====

@app.get("/api/alerts")
async def get_alerts():
    """Get all active alerts"""
    alerts = db.get_active_alerts()
    return {"success": True, "data": alerts}


@app.put("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Acknowledge alert"""
    db.acknowledge_alert(alert_id)
    await manager.broadcast({
        "type": "ALERT_ACKNOWLEDGED",
        "alert_id": alert_id
    })
    return {"success": True, "message": "Alert acknowledged"}


@app.put("/api/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Resolve alert"""
    db.resolve_alert(alert_id)
    await manager.broadcast({
        "type": "ALERT_RESOLVED",
        "alert_id": alert_id
    })
    return {"success": True, "message": "Alert resolved"}


# ===== LOGS ROUTES =====

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent event logs"""
    logs = db.get_recent_logs(limit)
    return {"success": True, "data": logs}


# ===== STATISTICS ROUTES =====

@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics"""
    stats = db.get_stats()
    return {"success": True, "data": stats}


# ===== WEBSOCKET ROUTES =====

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "STATUS_REQUEST":
                # Send current stats
                stats = db.get_stats()
                await websocket.send_json({
                    "type": "STATS_UPDATE",
                    "data": stats
                })
            
            elif message.get("type") == "DEVICES_REQUEST":
                # Send all devices
                devices = db.get_all_devices()
                await websocket.send_json({
                    "type": "DEVICES_UPDATE",
                    "data": devices
                })
            
            elif message.get("type") == "ALERTS_REQUEST":
                # Send all alerts
                alerts = db.get_active_alerts()
                await websocket.send_json({
                    "type": "ALERTS_UPDATE",
                    "data": alerts
                })
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


# ===== MONITORING CONTROL =====

@app.post("/api/monitoring/start")
async def start_monitoring():
    """Start monitoring engine"""
    if not monitor.is_running:
        asyncio.create_task(monitor.run_monitor_loop())
        return {"success": True, "message": "Monitoring started"}
    return {"success": False, "message": "Monitoring already running"}


@app.post("/api/monitoring/stop")
async def stop_monitoring():
    """Stop monitoring engine"""
    monitor.stop()
    return {"success": True, "message": "Monitoring stopped"}


@app.get("/api/monitoring/status")
async def monitoring_status():
    """Get monitoring engine status"""
    return {
        "success": True,
        "running": monitor.is_running,
        "last_run": monitor.last_run.isoformat() if monitor.last_run else None,
        "interval": monitor.interval,
        "batch_size": monitor.batch_size
    }


# ===== STARTUP/SHUTDOWN =====

@app.on_event("startup")
async def startup_event():
    """Initialize on server startup"""
    print("\n" + "="*50)
    print("🚀 PulseWatch NOC Server Starting")
    print("="*50)
    print(f"📍 API: http://localhost:8000")
    print(f"📊 Database: {db.db_path}")
    print(f"📡 WebSocket: ws://localhost:8000/ws")
    print("="*50 + "\n")
    
    # Load some test data if database is empty
    if len(db.get_all_devices()) == 0:
        print("📝 Adding sample devices for testing...")
        sample_devices = [
            ("Main Router", "192.168.1.1", "Router", "Cisco", "ASR1000", "Core Network"),
            ("Network Switch-1", "192.168.1.50", "Switch", "Juniper", "EX4300", "Core Network"),
            ("Network Switch-2", "192.168.1.51", "Switch", "Juniper", "EX4300", "Core Network"),
            ("Server-01", "192.168.2.10", "Server", "Dell", "PowerEdge R750", "Data Center"),
            ("Server-02", "192.168.2.11", "Server", "Dell", "PowerEdge R750", "Data Center"),
            ("Security Camera-1", "192.168.3.20", "Camera", "Hikvision", "DS-2DE7230IW", "Security"),
            ("Security Camera-2", "192.168.3.21", "Camera", "Hikvision", "DS-2DE7230IW", "Security"),
            ("Printer-1", "192.168.4.30", "Printer", "HP", "LaserJet M806", "Office"),
            ("PC-01", "192.168.5.40", "PC", "Dell", "OptiPlex 7090", "Office"),
            ("PC-02", "192.168.5.41", "PC", "Dell", "OptiPlex 7090", "Office"),
        ]
        
        for name, ip, dtype, vendor, model, group in sample_devices:
            db.add_device(name, ip, dtype, vendor, model, group)
        
        print(f"✅ Added {len(sample_devices)} sample devices\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    monitor.stop()
    db.close()
    print("\n✅ PulseWatch Server Shutdown Complete\n")


if __name__ == "__main__":
    import uvicorn
    
    # Run development server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
