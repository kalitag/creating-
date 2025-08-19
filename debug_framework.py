# ReviewCheckk Bot - Comprehensive Debug Framework
import logging
import json
import time
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

class DebugLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class DebugEvent:
    timestamp: float
    level: DebugLevel
    component: str
    event_type: str
    message: str
    data: Dict[str, Any]
    stack_trace: Optional[str] = None
    user_id: Optional[int] = None
    url: Optional[str] = None

class DebugTracker:
    """Comprehensive debug tracking system for bot analysis."""
    
    def __init__(self):
        self.events: List[DebugEvent] = []
        self.session_stats = {
            'total_requests': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'platform_stats': {},
            'error_patterns': {},
            'response_times': [],
            'session_start': time.time()
        }
        self.max_events = 1000  # Keep last 1000 events
        
    def log_event(self, level: DebugLevel, component: str, event_type: str, 
                  message: str, data: Dict[str, Any] = None, 
                  user_id: int = None, url: str = None):
        """Log a debug event with comprehensive context."""
        event = DebugEvent(
            timestamp=time.time(),
            level=level,
            component=component,
            event_type=event_type,
            message=message,
            data=data or {},
            stack_trace=traceback.format_stack() if level in [DebugLevel.ERROR, DebugLevel.CRITICAL] else None,
            user_id=user_id,
            url=url
        )
        
        self.events.append(event)
        
        # Keep only recent events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Update session stats
        self._update_session_stats(event)
        
        # Log to standard logger
        logger = logging.getLogger(__name__)
        log_message = f"[{component}:{event_type}] {message}"
        if data:
            log_message += f" | Data: {json.dumps(data, default=str)}"
        
        if level == DebugLevel.CRITICAL:
            logger.critical(log_message)
        elif level == DebugLevel.ERROR:
            logger.error(log_message)
        elif level == DebugLevel.WARNING:
            logger.warning(log_message)
        elif level == DebugLevel.INFO:
            logger.info(log_message)
        else:
            logger.debug(log_message)
    
    def _update_session_stats(self, event: DebugEvent):
        """Update session statistics based on events."""
        if event.event_type == 'request_start':
            self.session_stats['total_requests'] += 1
        elif event.event_type == 'extraction_success':
            self.session_stats['successful_extractions'] += 1
        elif event.event_type == 'extraction_failed':
            self.session_stats['failed_extractions'] += 1
        
        # Track platform stats
        if event.data and 'platform' in event.data:
            platform = event.data['platform']
            if platform not in self.session_stats['platform_stats']:
                self.session_stats['platform_stats'][platform] = {
                    'attempts': 0, 'successes': 0, 'failures': 0
                }
            
            if event.event_type == 'extraction_attempt':
                self.session_stats['platform_stats'][platform]['attempts'] += 1
            elif event.event_type == 'extraction_success':
                self.session_stats['platform_stats'][platform]['successes'] += 1
            elif event.event_type == 'extraction_failed':
                self.session_stats['platform_stats'][platform]['failures'] += 1
        
        # Track error patterns
        if event.level in [DebugLevel.ERROR, DebugLevel.CRITICAL]:
            error_key = f"{event.component}:{event.event_type}"
            if error_key not in self.session_stats['error_patterns']:
                self.session_stats['error_patterns'][error_key] = 0
            self.session_stats['error_patterns'][error_key] += 1
        
        # Track response times
        if event.data and 'response_time' in event.data:
            self.session_stats['response_times'].append(event.data['response_time'])
    
    def get_recent_events(self, count: int = 50, level: DebugLevel = None) -> List[DebugEvent]:
        """Get recent debug events, optionally filtered by level."""
        events = self.events[-count:] if not level else [
            e for e in self.events[-count:] if e.level == level
        ]
        return sorted(events, key=lambda x: x.timestamp, reverse=True)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error analysis."""
        recent_errors = self.get_recent_events(100, DebugLevel.ERROR)
        critical_errors = self.get_recent_events(100, DebugLevel.CRITICAL)
        
        error_types = {}
        for error in recent_errors + critical_errors:
            error_type = f"{error.component}:{error.event_type}"
            if error_type not in error_types:
                error_types[error_type] = {
                    'count': 0,
                    'last_occurrence': None,
                    'sample_message': None,
                    'affected_urls': set(),
                    'affected_users': set()
                }
            
            error_types[error_type]['count'] += 1
            error_types[error_type]['last_occurrence'] = error.timestamp
            error_types[error_type]['sample_message'] = error.message
            
            if error.url:
                error_types[error_type]['affected_urls'].add(error.url)
            if error.user_id:
                error_types[error_type]['affected_users'].add(error.user_id)
        
        # Convert sets to lists for JSON serialization
        for error_type in error_types:
            error_types[error_type]['affected_urls'] = list(error_types[error_type]['affected_urls'])
            error_types[error_type]['affected_users'] = list(error_types[error_type]['affected_users'])
        
        return {
            'total_errors': len(recent_errors),
            'total_critical': len(critical_errors),
            'error_types': error_types,
            'session_stats': self.session_stats
        }
    
    def get_platform_analysis(self) -> Dict[str, Any]:
        """Analyze performance by platform."""
        platform_analysis = {}
        
        for platform, stats in self.session_stats['platform_stats'].items():
            success_rate = (stats['successes'] / stats['attempts'] * 100) if stats['attempts'] > 0 else 0
            
            # Get recent events for this platform
            platform_events = [
                e for e in self.events[-200:] 
                if e.data and e.data.get('platform') == platform
            ]
            
            # Analyze common failure reasons
            failure_reasons = {}
            for event in platform_events:
                if event.level == DebugLevel.ERROR and event.event_type == 'extraction_failed':
                    reason = event.message
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            
            platform_analysis[platform] = {
                'attempts': stats['attempts'],
                'successes': stats['successes'],
                'failures': stats['failures'],
                'success_rate': round(success_rate, 2),
                'common_failures': dict(sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5])
            }
        
        return platform_analysis
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance analysis."""
        response_times = self.session_stats['response_times']
        
        if not response_times:
            return {'message': 'No response time data available'}
        
        avg_response_time = sum(response_times) / len(response_times)
        slow_requests = [rt for rt in response_times if rt > 10.0]  # > 10 seconds
        
        return {
            'total_requests': len(response_times),
            'average_response_time': round(avg_response_time, 2),
            'slow_requests_count': len(slow_requests),
            'slow_requests_percentage': round(len(slow_requests) / len(response_times) * 100, 2),
            'fastest_response': min(response_times),
            'slowest_response': max(response_times)
        }
    
    def generate_debug_report(self) -> str:
        """Generate comprehensive debug report."""
        error_summary = self.get_error_summary()
        platform_analysis = self.get_platform_analysis()
        performance_metrics = self.get_performance_metrics()
        
        report = []
        report.append("=== REVIEWCHECKK BOT DEBUG REPORT ===")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Session Duration: {time.time() - self.session_stats['session_start']:.0f} seconds")
        report.append("")
        
        # Session Overview
        report.append("SESSION OVERVIEW:")
        report.append(f"  Total Requests: {self.session_stats['total_requests']}")
        report.append(f"  Successful Extractions: {self.session_stats['successful_extractions']}")
        report.append(f"  Failed Extractions: {self.session_stats['failed_extractions']}")
        
        if self.session_stats['total_requests'] > 0:
            success_rate = (self.session_stats['successful_extractions'] / self.session_stats['total_requests']) * 100
            report.append(f"  Overall Success Rate: {success_rate:.1f}%")
        report.append("")
        
        # Error Analysis
        report.append("ERROR ANALYSIS:")
        report.append(f"  Total Errors: {error_summary['total_errors']}")
        report.append(f"  Critical Errors: {error_summary['total_critical']}")
        
        if error_summary['error_types']:
            report.append("  Top Error Types:")
            for error_type, details in sorted(error_summary['error_types'].items(), 
                                            key=lambda x: x[1]['count'], reverse=True)[:5]:
                report.append(f"    {error_type}: {details['count']} occurrences")
                report.append(f"      Sample: {details['sample_message']}")
        report.append("")
        
        # Platform Analysis
        report.append("PLATFORM ANALYSIS:")
        for platform, stats in platform_analysis.items():
            report.append(f"  {platform.upper()}:")
            report.append(f"    Attempts: {stats['attempts']}")
            report.append(f"    Success Rate: {stats['success_rate']}%")
            if stats['common_failures']:
                report.append(f"    Common Failures:")
                for failure, count in list(stats['common_failures'].items())[:3]:
                    report.append(f"      - {failure}: {count} times")
        report.append("")
        
        # Performance Metrics
        report.append("PERFORMANCE METRICS:")
        if isinstance(performance_metrics, dict) and 'total_requests' in performance_metrics:
            report.append(f"  Average Response Time: {performance_metrics['average_response_time']}s")
            report.append(f"  Slow Requests (>10s): {performance_metrics['slow_requests_percentage']}%")
            report.append(f"  Fastest Response: {performance_metrics['fastest_response']}s")
            report.append(f"  Slowest Response: {performance_metrics['slowest_response']}s")
        else:
            report.append("  No performance data available")
        
        return "\n".join(report)

# Global debug tracker instance
debug_tracker = DebugTracker()

# Convenience functions for common debug operations
def log_request_start(user_id: int, url: str, platform: str = None):
    """Log the start of a request."""
    debug_tracker.log_event(
        DebugLevel.INFO, 
        'bot', 
        'request_start',
        f"Processing request from user {user_id}",
        {'platform': platform, 'url': url},
        user_id=user_id,
        url=url
    )

def log_extraction_attempt(url: str, platform: str, method: str):
    """Log an extraction attempt."""
    debug_tracker.log_event(
        DebugLevel.DEBUG,
        'scraper',
        'extraction_attempt',
        f"Attempting to extract from {platform} using {method}",
        {'platform': platform, 'method': method, 'url': url},
        url=url
    )

def log_extraction_success(url: str, platform: str, product_data: Dict):
    """Log successful extraction."""
    debug_tracker.log_event(
        DebugLevel.INFO,
        'scraper',
        'extraction_success',
        f"Successfully extracted product: {product_data.get('title', 'Unknown')}",
        {
            'platform': platform,
            'has_title': bool(product_data.get('title')),
            'has_price': bool(product_data.get('price')),
            'has_images': bool(product_data.get('images')),
            'extraction_method': product_data.get('extraction_method', 'unknown')
        },
        url=url
    )

def log_extraction_failure(url: str, platform: str, reason: str, error: Exception = None):
    """Log extraction failure."""
    debug_tracker.log_event(
        DebugLevel.ERROR,
        'scraper',
        'extraction_failed',
        f"Failed to extract from {platform}: {reason}",
        {
            'platform': platform,
            'reason': reason,
            'error_type': type(error).__name__ if error else None,
            'error_message': str(error) if error else None
        },
        url=url
    )

def log_response_sent(user_id: int, response_time: float, success: bool):
    """Log response sent to user."""
    debug_tracker.log_event(
        DebugLevel.INFO,
        'bot',
        'response_sent',
        f"Response sent to user {user_id} in {response_time:.2f}s",
        {'response_time': response_time, 'success': success},
        user_id=user_id
    )

def get_debug_status() -> str:
    """Get current debug status for /status command."""
    return debug_tracker.generate_debug_report()
