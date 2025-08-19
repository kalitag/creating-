# ReviewCheckk Bot - Testing Framework
import asyncio
import logging
from typing import List, Dict, Any
from debug_framework import debug_tracker, log_extraction_attempt, log_extraction_success, log_extraction_failure
from scraper import modern_scraper
from url_resolver import url_resolver

logger = logging.getLogger(__name__)

class BotTester:
    """Comprehensive testing framework for bot functionality."""
    
    def __init__(self):
        self.test_urls = {
            'amazon': [
                'https://www.amazon.in/dp/B08N5WRWNW',
                'https://amzn.to/3example',
                'https://www.amazon.com/dp/B08N5WRWNW'
            ],
            'flipkart': [
                'https://www.flipkart.com/product/p/example',
                'https://dl.flipkart.com/s/example'
            ],
            'meesho': [
                'https://www.meesho.com/product/example'
            ],
            'myntra': [
                'https://www.myntra.com/product/example'
            ]
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        logger.info("Starting comprehensive bot test suite...")
        
        results = {
            'url_resolution_tests': await self._test_url_resolution(),
            'scraping_tests': await self._test_scraping(),
            'error_handling_tests': await self._test_error_handling(),
            'performance_tests': await self._test_performance()
        }
        
        # Generate test report
        report = self._generate_test_report(results)
        logger.info("Test suite completed")
        
        return {
            'results': results,
            'report': report,
            'debug_summary': debug_tracker.get_error_summary()
        }
    
    async def _test_url_resolution(self) -> Dict[str, Any]:
        """Test URL resolution functionality."""
        logger.info("Testing URL resolution...")
        
        test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'details': []
        }
        
        test_cases = [
            ('https://amzn.to/test', 'amazon'),
            ('https://bit.ly/test', 'unknown'),
            ('https://www.flipkart.com/test', 'flipkart'),
            ('https://invalid-url', None)
        ]
        
        for url, expected_platform in test_cases:
            test_results['total_tests'] += 1
            
            try:
                result = url_resolver.resolve_url(url)
                detected_platform = result.get('platform')
                
                if expected_platform is None:
                    # Expecting failure
                    if result.get('error'):
                        test_results['passed'] += 1
                        test_results['details'].append({
                            'url': url,
                            'status': 'PASS',
                            'message': 'Correctly identified invalid URL'
                        })
                    else:
                        test_results['failed'] += 1
                        test_results['details'].append({
                            'url': url,
                            'status': 'FAIL',
                            'message': 'Should have failed but didn\'t'
                        })
                else:
                    # Expecting success
                    if detected_platform == expected_platform:
                        test_results['passed'] += 1
                        test_results['details'].append({
                            'url': url,
                            'status': 'PASS',
                            'message': f'Correctly detected {expected_platform}'
                        })
                    else:
                        test_results['failed'] += 1
                        test_results['details'].append({
                            'url': url,
                            'status': 'FAIL',
                            'message': f'Expected {expected_platform}, got {detected_platform}'
                        })
                        
            except Exception as e:
                test_results['failed'] += 1
                test_results['details'].append({
                    'url': url,
                    'status': 'ERROR',
                    'message': f'Exception: {str(e)}'
                })
        
        return test_results
    
    async def _test_scraping(self) -> Dict[str, Any]:
        """Test scraping functionality with real URLs."""
        logger.info("Testing scraping functionality...")
        
        test_results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'platform_results': {}
        }
        
        # Test each platform
        for platform, urls in self.test_urls.items():
            platform_results = {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'details': []
            }
            
            for url in urls[:2]:  # Test first 2 URLs per platform
                platform_results['total'] += 1
                test_results['total_tests'] += 1
                
                try:
                    log_extraction_attempt(url, platform, 'test')
                    
                    product_data = modern_scraper.scrape_product(url, platform)
                    
                    if product_data and product_data.get('title'):
                        platform_results['passed'] += 1
                        test_results['passed'] += 1
                        
                        log_extraction_success(url, platform, product_data)
                        
                        platform_results['details'].append({
                            'url': url,
                            'status': 'PASS',
                            'title': product_data.get('title', '')[:50] + '...',
                            'has_price': bool(product_data.get('price')),
                            'has_images': bool(product_data.get('images'))
                        })
                    else:
                        platform_results['failed'] += 1
                        test_results['failed'] += 1
                        
                        log_extraction_failure(url, platform, 'No title extracted')
                        
                        platform_results['details'].append({
                            'url': url,
                            'status': 'FAIL',
                            'message': 'No title extracted'
                        })
                        
                except Exception as e:
                    platform_results['failed'] += 1
                    test_results['failed'] += 1
                    
                    log_extraction_failure(url, platform, f'Exception: {str(e)}', e)
                    
                    platform_results['details'].append({
                        'url': url,
                        'status': 'ERROR',
                        'message': f'Exception: {str(e)}'
                    })
                
                # Add delay between requests
                await asyncio.sleep(2)
            
            test_results['platform_results'][platform] = platform_results
        
        return test_results
    
    async def _test_error_handling(self) -> Dict[str, Any]:
        """Test error handling with invalid inputs."""
        logger.info("Testing error handling...")
        
        test_cases = [
            ('', 'Empty URL'),
            ('not-a-url', 'Invalid URL format'),
            ('https://nonexistent-domain.com/product', 'Non-existent domain'),
            ('https://httpstat.us/404', '404 error'),
            ('https://httpstat.us/500', '500 error')
        ]
        
        results = {
            'total_tests': len(test_cases),
            'handled_gracefully': 0,
            'unhandled_errors': 0,
            'details': []
        }
        
        for url, description in test_cases:
            try:
                product_data = modern_scraper.scrape_product(url)
                
                # Should return None or empty dict for invalid URLs
                if not product_data or not product_data.get('title'):
                    results['handled_gracefully'] += 1
                    results['details'].append({
                        'test': description,
                        'status': 'PASS',
                        'message': 'Error handled gracefully'
                    })
                else:
                    results['details'].append({
                        'test': description,
                        'status': 'UNEXPECTED',
                        'message': 'Unexpected success'
                    })
                    
            except Exception as e:
                results['unhandled_errors'] += 1
                results['details'].append({
                    'test': description,
                    'status': 'UNHANDLED_ERROR',
                    'message': f'Unhandled exception: {str(e)}'
                })
            
            await asyncio.sleep(1)
        
        return results
    
    async def _test_performance(self) -> Dict[str, Any]:
        """Test performance metrics."""
        logger.info("Testing performance...")
        
        import time
        
        # Test response times
        test_url = 'https://www.amazon.in/dp/B08N5WRWNW'  # Example URL
        response_times = []
        
        for i in range(3):  # Test 3 times
            start_time = time.time()
            try:
                product_data = modern_scraper.scrape_product(test_url, 'amazon')
                end_time = time.time()
                response_times.append(end_time - start_time)
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            return {
                'average_response_time': round(avg_time, 2),
                'fastest': round(min(response_times), 2),
                'slowest': round(max(response_times), 2),
                'all_times': [round(t, 2) for t in response_times]
            }
        else:
            return {'message': 'No successful requests for performance testing'}
    
    def _generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("=== BOT TEST REPORT ===")
        report.append("")
        
        # URL Resolution Tests
        url_tests = results['url_resolution_tests']
        report.append("URL RESOLUTION TESTS:")
        report.append(f"  Total: {url_tests['total_tests']}")
        report.append(f"  Passed: {url_tests['passed']}")
        report.append(f"  Failed: {url_tests['failed']}")
        report.append(f"  Success Rate: {(url_tests['passed']/url_tests['total_tests']*100):.1f}%")
        report.append("")
        
        # Scraping Tests
        scraping_tests = results['scraping_tests']
        report.append("SCRAPING TESTS:")
        report.append(f"  Total: {scraping_tests['total_tests']}")
        report.append(f"  Passed: {scraping_tests['passed']}")
        report.append(f"  Failed: {scraping_tests['failed']}")
        report.append(f"  Success Rate: {(scraping_tests['passed']/scraping_tests['total_tests']*100):.1f}%")
        
        for platform, platform_results in scraping_tests['platform_results'].items():
            success_rate = (platform_results['passed']/platform_results['total']*100) if platform_results['total'] > 0 else 0
            report.append(f"    {platform.upper()}: {platform_results['passed']}/{platform_results['total']} ({success_rate:.1f}%)")
        report.append("")
        
        # Error Handling Tests
        error_tests = results['error_handling_tests']
        report.append("ERROR HANDLING TESTS:")
        report.append(f"  Total: {error_tests['total_tests']}")
        report.append(f"  Handled Gracefully: {error_tests['handled_gracefully']}")
        report.append(f"  Unhandled Errors: {error_tests['unhandled_errors']}")
        report.append("")
        
        # Performance Tests
        perf_tests = results['performance_tests']
        report.append("PERFORMANCE TESTS:")
        if 'average_response_time' in perf_tests:
            report.append(f"  Average Response Time: {perf_tests['average_response_time']}s")
            report.append(f"  Fastest: {perf_tests['fastest']}s")
            report.append(f"  Slowest: {perf_tests['slowest']}s")
        else:
            report.append(f"  {perf_tests.get('message', 'No data available')}")
        
        return "\n".join(report)

# Global tester instance
bot_tester = BotTester()
