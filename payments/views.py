from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from courses.models import Enrollment
from .models import Payment
from .forms import PaymentForm
from django.core.paginator import Paginator
from .utils import send_payment_rejection_email


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
def upload_receipt(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)
        if form.is_valid():
            # Check if there's an existing payment (rejected or pending)
            if hasattr(enrollment, 'payment'):
                # Update existing payment record instead of creating new one
                payment = enrollment.payment
                payment.receipt = request.FILES['receipt']
                payment.uploaded_at = __import__('django.utils.timezone', fromlist=['now']).now()
                payment.rejection_reason = None  # Clear rejection reason on re-upload
                payment.approved = False
                payment.rejected = False          # Clear rejected flag on re-upload
                payment.save()
                messages.success(request, "Receipt updated successfully. Awaiting re-approval.")
            else:
                # Create new payment
                payment = form.save(commit=False)
                payment.enrollment = enrollment
                payment.save()
                messages.success(request, "Receipt uploaded successfully. Awaiting approval.")
            return redirect('dashboard:index')
    else:
        form = PaymentForm()
    return render(request, 'payments/upload_receipt.html', {'form': form, 'enrollment': enrollment})

@login_required
def review_receipts(request):
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can review receipts.")
        return redirect('dashboard:index')

    # Get all payments for this instructor's courses
    payments = Payment.objects.filter(enrollment__course__instructor=request.user).order_by('-uploaded_at')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        payments = payments.filter(
            Q(enrollment__student__username__icontains=search_query) |
            Q(enrollment__student__first_name__icontains=search_query) |
            Q(enrollment__student__last_name__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'pending':
        payments = payments.filter(approved=False, rejected=False)
    elif status_filter == 'approved':
        payments = payments.filter(approved=True)
    elif status_filter == 'rejected':
        payments = payments.filter(rejected=True)

    # Pagination
    paginator = Paginator(payments, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate statistics (always from full unfiltered set)
    all_payments = Payment.objects.filter(enrollment__course__instructor=request.user)
    approved_count  = all_payments.filter(approved=True).count()
    rejected_count  = all_payments.filter(rejected=True).count()
    pending_count   = all_payments.filter(approved=False, rejected=False).count()
    total_count     = all_payments.count()
    approval_percentage = int((approved_count / total_count * 100)) if total_count > 0 else 0
    filtered_count  = payments.count()

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'filtered_count': filtered_count,
        'search_query': search_query,
        'status': status_filter,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_count': pending_count,
        'total_count': total_count,
        'approval_percentage': approval_percentage,
    }

    return render(request, 'payments/review_receipts.html', context)

@login_required
def approve_receipt(request, payment_id):
    """Approve a payment receipt and send approval email."""
    payment = get_object_or_404(Payment, id=payment_id, enrollment__course__instructor=request.user)

    payment.approved = True
    payment.rejected = False          # Clear any previous rejection
    payment.rejection_reason = None
    payment.save()  # This will trigger the signal to send approval email

    # Grant course access
    payment.enrollment.approved = True
    payment.enrollment.save()

    messages.success(
        request,
        f"✓ Payment approved. {payment.enrollment.student.username} now has access to {payment.enrollment.course.title}."
    )
    return redirect('payments:review_receipts')

@login_required
def reject_receipt(request, payment_id):
    """Reject a payment receipt and send rejection email."""
    payment = get_object_or_404(Payment, id=payment_id, enrollment__course__instructor=request.user)

    student_name = payment.enrollment.student.username
    course_name  = payment.enrollment.course.title

    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '')

        payment.rejection_reason = rejection_reason
        payment.approved = False
        payment.rejected = True       # Explicitly mark as rejected in DB
        payment.save()

        send_payment_rejection_email(payment, rejection_reason)

        messages.success(
            request,
            f"✓ Payment receipt from {student_name} for {course_name} has been rejected. Rejection email sent."
        )

    return redirect('payments:review_receipts')
