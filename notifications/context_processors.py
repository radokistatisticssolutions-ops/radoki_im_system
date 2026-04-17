def unread_notifications(request):
    """
    Injects `unread_notif_count`, `recent_notifications`, and `just_logged_in`
    into every template context for authenticated users.

    `just_logged_in` is a one-shot flag: it is True only on the first page
    rendered after a successful login, then it is removed from the session.
    """
    if not request.user.is_authenticated:
        return {'unread_notif_count': 0, 'recent_notifications': [], 'just_logged_in': False}
    try:
        from notifications.models import Notification
        qs = Notification.objects.filter(recipient=request.user, is_read=False)
        count = qs.count()
        recent = (
            Notification.objects
            .filter(recipient=request.user)
            .order_by('-created_at')[:5]
        )
        # Pop the flag so it is consumed exactly once (the first page after login).
        just_logged_in = request.session.pop('just_logged_in', False)
        return {
            'unread_notif_count': count,
            'recent_notifications': recent,
            'just_logged_in': just_logged_in,
        }
    except Exception:
        return {'unread_notif_count': 0, 'recent_notifications': [], 'just_logged_in': False}
