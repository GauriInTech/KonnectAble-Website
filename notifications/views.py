from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Notification

@login_required
def notification_list(request):
    """Display all notifications for the current user."""
    notifications = request.user.notifications.all()
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'notifications/notification_list.html', context)

@login_required
def mark_as_read(request, notification_id):
    """Mark a specific notification as read."""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notifications:notification_list')

@login_required
def mark_all_as_read(request):
    """Mark all notifications as read for the current user."""
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:notification_list')
