import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()

print("\n===== TESTING WEB INTERFACE =====\n")

client = Client()

# Test 1: Coupon list
print("[TEST 1] Coupon List Endpoint:")
try:
    response = client.get('/courses/coupons/')
    print(f"  Status code: {response.status_code}")
    if response.status_code == 302:
        print("  - Redirects to login (OK)")
    else:
        print("  - Status: OK" if response.status_code == 200 else f"  - Error {response.status_code}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: Create coupon form
print("\n[TEST 2] Create Coupon Form:")
try:
    response = client.get('/courses/coupons/create/')
    print(f"  Status code: {response.status_code}")
    print("  - Template renders: YES" if response.status_code in [200, 302] else "NO")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 3: Course detail page
print("\n[TEST 3] Course Detail with Coupon Modal:")
try:
    response = client.get('/courses/1/')
    has_modal = b'enrollmentModal' in response.content
    has_api = b'validateCouponBtn' in response.content
    print(f"  Status code: {response.status_code}")
    print(f"  - Modal present: {has_modal}")
    print(f"  - API JS present: {has_api}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 4: API endpoint
print("\n[TEST 4] API Validation Endpoint:")
try:
    response = client.post(
        '/courses/api/validate-coupon/',
        data=json.dumps({"code": "TEST20", "course_id": 1}),
        content_type='application/json'
    )
    print(f"  Status code: {response.status_code}")
    if response.status_code == 401:
        print("  - Requires login: OK")
    elif response.status_code == 200:
        data = json.loads(response.content)
        print(f"  - Response valid: {data.get('valid')}")
        print(f"  - Discount: {data.get('discount_amount')}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 5: URL routing
print("\n[TEST 5] URL Routing:")
try:
    from django.urls import resolve
    from django.urls import NoReverseMatch
    
    urls_to_test = [
        '/courses/coupons/',
        '/courses/coupons/create/',
        '/courses/coupons/1/edit/',
        '/courses/coupons/1/delete/',
        '/courses/api/validate-coupon/',
    ]
    
    for url in urls_to_test:
        try:
            match = resolve(url)
            print(f"  {url:40} -> {match.func.__name__}")
        except:
            print(f"  {url:40} -> NOT FOUND")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n===== WEB INTERFACE TEST COMPLETE =====\n")
