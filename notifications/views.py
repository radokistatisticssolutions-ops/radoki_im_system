from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta

from .models import Notification


def _page_window(page_obj, on_each_side=2, on_ends=1):
    paginator = page_obj.paginator
    num_pages = paginator.num_pages
    current = page_obj.number
    included = set()
    for i in range(1, min(on_ends + 1, num_pages + 1)):
        included.add(i)
    for i in range(max(1, num_pages - on_ends + 1), num_pages + 1):
        included.add(i)
    for i in range(max(1, current - on_each_side), min(num_pages + 1, current + on_each_side + 1)):
        included.add(i)
    result = []
    last = 0
    for n in sorted(included):
        if n - last > 1:
            result.append(None)
        result.append(n)
        last = n
    return result


@login_required
def notification_list(request):
    """Full-page notification centre."""
    filter_type = request.GET.get('type', '')
    filter_read = request.GET.get('read', '')

    qs = Notification.objects.filter(recipient=request.user)

    if filter_type:
        qs = qs.filter(notif_type=filter_type)
    if filter_read == 'unread':
        qs = qs.filter(is_read=False)
    elif filter_read == 'read':
        qs = qs.filter(is_read=True)

    filtered_count = qs.count()
    paginator = Paginator(qs, 5)
    page_obj  = paginator.get_page(request.GET.get('page'))

    unread_total = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    return render(request, 'notifications/notification_list.html', {
        'page_obj':       page_obj,
        'paginator':      paginator,
        'page_window':    _page_window(page_obj),
        'filtered_count': filtered_count,
        'filter_type':    filter_type,
        'filter_read':    filter_read,
        'unread_total':   unread_total,
        'TYPES':          Notification.TYPES,
    })


@login_required
@require_POST
def mark_read(request, pk):
    """AJAX — mark a single notification as read."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_read(request):
    """AJAX — mark every unread notification as read."""
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'success': True})


@login_required
@require_POST
def delete_notification(request, pk):
    """AJAX — delete a single notification."""
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.delete()
    return JsonResponse({'success': True})


@login_required
def api_count(request):
    """
    Lightweight polling endpoint.
    Returns unread count + 5 most recent notifications for the bell dropdown.
    """
    unread = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    recent = (
        Notification.objects
        .filter(recipient=request.user)
        .order_by('-created_at')[:5]
    )

    items = []
    for n in recent:
        items.append({
            'id':       n.pk,
            'title':    n.title,
            'message':  n.message,
            'link':     n.link,
            'is_read':  n.is_read,
            'icon':     n.icon,
            'colour':   n.colour,
            'bg':       n.bg,
            'time':     n.created_at.strftime('%d %b, %H:%M'),
        })

    return JsonResponse({'unread': unread, 'notifications': items})


@login_required
@require_GET
def get_unread_for_reminders(request):
    """
    Get unread notifications that need sound reminders.
    
    Returns notifications where:
    - is_read = False
    - reminder_enabled = True
    - last_reminder_sent is None OR last_reminder_sent > 10 minutes ago
    
    This endpoint is called by JavaScript every 10 minutes to trigger sound alerts.
    """
    now = timezone.now()
    ten_minutes_ago = now - timedelta(minutes=10)
    
    # Get notifications that need reminders
    remind_notifs = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
        reminder_enabled=True,
    ).filter(
        # Either no reminder sent yet OR last one was > 10 mins ago
    )
    
    # Filter for those needing reminders (using Python since Django ORM limitation)
    notifications_needing_reminders = []
    for n in remind_notifs:
        if n.last_reminder_sent is None or n.last_reminder_sent <= ten_minutes_ago:
            notifications_needing_reminders.append(n)
    
    # Build response
    items = []
    for n in notifications_needing_reminders:
        items.append({
            'id': n.pk,
            'title': n.title,
            'message': n.message,
            'notif_type': n.notif_type,
            'icon': n.icon,
            'colour': n.colour,
            'time': n.created_at.strftime('%H:%M'),
        })
    
    return JsonResponse({
        'count': len(items),
        'notifications': items,
    })


@login_required
@require_POST
def update_reminder_timestamp(request, pk):
    """
    Update the last_reminder_sent timestamp for a notification.
    This is called by JavaScript after a sound alert has been played.
    """
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.last_reminder_sent = timezone.now()
    notif.save(update_fields=['last_reminder_sent'])
    return JsonResponse({'success': True, 'updated_at': notif.last_reminder_sent.isoformat()})
