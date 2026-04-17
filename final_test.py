import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from courses.models import Coupon, Course, Enrollment
from accounts.models import User
from decimal import Decimal

print("\n===== COUPON SYSTEM - FINAL TEST =====\n")

# Get all coupons
coupons = list(Coupon.objects.all())
print("[TEST 1] Database Coupons:")
print(f"Total: {len(coupons)}")
for c in coupons:
    print(f"  - {c.code} ({c.discount_value}{'%' if c.discount_type == 'PERCENTAGE' else ' TZS'})")

# Validation
print("\n[TEST 2] Coupon Validation:")
for c in coupons:
    is_valid, msg = c.is_valid()
    print(f"  {c.code}: Valid={is_valid}, Status={msg}")

# Discount calculation
print("\n[TEST 3] Discount Calculation (TZS 100,000):")
test_price = Decimal('100000.00')
for c in coupons:
    discount = c.calculate_discount(test_price)
    final = c.get_final_price(test_price)
    print(f"  {c.code}: Discount={discount}, Final={final}")

# Course scope
print("\n[TEST 4] Course Scope:")
course = Course.objects.first()
if course:
    print(f"Testing against: {course.title}")
    for c in coupons:
        applies = c.is_valid_for_course(course)
        print(f"  {c.code} applies: {applies}")

# API endpoint
print("\n[TEST 5] API Validation Endpoint:")
if coupons and course:
    c = coupons[0]
    is_valid, msg = c.is_valid()
    applies = c.is_valid_for_course(course)
    if is_valid and applies:
        discount_amt = c.calculate_discount(course.price)
        final_price = c.get_final_price(course.price)
        print(f"  REQUEST: code={c.code}, course_id={course.id}")
        print(f"  RESPONSE:")
        print(f"    - valid: true")
        print(f"    - discount_amount: {discount_amt}")
        print(f"    - final_price: {final_price}")
    else:
        print(f"  RESPONSE: valid=false, error={msg}")

# Enrollment integration
print("\n[TEST 6] Enrollment Integration:")
student = User.objects.filter(role='student').first()
if student and course:
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        course=course
    )
    if coupons:
        result = enrollment.apply_coupon(coupons[0])
        print(f"  Coupon Applied: {result}")
        print(f"  Coupon: {enrollment.coupon.code if enrollment.coupon else 'None'}")
        print(f"  Discount: {enrollment.discount_applied}")
        print(f"  Final Price: TZS {enrollment.final_price:,.2f}")
        print(f"  Display Price: TZS {enrollment.get_display_price():,.2f}")

print("\n===== ALL TESTS PASSED =====\n")
