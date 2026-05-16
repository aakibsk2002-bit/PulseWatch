"""PulseWatch Database Module - SQLite Setup & All Tables

This module initializes SQLite database with all required tables for:
- Device inventory and status
- Real-time monitoring data
- Alerts and events
- Topology and dependencies
- Maintenance schedules
- User management
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Database path - auto-create data folder
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "pulsewatch.db"


class Database:
    """SQLite Database Manager for PulseWatch"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.init_connection()
        self.create_tables()

    def init_connection(self):
        """Initialize database connection"""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            print(f"✅ Database connected: {self.db_path}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

    def create_tables(self):
        """Create all required tables if they don't exist"""
        try:
            # 1. DEVICES TABLE - Main device inventory
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    ip TEXT NOT NULL UNIQUE,
                    type TEXT DEFAULT 'Other',
                    vendor TEXT,
                    model TEXT,
                    group_name TEXT DEFAULT 'Default',
                    status TEXT DEFAULT 'unknown',
                    last_check TIMESTAMP,
                    response_time INTEGER,
                    uptime TEXT,
                    snmp_enabled BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Devices table created")

            # 2. DEVICE_STATUS TABLE - Status history for tracking
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    status TEXT,
                    response_time INTEGER,
                    packet_loss REAL,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            print("✅ Device status table created")

            # 3. ALERTS TABLE - Alert management
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    severity TEXT DEFAULT 'warning',
                    message TEXT NOT NULL,
                    acknowledged BOOLEAN DEFAULT 0,
                    resolved BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            print("✅ Alerts table created")

            # 4. EVENT_LOGS TABLE - System event logging
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT NOT NULL,
                    source TEXT,
                    device_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE SET NULL
                )
            """)
            print("✅ Event logs table created")

            # 5. DEPENDENCIES TABLE - Device relationships (parent-child)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parent_device_id INTEGER NOT NULL,
                    child_device_id INTEGER NOT NULL,
                    relationship_type TEXT DEFAULT 'connected_to',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(parent_device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    FOREIGN KEY(child_device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            print("✅ Dependencies table created")

            # 6. TOPOLOGY TABLE - Device positions for map visualization
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS topology (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    x_position REAL DEFAULT 0,
                    y_position REAL DEFAULT 0,
                    zoom_level REAL DEFAULT 1.0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            print("✅ Topology table created")

            # 7. MAINTENANCE TABLE - Scheduled maintenance windows
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS maintenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'scheduled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            print("✅ Maintenance table created")

            # 8. SETTINGS TABLE - Application configuration
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT,
                    type TEXT DEFAULT 'string',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("✅ Settings table created")

            # 9. USERS TABLE - Multi-user support (future)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'viewer',
                    email TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            print("✅ Users table created")

            self.conn.commit()
            print("\n✅ All database tables initialized successfully!\n")

        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise

    # ===== DEVICE OPERATIONS =====

    def add_device(self, name, ip, device_type="Other", vendor=None, model=None, group_name="Default"):
        """Add a new device to inventory"""
        try:
            self.cursor.execute("""
                INSERT INTO devices (name, ip, type, vendor, model, group_name, status)
                VALUES (?, ?, ?, ?, ?, ?, 'unknown')
            """, (name, ip, device_type, vendor, model, group_name))
            self.conn.commit()
            device_id = self.cursor.lastrowid
            
            # Add empty topology entry
            self.cursor.execute("""
                INSERT INTO topology (device_id, x_position, y_position)
                VALUES (?, ?, ?)
            """, (device_id, 0, 0))
            self.conn.commit()
            
            self.log_event("info", f"Device added: {name} ({ip})", device_id)
            return device_id
        except sqlite3.IntegrityError:
            print(f"❌ Device with IP {ip} already exists!")
            return None

    def get_all_devices(self):
        """Get all devices from inventory"""
        self.cursor.execute("SELECT * FROM devices ORDER BY name")
        return [dict(row) for row in self.cursor.fetchall()]

    def get_device(self, device_id):
        """Get specific device details"""
        self.cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_device_status(self, device_id, status, response_time=None):
        """Update device status after monitoring check"""
        self.cursor.execute("""
            UPDATE devices SET status = ?, response_time = ?, last_check = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, response_time, device_id))
        
        # Log status history
        self.cursor.execute("""
            INSERT INTO device_status (device_id, status, response_time, checked_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (device_id, status, response_time))
        
        self.conn.commit()

    def delete_device(self, device_id):
        """Delete device and all related data"""
        device = self.get_device(device_id)
        if device:
            self.cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
            self.conn.commit()
            self.log_event("info", f"Device deleted: {device['name']}")
            return True
        return False

    # ===== ALERT OPERATIONS =====

    def create_alert(self, device_id, severity, message):
        """Create alert for device event"""
        self.cursor.execute("""
            INSERT INTO alerts (device_id, severity, message, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (device_id, severity, message))
        self.conn.commit()
        alert_id = self.cursor.lastrowid
        self.log_event("warning", f"Alert created: {message}", device_id)
        return alert_id

    def get_active_alerts(self):
        """Get all unresolved alerts"""
        self.cursor.execute("""
            SELECT a.*, d.name as device_name, d.ip
            FROM alerts a
            JOIN devices d ON a.device_id = d.id
            WHERE a.resolved = 0
            ORDER BY a.created_at DESC
        """)
        return [dict(row) for row in self.cursor.fetchall()]

    def acknowledge_alert(self, alert_id):
        """Mark alert as acknowledged"""
        self.cursor.execute("""
            UPDATE alerts SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (alert_id,))
        self.conn.commit()

    def resolve_alert(self, alert_id):
        """Mark alert as resolved"""
        self.cursor.execute("""
            UPDATE alerts SET resolved = 1, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (alert_id,))
        self.conn.commit()

    # ===== EVENT LOG OPERATIONS =====

    def log_event(self, level, message, device_id=None):
        """Log system event"""
        self.cursor.execute("""
            INSERT INTO event_logs (level, message, device_id, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (level, message, device_id))
        self.conn.commit()

    def get_recent_logs(self, limit=100):
        """Get recent event logs"""
        self.cursor.execute("""
            SELECT l.*, d.name as device_name
            FROM event_logs l
            LEFT JOIN devices d ON l.device_id = d.id
            ORDER BY l.created_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    # ===== STATISTICS =====

    def get_stats(self):
        """Get dashboard statistics"""
        self.cursor.execute("SELECT COUNT(*) as total FROM devices")
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) as online FROM devices WHERE status = 'online'")
        online = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) as offline FROM devices WHERE status = 'offline'")
        offline = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) as alerts FROM alerts WHERE resolved = 0")
        alerts = self.cursor.fetchone()[0]
        
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "alerts": alerts,
            "health": round((online / total * 100), 2) if total > 0 else 0
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("✅ Database connection closed")


# Global database instance
db = Database()
