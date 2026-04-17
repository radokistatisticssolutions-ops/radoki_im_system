"""
Utility helpers for the notifications app.
Import and call notify() anywhere to create an in-app notification.
"""
import logging
from django.db import OperationalError
from django.utils import timezone

logger = logging.getLogger(__name__)


def notify(recipient, notif_type, title, message='', link='', metadata=None, reminder_enabled=True):
    """
    Create a single in-app notification for *recipient*.

    Parameters
    ----------
    recipient       : User instance
    notif_type      : str  — one of Notification.TYPES keys
    title           : str  — short headline (max 255 chars)
    message         : str  — optional longer body
    link            : str  — optional URL the bell-click/item-click should navigate to
    metadata        : dict — optional metadata (sender, content_type, timestamp, etc.)
    reminder_enabled: bool — whether to enable sound reminders for this notification
    """
    try:
        from notifications.models import Notification
        notif = Notification.objects.create(
            recipient=recipient,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link,
            metadata=metadata or {},
            reminder_enabled=reminder_enabled,
        )
        return notif
    except OperationalError:
        # Table might not exist yet (e.g. during initial migration)
        logger.warning("notifications table not ready — skipping notify()")
    except Exception as exc:
        logger.error(f"notify() failed: {exc}")


def notify_many(recipients, notif_type, title, message='', link='', metadata=None, reminder_enabled=True):
    """
    Bulk-create notifications for an iterable of User instances.
    
    Parameters
    ----------
    recipients      : iterable of User instances
    notif_type      : str  — one of Notification.TYPES keys
    title           : str  — short headline (max 255 chars)
    message         : str  — optional longer body
    link            : str  — optional URL the bell-click/item-click should navigate to
    metadata        : dict — optional metadata (sender, content_type, timestamp, etc.)
    reminder_enabled: bool — whether to enable sound reminders for these notifications
    """
    try:
        from notifications.models import Notification
        objs = [
            Notification(
                recipient=r,
                notif_type=notif_type,
                title=title,
                message=message,
                link=link,
                metadata=metadata or {},
                reminder_enabled=reminder_enabled,
            )
            for r in recipients
        ]
        if objs:
            created_notifs = Notification.objects.bulk_create(objs)
            return created_notifs
    except OperationalError:
        logger.warning("notifications table not ready — skipping notify_many()")
    except Exception as exc:
        logger.error(f"notify_many() failed: {exc}")
    return []
