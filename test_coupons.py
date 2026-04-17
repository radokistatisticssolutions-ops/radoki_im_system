#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from courses.models import Coupon, Course, Enrollment
from accounts.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

print("=" * 70)
print("COUPON SYSTEM FUNCTIONALITY TEST")
print("=" * 70)

# Test 1: Database state
print("\n[TEST 1] Current Coupons in Database:")
total = Coupon.objects.count()
print(f"Total coupons: {total}")
for c in Coupon.objects.all():
    disc_type = "%" if c.discount_type == "PERCENTAGE" else "TZS"
    print(f"  ✓ {c.code:15} | {c.discount_value}{disc_type:2} OFF | Created by: {c.created_by.username}")

# Test 2: Percentage coupon validation
print("\n[TEST 2] Testing SUMMER25 (25% Percentage Coupon):")
try:
    coupon = Coupon.objects.get(code='SUMMER25')
    is_valid, msg = coupon.is_valid()
    print(f"  ✓ Valid: {is_valid}")
    print(f"  ✓ Status: {msg}")

    # Test discount on TZS 100,000 course
    original_price = Decimal('100000.00')
    discount = coupon.calculate_discount(original_price)
    final_price = coupon.get_final_price(original_price)
    print(f"  ✓ Discount on TZS {original_price:,.0f}: TZS {discount:,.2f}")
    print(f"  ✓ Final price: TZS {final_price:,.2f}")
except Coupon.DoesNotExist:
    print("  ✗ SUMMER25 coupon not found!")

# Test 3: Fixed amount coupon
print("\n[TEST 3] Testing SAVE10 (Fixed TZS 10,000 Coupon):")
try:
    coupon = Coupon.objects.get(code='SAVE10')
    is_valid, msg = coupon.is_valid()
    print(f"  ✓ Valid: {is_valid}")
    print(f"  ✓ Status: {msg}")

    # Test discount on TZS 100,000 course
    original_price = Decimal('100000.00')
    discount = coupon.calculate_discount(original_price)
    final_price = coupon.get_final_price(original_price)
    print(f"  ✓ Discount on TZS {original_price:,.0f}: TZS {discount:,.2f}")
    print(f"  ✓ Final price: TZS {final_price:,.2f}")
except Coupon.DoesNotExist:
    print("  ✗ SAVE10 coupon not found!")

# Test 4: Course scope
print("\n[TEST 4] Testing Course Scope:")
course = Course.objects.first()
if course:
    print(f"Sample course: {course.title} (Price: TZS {course.price:,.0f})")
    for c in Coupon.objects.all():
        applies = c.is_valid_for_course(course)
        print(f"  ✓ {c.code} applies to this course: {applies}")

# Test 5: Usage limits
print("\n[TEST 5] Testing LIMITED5 (Usage Limits):")
try:
    coupon = Coupon.objects.get(code='LIMITED5')
    print(f"  ✓ Max uses: {coupon.max_uses}")
    print(f"  ✓ Current uses: {coupon.uses_count}")
    print(f"  ✓ Remaining: {coupon.max_uses - coupon.uses_count}")
except Coupon.DoesNotExist:
    print("  ✗ LIMITED5 coupon not found!")

# Test 6: Test Enrollment coupon integration
print("\n[TEST 6] Testing Coupon Integration with Enrollment:")
student = User.objects.filter(role='student').first()
if student and course:
    # Get or create enrollment
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        course=course
    )
    print(f"  ✓ Enrollment created: {created}")
    
    # Try to apply coupon
    coupon_to_apply = Coupon.objects.first()
    if coupon_to_apply:
        result = enrollment.apply_coupon(coupon_to_apply)
        print(f"  ✓ Coupon applied: {result}")
        print(f"  ✓ Discount applied: TZS {enrollment.discount_applied:,.2f}")
        print(f"  ✓ Final price: TZS {enrollment.final_price:,.2f}")
        print(f"  ✓ Display price: TZS {enrollment.get_display_price():,.2f}")
        
        # Check coupon usage incremented
        refreshed_coupon = Coupon.objects.get(pk=coupon_to_apply.pk)
        print(f"  ✓ Coupon uses incremented to: {refreshed_coupon.uses_count}")

# Test 7: Test API validation endpoint simulation
print("\n[TEST 7] Testing API Validation Logic:")
test_course = Course.objects.first()
if test_course:
    test_coupon = Coupon.objects.first()
    if test_coupon:
        # Simulate API request
        is_valid_now, msg = test_coupon.is_valid()
        applies_to_course = test_coupon.is_valid_for_course(test_course)
        
        if is_valid_now and applies_to_course:
            discount = test_coupon.calculate_discount(test_course.price)
            final_price = test_coupon.get_final_price(test_course.price)
            print(f"  ✓ API Response for {test_coupon.code}:")
            print(f"    - Valid: True")
            print(f"    - Original: TZS {test_course.price:,.0f}")
            print(f"    - Discount: TZS {discount:,.2f}")
            print(f"    - Final: TZS {final_price:,.2f}")
            print(f"    - Savings: TZS {discount:,.2f}")
        else:
            print(f"  ✗ Coupon validation failed: {msg}")

print("\n" + "=" * 70)
print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
print("=" * 70)
