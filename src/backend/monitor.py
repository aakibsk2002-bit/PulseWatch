"""PulseWatch Monitoring Engine - Async Device Monitoring

This module handles:
- Concurrent PING monitoring for 5000+ devices
- Batch processing to prevent resource exhaustion
- Status change detection and alert generation
- Real-time WebSocket updates
- Configurable monitoring intervals
"""

import asyncio
import time
from datetime import datetime
import subprocess
import platform
from typing import List, Dict, Optional
from database import db


class MonitoringEngine:
    """Async monitoring engine for PulseWatch"""

    def __init__(self, batch_size=100, timeout=5, interval=10):
        """
        Initialize monitoring engine
        
        Args:
            batch_size: Devices to ping concurrently (default: 100)
            timeout: Ping timeout in seconds (default: 5)
            interval: Monitoring interval in seconds (default: 10)
        """
        self.batch_size = batch_size
        self.timeout = timeout
        self.interval = interval
        self.is_running = False
        self.last_run = None
        self.device_cache = {}

    @staticmethod
    async def ping_device(ip: str, timeout: int = 5) -> Dict:
        """
        Async ping a single device
        
        Returns:
            {
                'ip': str,
                'online': bool,
                'response_time': int (milliseconds),
                'timestamp': datetime
            }
        """
        try:
            # Different ping commands for different OS
            if platform.system() == "Windows":
                cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout + 1)
                output = stdout.decode()
                
                # Check if successful
                if result.returncode == 0:
                    # Extract response time
                    if "time=" in output:
                        response_time = int(output.split("time=")[1].split("ms")[0])
                        return {
                            "ip": ip,
                            "online": True,
                            "response_time": response_time,
                            "timestamp": datetime.now()
                        }
            else:
                # Linux/Mac ping
                cmd = ["ping", "-c", "1", "-W", str(timeout), ip]
                result = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=timeout + 1)
                output = stdout.decode()
                
                if result.returncode == 0:
                    if "time=" in output:
                        response_time = float(output.split("time=")[1].split(" ")[0])
                        return {
                            "ip": ip,
                            "online": True,
                            "response_time": int(response_time),
                            "timestamp": datetime.now()
                        }
            
            # Device offline
            return {
                "ip": ip,
                "online": False,
                "response_time": None,
                "timestamp": datetime.now()
            }

        except asyncio.TimeoutError:
            return {
                "ip": ip,
                "online": False,
                "response_time": None,
                "timestamp": datetime.now()
            }
        except Exception as e:
            print(f"❌ Ping error for {ip}: {e}")
            return {
                "ip": ip,
                "online": False,
                "response_time": None,
                "timestamp": datetime.now()
            }

    async def check_batch(self, devices: List[Dict]) -> List[Dict]:
        """
        Check a batch of devices concurrently
        
        Args:
            devices: List of device dictionaries from database
            
        Returns:
            List of ping results
        """
        tasks = []
        for device in devices:
            task = self.ping_device(device["ip"], self.timeout)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

    def process_results(self, results: List[Dict], devices_map: Dict):
        """
        Process ping results and update database
        
        Args:
            results: Ping results from check_batch
            devices_map: Mapping of IP to device ID
        """
        for result in results:
            ip = result["ip"]
            device_id = devices_map.get(ip)
            
            if not device_id:
                continue
            
            # Determine new status
            new_status = "online" if result["online"] else "offline"
            old_device = db.get_device(device_id)
            old_status = old_device["status"] if old_device else "unknown"
            
            # Update device status in database
            db.update_device_status(
                device_id,
                new_status,
                result["response_time"]
            )
            
            # Check for status change and create alert if needed
            if old_status != new_status:
                if new_status == "offline":
                    # Device went DOWN - create CRITICAL alert
                    db.create_alert(
                        device_id,
                        "critical",
                        f"Device {ip} is now OFFLINE"
                    )
                    print(f"🔴 OFFLINE: {ip}")
                elif new_status == "online" and old_status == "offline":
                    # Device came BACK UP - create INFO alert
                    db.create_alert(
                        device_id,
                        "info",
                        f"Device {ip} is back ONLINE"
                    )
                    print(f"🟢 ONLINE: {ip}")

    async def monitor_all_devices(self):
        """
        Monitor all devices in batches
        
        This is the main monitoring loop that:
        1. Fetches all devices
        2. Splits them into batches
        3. Pings each batch concurrently
        4. Updates database with results
        5. Generates alerts for status changes
        """
        try:
            devices = db.get_all_devices()
            if not devices:
                print("⚠️  No devices to monitor")
                return []
            
            # Create IP to device_id mapping
            devices_map = {d["ip"]: d["id"] for d in devices}
            
            print(f"\n📊 Monitoring {len(devices)} devices...")
            start_time = time.time()
            
            all_results = []
            
            # Process devices in batches
            for i in range(0, len(devices), self.batch_size):
                batch = devices[i:i + self.batch_size]
                print(f"  📍 Batch {i//self.batch_size + 1}: Processing {len(batch)} devices...")
                
                results = await self.check_batch(batch)
                all_results.extend(results)
                self.process_results(results, devices_map)
            
            elapsed = time.time() - start_time
            stats = db.get_stats()
            
            print(f"✅ Monitoring complete in {elapsed:.2f}s")
            print(f"   Total: {stats['total']} | Online: {stats['online']} | Offline: {stats['offline']} | Alerts: {stats['alerts']}")
            print(f"   Network Health: {stats['health']}%\n")
            
            self.last_run = datetime.now()
            return all_results

        except Exception as e:
            print(f"❌ Monitoring error: {e}")
            db.log_event("error", f"Monitoring error: {e}")
            return []

    async def run_monitor_loop(self):
        """
        Main monitoring loop - runs continuously
        """
        self.is_running = True
        print(f"\n🚀 Monitoring Engine Started (Interval: {self.interval}s, Batch: {self.batch_size})\n")
        
        try:
            while self.is_running:
                await self.monitor_all_devices()
                await asyncio.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\n⛔ Monitoring stopped by user")
            self.is_running = False
        except Exception as e:
            print(f"❌ Monitor loop error: {e}")
            db.log_event("error", f"Monitor loop error: {e}")

    def stop(self):
        """Stop monitoring engine"""
        self.is_running = False
        print("⛔ Monitoring engine stopped")


# Global monitor instance
monitor = MonitoringEngine(batch_size=100, timeout=5, interval=10)
