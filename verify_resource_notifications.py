"""
Final verification of resource notification system
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from notifications.models import Notification

print("=" * 70)
print("VERIFYING RESOURCE NOTIFICATION SYSTEM")
print("=" * 70)

# Get notification model
notif = Notification()

# Check TYPES
print("\n✓ Notification Types (Total: {})".format(len(notif.TYPES)))
resource_type = next((t for t in notif.TYPES if t[0] == 'resource_uploaded'), None)
if resource_type:
    print(f"  - Found: {resource_type[0]} → {resource_type[1]}")
else:
    print("  ✗ ERROR: resource_uploaded type not found!")
    sys.exit(1)

# Check icon
print("\n✓ Icon Configuration")
test_notif = Notification(notif_type='resource_uploaded')
icon = test_notif.icon
print(f"  - resource_uploaded icon: {icon}")
if icon == 'fa-file-download':
    print("  ✓ Icon is correct (fa-file-download)")
else:
    print(f"  ✗ ERROR: Expected fa-file-download, got {icon}")
    sys.exit(1)

# Check colour
print("\n✓ Colour Configuration")
colour = test_notif.colour
print(f"  - resource_uploaded colour: {colour}")
if colour == '#2980b9':
    print("  ✓ Colour is correct (#2980b9)")
else:
    print(f"  ✗ ERROR: Expected #2980b9, got {colour}")
    sys.exit(1)

# Check background
print("\n✓ Background Configuration")
bg = test_notif.bg
print(f"  - resource_uploaded bg: {bg}")
if bg == '#d6eaf8':
    print("  ✓ Background is correct (#d6eaf8)")
else:
    print(f"  ✗ ERROR: Expected #d6eaf8, got {bg}")
    sys.exit(1)

# Verify signal handler exists
print("\n✓ Signal Handler Check")
from notifications import signals
if hasattr(signals, 'on_resource_uploaded'):
    print("  ✓ on_resource_uploaded handler found")
else:
    print("  ✗ ERROR: on_resource_uploaded handler not found!")
    sys.exit(1)

# Count resource_uploaded notifications
print("\n✓ Database Check")
resource_notifs = Notification.objects.filter(notif_type='resource_uploaded')
print(f"  - Total resource notifications in DB: {resource_notifs.count()}")

# List recent ones
if resource_notifs.exists():
    latest = resource_notifs.latest('created_at')
    print(f"  - Latest: {latest.title}")
    print(f"    Recipient: {latest.recipient.username}")
    print(f"    Message: {latest.message[:60]}...")

print("\n" + "=" * 70)
print("ALL CHECKS PASSED ✓")
print("=" * 70)
