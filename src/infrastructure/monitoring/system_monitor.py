"""System monitoring and alerting"""
import asyncio
import psutil
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger
import json

@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, int]
    active_connections: int
    redis_memory: Optional[float] = None
    redis_connections: Optional[int] = None

@dataclass
class Alert:
    id: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    title: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None

class SystemMonitor:
    def __init__(self, redis_client=None, alert_callback=None):
        self.redis_client = redis_client
        self.alert_callback = alert_callback
        self.alerts: List[Alert] = []
        self.metrics_history: List[SystemMetrics] = []
        self.thresholds = {
            'cpu_usage': 80.0,      # CPU usage %
            'memory_usage': 85.0,   # Memory usage %
            'disk_usage': 90.0,     # Disk usage %
            'redis_memory': 1024,   # Redis memory MB
            'connection_latency': 1000,  # Latency ms
            'error_rate': 0.05      # Error rate %
        }
        
    async def start_monitoring(self):
        """Start system monitoring loop"""
        logger.info("Starting system monitoring...")
        
        monitoring_tasks = [
            asyncio.create_task(self._monitor_system_resources()),
            asyncio.create_task(self._monitor_redis_health()),
            asyncio.create_task(self._monitor_exchange_connections()),
            asyncio.create_task(self._monitor_trading_performance()),
            asyncio.create_task(self._cleanup_old_data())
        ]
        
        await asyncio.gather(*monitoring_tasks)
    
    async def _monitor_system_resources(self):
        """Monitor CPU, memory, disk usage"""
        while True:
            try:
                # Get system metrics
                cpu_usage = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                network = psutil.net_io_counters()
                
                # Count active network connections
                connections = len(psutil.net_connections())
                
                metrics = SystemMetrics(
                    timestamp=datetime.now(),
                    cpu_usage=cpu_usage,
                    memory_usage=memory.percent,
                    disk_usage=disk.percent,
                    network_io={
                        'bytes_sent': network.bytes_sent,
                        'bytes_recv': network.bytes_recv
                    },
                    active_connections=connections
                )
                
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics (last 1000 points)
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
                
                # Check for alerts
                await self._check_resource_alerts(metrics)
                
                # Store in Redis
                if self.redis_client:
                    await self._store_metrics(metrics)
                
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _monitor_redis_health(self):
        """Monitor Redis health and performance"""
        while True:
            try:
                if self.redis_client:
                    # Get Redis info
                    redis_info = await self.redis_client.info()
                    
                    memory_mb = redis_info.get('used_memory', 0) / (1024 * 1024)
                    connections = redis_info.get('connected_clients', 0)
                    
                    # Update latest metrics
                    if self.metrics_history:
                        self.metrics_history[-1].redis_memory = memory_mb
                        self.metrics_history[-1].redis_connections = connections
                    
                    # Check Redis-specific alerts
                    if memory_mb > self.thresholds['redis_memory']:
                        await self._create_alert(
                            'high',
                            'High Redis Memory Usage',
                            f'Redis using {memory_mb:.1f}MB (threshold: {self.thresholds["redis_memory"]}MB)'
                        )
                    
                    if connections > 100:  # Redis connection limit alert
                        await self._create_alert(
                            'medium',
                            'High Redis Connections',
                            f'Redis has {connections} active connections'
                        )
                
            except Exception as e:
                logger.error(f"Redis monitoring error: {e}")
                await self._create_alert(
                    'critical',
                    'Redis Connection Lost',
                    f'Cannot connect to Redis: {e}'
                )
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _monitor_exchange_connections(self):
        """Monitor exchange connection health"""
        while True:
            try:
                # This would integrate with the exchange manager
                # For now, simulate connection monitoring
                
                # Check latencies and create alerts for slow connections
                # This would be implemented with actual exchange manager integration
                
                logger.debug("Exchange connection monitoring (placeholder)")
                
            except Exception as e:
                logger.error(f"Exchange monitoring error: {e}")
            
            await asyncio.sleep(120)  # Check every 2 minutes
    
    async def _monitor_trading_performance(self):
        """Monitor trading performance and create alerts"""
        while True:
            try:
                # This would integrate with performance tracker
                # Monitor for:
                # - High error rates
                # - Unusual losses
                # - System performance degradation
                
                logger.debug("Trading performance monitoring (placeholder)")
                
            except Exception as e:
                logger.error(f"Trading performance monitoring error: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _check_resource_alerts(self, metrics: SystemMetrics):
        """Check system resources against thresholds"""
        
        # CPU usage alert
        if metrics.cpu_usage > self.thresholds['cpu_usage']:
            await self._create_alert(
                'high' if metrics.cpu_usage > 90 else 'medium',
                'High CPU Usage',
                f'CPU usage at {metrics.cpu_usage:.1f}%'
            )
        
        # Memory usage alert
        if metrics.memory_usage > self.thresholds['memory_usage']:
            await self._create_alert(
                'high' if metrics.memory_usage > 95 else 'medium',
                'High Memory Usage',
                f'Memory usage at {metrics.memory_usage:.1f}%'
            )
        
        # Disk usage alert
        if metrics.disk_usage > self.thresholds['disk_usage']:
            await self._create_alert(
                'critical' if metrics.disk_usage > 95 else 'high',
                'High Disk Usage',
                f'Disk usage at {metrics.disk_usage:.1f}%'
            )
    
    async def _create_alert(self, severity: str, title: str, message: str):
        """Create and process an alert"""
        alert_id = f"{int(time.time())}_{len(self.alerts)}"
        
        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            message=message,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # Log the alert
        log_func = logger.critical if severity == 'critical' else \
                  logger.error if severity == 'high' else \
                  logger.warning if severity == 'medium' else \
                  logger.info
        
        log_func(f"ALERT [{severity.upper()}]: {title} - {message}")
        
        # Call alert callback if provided
        if self.alert_callback:
            try:
                await self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        # Store in Redis
        if self.redis_client:
            await self._store_alert(alert)
    
    async def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in Redis"""
        try:
            metrics_key = f"system_metrics:{int(metrics.timestamp.timestamp())}"
            metrics_data = {
                'timestamp': metrics.timestamp.isoformat(),
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'disk_usage': metrics.disk_usage,
                'network_bytes_sent': metrics.network_io['bytes_sent'],
                'network_bytes_recv': metrics.network_io['bytes_recv'],
                'active_connections': metrics.active_connections
            }
            
            if metrics.redis_memory:
                metrics_data['redis_memory'] = metrics.redis_memory
            if metrics.redis_connections:
                metrics_data['redis_connections'] = metrics.redis_connections
            
            await self.redis_client.hset(metrics_key, mapping=metrics_data)
            await self.redis_client.expire(metrics_key, 86400)  # Keep for 24 hours
            
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    async def _store_alert(self, alert: Alert):
        """Store alert in Redis"""
        try:
            alert_key = f"alert:{alert.id}"
            alert_data = {
                'id': alert.id,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            
            await self.redis_client.hset(alert_key, mapping=alert_data)
            await self.redis_client.expire(alert_key, 86400 * 7)  # Keep for 7 days
            
            # Add to severity-based sorted set
            await self.redis_client.zadd(
                f"alerts:{alert.severity}",
                {alert.id: alert.timestamp.timestamp()}
            )
            
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        while True:
            try:
                # Keep only recent alerts (last 100)
                if len(self.alerts) > 100:
                    self.alerts = self.alerts[-100:]
                
                # Clean up old Redis data
                if self.redis_client:
                    cutoff_time = time.time() - 86400  # 24 hours ago
                    
                    # Clean old metrics
                    pattern = "system_metrics:*"
                    keys = await self.redis_client.keys(pattern)
                    for key in keys:
                        timestamp = int(key.split(':')[1])
                        if timestamp < cutoff_time:
                            await self.redis_client.delete(key)
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            
            await asyncio.sleep(3600)  # Clean every hour
    
    async def get_system_status(self) -> Dict:
        """Get current system status"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        latest_metrics = self.metrics_history[-1]
        active_alerts = [a for a in self.alerts if not a.resolved]
        
        # Determine overall status
        critical_alerts = [a for a in active_alerts if a.severity == 'critical']
        high_alerts = [a for a in active_alerts if a.severity == 'high']
        
        if critical_alerts:
            status = 'critical'
        elif high_alerts:
            status = 'warning'
        elif latest_metrics.cpu_usage > 70 or latest_metrics.memory_usage > 80:
            status = 'caution'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'metrics': {
                'cpu_usage': latest_metrics.cpu_usage,
                'memory_usage': latest_metrics.memory_usage,
                'disk_usage': latest_metrics.disk_usage,
                'active_connections': latest_metrics.active_connections,
                'redis_memory': latest_metrics.redis_memory,
                'redis_connections': latest_metrics.redis_connections
            },
            'active_alerts': len(active_alerts),
            'alert_breakdown': {
                'critical': len([a for a in active_alerts if a.severity == 'critical']),
                'high': len([a for a in active_alerts if a.severity == 'high']),
                'medium': len([a for a in active_alerts if a.severity == 'medium']),
                'low': len([a for a in active_alerts if a.severity == 'low'])
            },
            'timestamp': latest_metrics.timestamp.isoformat()
        }
