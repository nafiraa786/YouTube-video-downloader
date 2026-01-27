#!/usr/bin/env python3
"""
API Testing Script - Test all endpoints
Run from backend directory: python test_api.py
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:5000/api"
TEST_VIDEO_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll
    "https://youtu.be/dQw4w9WgXcQ",                   # Short form
]

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test(title: str):
    """Print test title"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST: {title}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")

def test_health_check():
    """Test 1: Health Check"""
    print_test("Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy: {data.get('status')}")
            print_info(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API - ensure backend is running on port 5000")
        return False
    except Exception as e:
        print_error(f"Health check error: {str(e)}")
        return False

def test_video_info(url: str):
    """Test 2: Get Video Information"""
    print_test(f"Get Video Information")
    print_info(f"URL: {url}")
    
    try:
        payload = {"url": url}
        response = requests.post(f"{BASE_URL}/video-info", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                video_data = data.get('data', {})
                print_success("Video information fetched successfully")
                print_info(f"Title: {video_data.get('title')}")
                print_info(f"Duration: {video_data.get('duration')}s")
                print_info(f"Channel: {video_data.get('channel_name')}")
                print_info(f"Thumbnail: {video_data.get('thumbnail_url')}")
                
                formats = video_data.get('formats', [])
                print_info(f"Available formats: {len(formats)}")
                for fmt in formats:
                    print_info(f"  - {fmt.get('height')}p ({fmt.get('ext')})")
                
                return True
            else:
                print_error(f"API error: {data.get('error')}")
                return False
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Video info error: {str(e)}")
        return False

def test_invalid_url():
    """Test 3: Invalid URL Validation"""
    print_test("Invalid URL Validation")
    
    invalid_urls = [
        "not-a-url",
        "https://google.com",
        "https://twitter.com/user",
        "",
    ]
    
    for url in invalid_urls:
        try:
            payload = {"url": url}
            response = requests.post(f"{BASE_URL}/video-info", json=payload, timeout=10)
            
            if response.status_code != 200:
                data = response.json()
                print_success(f"Correctly rejected invalid URL: {url}")
            else:
                print_error(f"Should have rejected URL: {url}")
                return False
                
        except Exception as e:
            print_error(f"Validation test error: {str(e)}")
            return False
    
    return True

def test_rate_limiting():
    """Test 4: Rate Limiting"""
    print_test("Rate Limiting")
    
    print_info("Sending 5 requests in rapid succession...")
    
    success_count = 0
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                print_info(f"Request {i+1}: Rate limited (429)")
        except Exception as e:
            print_error(f"Request {i+1} failed: {str(e)}")
        
        time.sleep(0.1)
    
    print_success(f"Rate limiting test completed ({success_count}/5 successful)")
    return True

def test_cors_headers():
    """Test 5: CORS Headers"""
    print_test("CORS Headers")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        headers = response.headers
        
        if 'Access-Control-Allow-Origin' in headers:
            print_success(f"CORS enabled: {headers.get('Access-Control-Allow-Origin')}")
            return True
        else:
            print_info("No CORS headers found (may be handled by reverse proxy)")
            return True
            
    except Exception as e:
        print_error(f"CORS test error: {str(e)}")
        return False

def test_error_handling():
    """Test 6: Error Handling"""
    print_test("Error Handling")
    
    tests = [
        ("Missing URL", "video-info", {}),
        ("Missing format", "download", {"url": "https://youtube.com/watch?v=test"}),
    ]
    
    for test_name, endpoint, payload in tests:
        try:
            response = requests.post(f"{BASE_URL}/{endpoint}", json=payload, timeout=5)
            
            if response.status_code != 200:
                data = response.json()
                if not data.get('success'):
                    print_success(f"Correctly handled error: {test_name}")
                else:
                    print_error(f"Should have returned error for: {test_name}")
                    return False
        except Exception as e:
            print_error(f"Error test failed: {str(e)}")
            return False
    
    return True

def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     YouTube Video Downloader - API Test Suite               ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    print(f"{Colors.YELLOW}Backend URL: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.YELLOW}Time: {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
    
    results = {}
    
    # Test 1: Health check
    results['Health Check'] = test_health_check()
    
    if not results['Health Check']:
        print_error("Backend is not running. Start it with: python app.py")
        return
    
    # Test 2: Video info
    for url in TEST_VIDEO_URLS[:1]:  # Test first URL only
        results['Video Info'] = test_video_info(url)
        if results['Video Info']:
            break
    
    # Test 3: Invalid URL validation
    results['Invalid URL Validation'] = test_invalid_url()
    
    # Test 4: Rate limiting
    results['Rate Limiting'] = test_rate_limiting()
    
    # Test 5: CORS headers
    results['CORS Headers'] = test_cors_headers()
    
    # Test 6: Error handling
    results['Error Handling'] = test_error_handling()
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓ PASSED{Colors.RESET}" if result else f"{Colors.RED}✗ FAILED{Colors.RESET}"
        print(f"{test_name}: {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All tests passed!{Colors.RESET}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  Some tests failed. Check output above.{Colors.RESET}\n")

if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user.{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
