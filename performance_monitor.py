# ReviewCheckk Bot - Performance Monitoring System
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics
from debug_framework import debug_tracker, DebugLevel

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    name: str
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlatformStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_types: Dict[str, int] = field(default_factory=dict)
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None

class PerformanceMonitor:
    """Comprehensive performance monitoring system for the bot."""
    
    def __init__(self):
        self.metrics = deque(maxlen=10000)  # Keep last 10k metrics
        self.platform_stats = defaultdict(PlatformStats)
        self.system_stats = {
            'total_requests': 0,
            'total_successful': 0,
            'total_failed': 0,
            'uptime_start': time.time(),
            'peak_requests_per_minute': 0,
            'current_requests_per_minute': 0,
            'memory_usage_mb': 0,
            'active_users': set(),
            'response_time_percentiles': {}
        }
        
        # Request tracking for rate calculation
        self.request_timestamps = deque(maxlen=1000)
        self.active_requests = {}  # Track ongoing requests
        
        # Performance thresholds
        self.thresholds = {
            'response_time_warning': 10.0,  # seconds
            'response_time_critical': 30.0,  # seconds
            'success_rate_warning': 70.0,   # percentage
            'success_rate_critical': 50.0,  # percentage
            'requests_per_minute_warning': 100,
            'requests_per_minute_critical': 200
        }
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def start_request(self, request_id: str, user_id: int, platform: str, url: str) -> None:
        """Start tracking a request."""
        try:
            start_time = time.time()
            self.request_timestamps.append(start_time)
            
            self.active_requests[request_id] = {
                'user_id': user_id,
                'platform': platform,
                'url': url,
                'start_time': start_time,
                'stage': 'started'
            }
            
            self.system_stats['total_requests'] += 1
            self.system_stats['active_users'].add(user_id)
            self.platform_stats[platform].total_requests += 1
            
            # Update requests per minute
            self._update_request_rate()
            
            debug_tracker.log_event(
                DebugLevel.DEBUG, 'performance', 'request_started',
                f'Started tracking request {request_id}',
                {'platform': platform, 'user_id': user_id}
            )
            
        except Exception as e:
            logger.error(f"Error starting request tracking: {str(e)}")
    
    def update_request_stage(self, request_id: str, stage: str, metadata: Dict = None) -> None:
        """Update the current stage of a request."""
        try:
            if request_id in self.active_requests:
                self.active_requests[request_id]['stage'] = stage
                if metadata:
                    self.active_requests[request_id].update(metadata)
                
                # Log stage transitions for slow requests
                elapsed = time.time() - self.active_requests[request_id]['start_time']
                if elapsed > 5.0:  # Log if taking more than 5 seconds
                    debug_tracker.log_event(
                        DebugLevel.WARNING, 'performance', 'slow_request_stage',
                        f'Request {request_id} in stage {stage} after {elapsed:.2f}s',
                        {'stage': stage, 'elapsed_time': elapsed}
                    )
                    
        except Exception as e:
            logger.debug(f"Error updating request stage: {str(e)}")
    
    def end_request(self, request_id: str, success: bool, error_type: str = None, 
                   product_data: Dict = None) -> float:
        """End tracking a request and return response time."""
        try:
            if request_id not in self.active_requests:
                logger.warning(f"Request {request_id} not found in active requests")
                return 0.0
            
            request_info = self.active_requests.pop(request_id)
            end_time = time.time()
            response_time = end_time - request_info['start_time']
            
            platform = request_info['platform']
            platform_stat = self.platform_stats[platform]
            
            # Update platform statistics
            platform_stat.response_times.append(response_time)
            
            if success:
                self.system_stats['total_successful'] += 1
                platform_stat.successful_requests += 1
                platform_stat.last_success_time = end_time
            else:
                self.system_stats['total_failed'] += 1
                platform_stat.failed_requests += 1
                platform_stat.last_failure_time = end_time
                
                if error_type:
                    platform_stat.error_types[error_type] = platform_stat.error_types.get(error_type, 0) + 1
            
            # Update average response time
            if platform_stat.response_times:
                platform_stat.avg_response_time = statistics.mean(platform_stat.response_times)
            
            # Record performance metric
            self._record_metric('response_time', response_time, {
                'platform': platform,
                'success': success,
                'error_type': error_type,
                'user_id': request_info['user_id']
            })
            
            # Check for performance issues
            self._check_performance_thresholds(platform, response_time, success)
            
            debug_tracker.log_event(
                DebugLevel.INFO, 'performance', 'request_completed',
                f'Request {request_id} completed in {response_time:.2f}s',
                {
                    'response_time': response_time,
                    'success': success,
                    'platform': platform,
                    'error_type': error_type
                }
            )
            
            return response_time
            
        except Exception as e:
            logger.error(f"Error ending request tracking: {str(e)}")
            return 0.0
    
    def _record_metric(self, name: str, value: float, metadata: Dict = None) -> None:
        """Record a performance metric."""
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            self.metrics.append(metric)
            
        except Exception as e:
            logger.debug(f"Error recording metric: {str(e)}")
    
    def _update_request_rate(self) -> None:
        """Update requests per minute calculation."""
        try:
            current_time = time.time()
            one_minute_ago = current_time - 60
            
            # Count requests in the last minute
            recent_requests = [ts for ts in self.request_timestamps if ts > one_minute_ago]
            self.system_stats['current_requests_per_minute'] = len(recent_requests)
            
            # Update peak if necessary
            if len(recent_requests) > self.system_stats['peak_requests_per_minute']:
                self.system_stats['peak_requests_per_minute'] = len(recent_requests)
                
        except Exception as e:
            logger.debug(f"Error updating request rate: {str(e)}")
    
    def _check_performance_thresholds(self, platform: str, response_time: float, success: bool) -> None:
        """Check if performance metrics exceed thresholds."""
        try:
            # Check response time thresholds
            if response_time > self.thresholds['response_time_critical']:
                debug_tracker.log_event(
                    DebugLevel.CRITICAL, 'performance', 'response_time_critical',
                    f'Critical response time: {response_time:.2f}s for {platform}',
                    {'response_time': response_time, 'platform': platform}
                )
            elif response_time > self.thresholds['response_time_warning']:
                debug_tracker.log_event(
                    DebugLevel.WARNING, 'performance', 'response_time_warning',
                    f'Slow response time: {response_time:.2f}s for {platform}',
                    {'response_time': response_time, 'platform': platform}
                )
            
            # Check success rate thresholds
            platform_stat = self.platform_stats[platform]
            if platform_stat.total_requests >= 10:  # Only check after sufficient data
                success_rate = (platform_stat.successful_requests / platform_stat.total_requests) * 100
                
                if success_rate < self.thresholds['success_rate_critical']:
                    debug_tracker.log_event(
                        DebugLevel.CRITICAL, 'performance', 'success_rate_critical',
                        f'Critical success rate: {success_rate:.1f}% for {platform}',
                        {'success_rate': success_rate, 'platform': platform}
                    )
                elif success_rate < self.thresholds['success_rate_warning']:
                    debug_tracker.log_event(
                        DebugLevel.WARNING, 'performance', 'success_rate_warning',
                        f'Low success rate: {success_rate:.1f}% for {platform}',
                        {'success_rate': success_rate, 'platform': platform}
                    )
            
            # Check request rate thresholds
            current_rpm = self.system_stats['current_requests_per_minute']
            if current_rpm > self.thresholds['requests_per_minute_critical']:
                debug_tracker.log_event(
                    DebugLevel.CRITICAL, 'performance', 'high_request_rate',
                    f'Critical request rate: {current_rpm} requests/minute',
                    {'requests_per_minute': current_rpm}
                )
            elif current_rpm > self.thresholds['requests_per_minute_warning']:
                debug_tracker.log_event(
                    DebugLevel.WARNING, 'performance', 'elevated_request_rate',
                    f'High request rate: {current_rpm} requests/minute',
                    {'requests_per_minute': current_rpm}
                )
                
        except Exception as e:
            logger.debug(f"Error checking performance thresholds: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        try:
            current_time = time.time()
            uptime_seconds = current_time - self.system_stats['uptime_start']
            uptime_hours = uptime_seconds / 3600
            
            # Calculate overall success rate
            total_requests = self.system_stats['total_requests']
            overall_success_rate = 0.0
            if total_requests > 0:
                overall_success_rate = (self.system_stats['total_successful'] / total_requests) * 100
            
            # Calculate response time percentiles
            all_response_times = []
            for platform_stat in self.platform_stats.values():
                all_response_times.extend(list(platform_stat.response_times))
            
            percentiles = {}
            if all_response_times:
                percentiles = {
                    'p50': statistics.median(all_response_times),
                    'p90': statistics.quantiles(all_response_times, n=10)[8] if len(all_response_times) >= 10 else max(all_response_times),
                    'p95': statistics.quantiles(all_response_times, n=20)[18] if len(all_response_times) >= 20 else max(all_response_times),
                    'p99': statistics.quantiles(all_response_times, n=100)[98] if len(all_response_times) >= 100 else max(all_response_times)
                }
            
            # Platform-specific summaries
            platform_summaries = {}
            for platform, stats in self.platform_stats.items():
                success_rate = 0.0
                if stats.total_requests > 0:
                    success_rate = (stats.successful_requests / stats.total_requests) * 100
                
                platform_summaries[platform] = {
                    'total_requests': stats.total_requests,
                    'success_rate': round(success_rate, 1),
                    'avg_response_time': round(stats.avg_response_time, 2),
                    'top_errors': dict(sorted(stats.error_types.items(), key=lambda x: x[1], reverse=True)[:3])
                }
            
            return {
                'system_overview': {
                    'uptime_hours': round(uptime_hours, 1),
                    'total_requests': total_requests,
                    'overall_success_rate': round(overall_success_rate, 1),
                    'current_requests_per_minute': self.system_stats['current_requests_per_minute'],
                    'peak_requests_per_minute': self.system_stats['peak_requests_per_minute'],
                    'active_users_count': len(self.system_stats['active_users']),
                    'active_requests_count': len(self.active_requests)
                },
                'response_times': {
                    'percentiles': {k: round(v, 2) for k, v in percentiles.items()},
                    'average': round(statistics.mean(all_response_times), 2) if all_response_times else 0.0
                },
                'platform_performance': platform_summaries,
                'health_status': self._get_health_status()
            }
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {str(e)}")
            return {'error': 'Failed to generate performance summary'}
    
    def _get_health_status(self) -> str:
        """Determine overall system health status."""
        try:
            total_requests = self.system_stats['total_requests']
            if total_requests == 0:
                return 'UNKNOWN'
            
            overall_success_rate = (self.system_stats['total_successful'] / total_requests) * 100
            current_rpm = self.system_stats['current_requests_per_minute']
            
            # Get recent response times
            recent_response_times = []
            for platform_stat in self.platform_stats.values():
                recent_response_times.extend(list(platform_stat.response_times)[-10:])  # Last 10 per platform
            
            avg_recent_response_time = statistics.mean(recent_response_times) if recent_response_times else 0
            
            # Determine health based on multiple factors
            if (overall_success_rate >= 90 and 
                avg_recent_response_time < 5.0 and 
                current_rpm < self.thresholds['requests_per_minute_warning']):
                return 'HEALTHY'
            elif (overall_success_rate >= 70 and 
                  avg_recent_response_time < 15.0 and 
                  current_rpm < self.thresholds['requests_per_minute_critical']):
                return 'WARNING'
            else:
                return 'CRITICAL'
                
        except Exception as e:
            logger.debug(f"Error determining health status: {str(e)}")
            return 'UNKNOWN'
    
    def _start_background_monitoring(self) -> None:
        """Start background thread for periodic monitoring tasks."""
        def background_monitor():
            while True:
                try:
                    time.sleep(60)  # Run every minute
                    
                    # Clean up old active users (inactive for 1 hour)
                    current_time = time.time()
                    one_hour_ago = current_time - 3600
                    
                    # Update memory usage (simplified)
                    import psutil
                    import os
                    process = psutil.Process(os.getpid())
                    self.system_stats['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024
                    
                    # Log periodic health check
                    health_status = self._get_health_status()
                    debug_tracker.log_event(
                        DebugLevel.INFO, 'performance', 'health_check',
                        f'System health: {health_status}',
                        {
                            'health_status': health_status,
                            'active_requests': len(self.active_requests),
                            'requests_per_minute': self.system_stats['current_requests_per_minute']
                        }
                    )
                    
                except Exception as e:
                    logger.debug(f"Error in background monitoring: {str(e)}")
        
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
    
    def get_platform_insights(self, platform: str) -> Dict[str, Any]:
        """Get detailed insights for a specific platform."""
        try:
            if platform not in self.platform_stats:
                return {'error': f'No data available for platform: {platform}'}
            
            stats = self.platform_stats[platform]
            
            # Calculate trends (last 10 vs previous 10 requests)
            response_times = list(stats.response_times)
            trend = 'stable'
            if len(response_times) >= 20:
                recent_avg = statistics.mean(response_times[-10:])
                previous_avg = statistics.mean(response_times[-20:-10])
                if recent_avg > previous_avg * 1.2:
                    trend = 'degrading'
                elif recent_avg < previous_avg * 0.8:
                    trend = 'improving'
            
            success_rate = 0.0
            if stats.total_requests > 0:
                success_rate = (stats.successful_requests / stats.total_requests) * 100
            
            return {
                'platform': platform,
                'total_requests': stats.total_requests,
                'success_rate': round(success_rate, 1),
                'avg_response_time': round(stats.avg_response_time, 2),
                'performance_trend': trend,
                'top_errors': dict(sorted(stats.error_types.items(), key=lambda x: x[1], reverse=True)[:5]),
                'last_success': datetime.fromtimestamp(stats.last_success_time).isoformat() if stats.last_success_time else None,
                'last_failure': datetime.fromtimestamp(stats.last_failure_time).isoformat() if stats.last_failure_time else None,
                'recommendations': self._generate_platform_recommendations(platform, stats)
            }
            
        except Exception as e:
            logger.error(f"Error getting platform insights: {str(e)}")
            return {'error': 'Failed to generate platform insights'}
    
    def _generate_platform_recommendations(self, platform: str, stats: PlatformStats) -> List[str]:
        """Generate performance recommendations for a platform."""
        recommendations = []
        
        try:
            success_rate = (stats.successful_requests / stats.total_requests) * 100 if stats.total_requests > 0 else 0
            
            if success_rate < 50:
                recommendations.append(f"Critical: {platform} success rate is very low. Check selectors and page structure.")
            elif success_rate < 70:
                recommendations.append(f"Warning: {platform} success rate could be improved. Review extraction logic.")
            
            if stats.avg_response_time > 15:
                recommendations.append(f"High response times for {platform}. Consider optimizing requests or adding caching.")
            elif stats.avg_response_time > 8:
                recommendations.append(f"Moderate response times for {platform}. Monitor for further degradation.")
            
            # Error-specific recommendations
            top_error = max(stats.error_types.items(), key=lambda x: x[1]) if stats.error_types else None
            if top_error:
                error_type, count = top_error
                if count > stats.total_requests * 0.3:  # More than 30% of requests
                    recommendations.append(f"Frequent {error_type} errors on {platform}. Investigate root cause.")
            
            if not recommendations:
                recommendations.append(f"{platform} performance is within acceptable ranges.")
            
        except Exception as e:
            logger.debug(f"Error generating recommendations: {str(e)}")
            recommendations.append("Unable to generate recommendations due to insufficient data.")
        
        return recommendations

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Convenience functions
def start_performance_tracking(request_id: str, user_id: int, platform: str, url: str) -> None:
    """Start tracking request performance."""
    performance_monitor.start_request(request_id, user_id, platform, url)

def update_performance_stage(request_id: str, stage: str, metadata: Dict = None) -> None:
    """Update request processing stage."""
    performance_monitor.update_request_stage(request_id, stage, metadata)

def end_performance_tracking(request_id: str, success: bool, error_type: str = None, 
                           product_data: Dict = None) -> float:
    """End tracking and return response time."""
    return performance_monitor.end_request(request_id, success, error_type, product_data)

def get_performance_report() -> str:
    """Get formatted performance report."""
    try:
        summary = performance_monitor.get_performance_summary()
        
        report = []
        report.append("=== PERFORMANCE REPORT ===")
        report.append("")
        
        # System Overview
        system = summary.get('system_overview', {})
        report.append("SYSTEM OVERVIEW:")
        report.append(f"  Uptime: {system.get('uptime_hours', 0)} hours")
        report.append(f"  Total Requests: {system.get('total_requests', 0)}")
        report.append(f"  Success Rate: {system.get('overall_success_rate', 0)}%")
        report.append(f"  Current Load: {system.get('current_requests_per_minute', 0)} req/min")
        report.append(f"  Peak Load: {system.get('peak_requests_per_minute', 0)} req/min")
        report.append(f"  Active Users: {system.get('active_users_count', 0)}")
        report.append(f"  Health Status: {summary.get('health_status', 'UNKNOWN')}")
        report.append("")
        
        # Response Times
        response_times = summary.get('response_times', {})
        percentiles = response_times.get('percentiles', {})
        if percentiles:
            report.append("RESPONSE TIMES:")
            report.append(f"  Average: {response_times.get('average', 0)}s")
            report.append(f"  50th percentile: {percentiles.get('p50', 0)}s")
            report.append(f"  90th percentile: {percentiles.get('p90', 0)}s")
            report.append(f"  95th percentile: {percentiles.get('p95', 0)}s")
            report.append("")
        
        # Platform Performance
        platforms = summary.get('platform_performance', {})
        if platforms:
            report.append("PLATFORM PERFORMANCE:")
            for platform, stats in platforms.items():
                report.append(f"  {platform.upper()}:")
                report.append(f"    Requests: {stats.get('total_requests', 0)}")
                report.append(f"    Success Rate: {stats.get('success_rate', 0)}%")
                report.append(f"    Avg Response: {stats.get('avg_response_time', 0)}s")
                
                top_errors = stats.get('top_errors', {})
                if top_errors:
                    report.append(f"    Top Errors: {', '.join([f'{k}({v})' for k, v in list(top_errors.items())[:2]])}")
        
        return "\n".join(report)
        
    except Exception as e:
        logger.error(f"Error generating performance report: {str(e)}")
        return "Error generating performance report"
