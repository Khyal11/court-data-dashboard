#!/usr/bin/env python3
"""
Decode the flash message from the session cookie
"""

import base64
import json
from urllib.parse import unquote

# Session cookie from the test
session_cookie = "eyJfZmxhc2hlcyI6W3siIHQiOlsid2FybmluZyIsIlx1Mjc0YyBObyBjYXNlIGZvdW5kIGZvciBDLkEuKENPTU0uSVBELVBWKSAxLzIwMjAuIFBsZWFzZSB2ZXJpZnkgdGhlIGNhc2UgZGV0YWlscy4iXX1dfQ.aJCTGg.HRm2QRUW2F6wB0apq5e9N5KMkAc"

try:
    # Extract the payload part (before the first dot)
    payload = session_cookie.split('.')[0]
    
    # Add padding if needed
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    
    # Decode base64
    decoded_bytes = base64.b64decode(payload)
    decoded_str = decoded_bytes.decode('utf-8')
    
    # Parse JSON
    session_data = json.loads(decoded_str)
    
    print("🔍 Decoded Flash Message:")
    print("=" * 40)
    
    flashes = session_data.get('_flashes', [])
    for flash in flashes:
        if ' t' in flash:
            flash_type, message = flash[' t']
            print(f"Type: {flash_type}")
            print(f"Message: {message}")
            
            # Check if it's our expected message
            if "No case found for C.A.(COMM.IPD-PV) 1/2020" in message:
                print("✅ PASS: Correct 'no data found' message displayed")
            else:
                print("❌ FAIL: Unexpected message")
    
except Exception as e:
    print(f"❌ Error decoding: {str(e)}")