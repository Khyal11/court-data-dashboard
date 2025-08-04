#!/usr/bin/env python3
"""
Test script to verify the complete web flow for "no data found" scenario
"""

import requests
import time

def test_web_search():
    """Test the web search endpoint with a case that doesn't exist"""
    
    print("🌐 Testing Web Search Flow - No Data Found")
    print("=" * 50)
    
    # Test data - case that likely doesn't exist
    test_data = {
        'case_type': 'C.A.(COMM.IPD-PV)',
        'case_number': '1',
        'filing_year': '2020'
    }
    
    print(f"🔍 Testing search: {test_data['case_type']} {test_data['case_number']}/{test_data['filing_year']}")
    
    try:
        # Make POST request to search endpoint
        response = requests.post(
            'http://127.0.0.1:5000/search',
            data=test_data,
            allow_redirects=False  # Don't follow redirects to see the response
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📍 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            # Check if it redirects to home page (expected for "no data found")
            location = response.headers.get('Location', '')
            print(f"🔄 Redirect Location: {location}")
            
            if location.endswith('/'):
                print("✅ PASS: Correctly redirected to home page")
                print("✅ PASS: No data found scenario handled properly")
            else:
                print(f"❌ FAIL: Unexpected redirect location: {location}")
        else:
            print(f"❌ FAIL: Unexpected status code: {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to Flask app. Make sure it's running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🏁 Web flow test completed")

if __name__ == "__main__":
    test_web_search()