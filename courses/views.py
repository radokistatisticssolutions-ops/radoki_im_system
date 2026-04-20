from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.core.exceptions import PermissionDenied # Correct import location
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Course, Enrollment, PaymentMethod, Resource, Module, Lesson, LessonCompletion, LessonProgress, ResourceDownload, LessonResourceDownload, LiveSession, Coupon
from core.models import AdminAccessControl


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


def _staff_permission_denied(request, message=None):
    """Staff users should see admin access denied rather than user redirect."""
    if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied(message or "Access denied")
    return None


from .forms import CourseForm, ResourceForm, PaymentMethodFormSet, LiveSessionForm, CouponForm
from django.utils.html import format_html
from django.http import FileResponse, HttpResponse
from django.urls import reverse
import mimetypes


@login_required
def course_list(request):
    search_query = request.GET.get('search', '').strip()
    courses = Course.objects.all()
    
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(instructor__first_name__icontains=search_query) |
            Q(instructor__last_name__icontains=search_query) |
            Q(instructor__username__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(courses, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total_courses = courses.count()
    
    return render(request, 'courses/course_list.html', {
        'courses': page_obj,
        'search_query': search_query,
        'total_courses': total_courses,
        'page_obj': page_obj,
    })


def _build_enriched_enrollments(queryset):
    """Helper: attach payment info to a queryset of Enrollment objects."""
    from payments.models import Payment
    result = []
    for enrollment in queryset:
        result.append({
            'enrollment': enrollment,
            'has_uploaded_receipt': hasattr(enrollment, 'payment') and enrollment.payment is not None,
            'payment': enrollment.payment if hasattr(enrollment, 'payment') else None,
        })
    return result


@login_required
def student_enrolled_courses(request):
    if not request.user.is_student():
        return redirect('dashboard:index')
    search_query = request.GET.get('search', '').strip()
    qs = (Enrollment.objects.filter(student=request.user)
          .select_related('course', 'course__instructor').order_by('-enrolled_at'))
    if search_query:
        qs = qs.filter(
            Q(course__title__icontains=search_query) |
            Q(course__instructor__first_name__icontains=search_query) |
            Q(course__instructor__last_name__icontains=search_query)
        )
    total = qs.count()
    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/student_my_courses.html', {
        'items': _build_enriched_enrollments(page_obj.object_list),
        'filter_label': 'Enrolled',
        'filter_key': 'enrolled',
        'total': total,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'search_query': search_query,
    })


@login_required
def student_pending_courses(request):
    if not request.user.is_student():
        return redirect('dashboard:index')
    search_query = request.GET.get('search', '').strip()
    qs = (Enrollment.objects.filter(student=request.user, approved=False)
          .select_related('course', 'course__instructor').order_by('-enrolled_at'))
    if search_query:
        qs = qs.filter(
            Q(course__title__icontains=search_query) |
            Q(course__instructor__first_name__icontains=search_query) |
            Q(course__instructor__last_name__icontains=search_query)
        )
    total = qs.count()
    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/student_my_courses.html', {
        'items': _build_enriched_enrollments(page_obj.object_list),
        'filter_label': 'Pending Payments',
        'filter_key': 'pending',
        'total': total,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'search_query': search_query,
    })


@login_required
def student_paid_courses(request):
    if not request.user.is_student():
        return redirect('dashboard:index')
    search_query = request.GET.get('search', '').strip()
    qs = (Enrollment.objects.filter(student=request.user, approved=True, completed=False)
          .select_related('course', 'course__instructor').order_by('-enrolled_at'))
    if search_query:
        qs = qs.filter(
            Q(course__title__icontains=search_query) |
            Q(course__instructor__first_name__icontains=search_query) |
            Q(course__instructor__last_name__icontains=search_query)
        )
    total = qs.count()
    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/student_my_courses.html', {
        'items': _build_enriched_enrollments(page_obj.object_list),
        'filter_label': 'Paid',
        'filter_key': 'paid',
        'total': total,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'search_query': search_query,
    })


@login_required
def student_completed_courses(request):
    if not request.user.is_student():
        return redirect('dashboard:index')
    search_query = request.GET.get('search', '').strip()
    qs = (Enrollment.objects.filter(student=request.user, completed=True)
          .select_related('course', 'course__instructor').order_by('-completed_at'))
    if search_query:
        qs = qs.filter(
            Q(course__title__icontains=search_query) |
            Q(course__instructor__first_name__icontains=search_query) |
            Q(course__instructor__last_name__icontains=search_query)
        )
    total = qs.count()
    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'courses/student_my_courses.html', {
        'items': _build_enriched_enrollments(page_obj.object_list),
        'filter_label': 'Completed',
        'filter_key': 'completed',
        'total': total,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'search_query': search_query,
    })


@login_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    enrollment = None
    has_uploaded_receipt = False
    completed_lesson_ids = set()

    if request.user.is_authenticated and request.user.is_student():
        enrollment = Enrollment.objects.filter(course=course, student=request.user).first()
        if enrollment:
            from payments.models import Payment
            has_uploaded_receipt = Payment.objects.filter(enrollment=enrollment).exists()
            if enrollment.approved:
                completed_lesson_ids = set(
                    LessonCompletion.objects.filter(
                        student=request.user,
                        lesson__module__course=course,
                    ).values_list('lesson_id', flat=True)
                )

    # Quiz data — list of (quiz, status_dict_or_None) tuples
    published_quizzes_qs = course.quizzes.filter(is_published=True).prefetch_related('questions')
    is_approved_student = (
        request.user.is_authenticated
        and request.user.is_student()
        and enrollment is not None
        and enrollment.approved
    )
    quiz_data = []
    for quiz in published_quizzes_qs:
        status = None
        if is_approved_student:
            best = quiz.student_best_attempt(request.user)
            status = {
                'passed': quiz.student_passed(request.user),
                'best_score': float(best.score) if best and best.score is not None else None,
                'attempts': quiz.student_attempts_count(request.user),
                'can_attempt': quiz.can_attempt(request.user),
            }
        quiz_data.append((quiz, status))

    # Get all live sessions for this course (sorted by date)
    from django.utils import timezone
    live_sessions = course.live_sessions.all().order_by('scheduled_at')
    upcoming_sessions = live_sessions.filter(scheduled_at__gte=timezone.now())
    past_sessions = live_sessions.filter(scheduled_at__lt=timezone.now())

    return render(request, 'courses/course_detail.html', {
        'course':               course,
        'enrollment':           enrollment,
        'enrolled':             bool(enrollment),
        'has_uploaded_receipt': has_uploaded_receipt,
        'completed_lesson_ids': completed_lesson_ids,
        'quiz_data':            quiz_data,
        'upcoming_sessions':    upcoming_sessions,
        'past_sessions':        past_sessions,
    })


@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    coupon_code = None
    reward_id = None
    
    if request.user.is_student():
        # Get coupon code and reward IDs from POST parameters
        coupon_code = request.POST.get('coupon_code')
        reward_ids_raw = request.POST.get('reward_ids', '').strip()

        enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
        if created:
            # Try to apply rewards if provided
            if reward_ids_raw:
                try:
                    from referrals.models import ReferralReward
                    ids = [i.strip() for i in reward_ids_raw.split(',') if i.strip()]
                    rewards_by_id = {
                        str(r.id): r for r in
                        ReferralReward.objects.filter(id__in=ids, referrer=request.user)
                    }
                    rewards = [rewards_by_id[i] for i in ids if i in rewards_by_id]
                    count = enrollment.apply_rewards(rewards)
                    if count:
                        messages.success(request, f"You enrolled in {course.title} with {count} reward{'s' if count != 1 else ''} applied!")
                    else:
                        messages.warning(request, "Rewards could not be applied. Course enrollment completed without discount.")
                except Exception:
                    messages.warning(request, "Rewards could not be applied. Course enrollment completed without discount.")
            # Try to apply coupon if provided
            elif coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code.strip().upper())
                    if enrollment.apply_coupon(coupon):
                        messages.success(request, f"You enrolled in {course.title} with coupon {coupon.code}. Discount applied!")
                    else:
                        messages.warning(request, f"Coupon {coupon_code} could not be applied. Course enrollment completed without discount.")
                except Coupon.DoesNotExist:
                    messages.warning(request, f"Coupon code '{coupon_code}' not found. Course enrollment completed without discount.")
            else:
                messages.success(request, f"You enrolled in {course.title}. Awaiting payment approval.")
        else:
            messages.info(request, "You are already enrolled in this course.")
    else:
        messages.error(request, "Only students can enroll.")
    return redirect('courses:course_detail', pk=pk)


@login_required
def instructor_courses(request):
    from django.core.paginator import Paginator
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can manage courses.")
        return redirect('courses:course_list')

    query = request.GET.get('q', '').strip()
    courses_qs = Course.objects.filter(instructor=request.user).prefetch_related(
        'enrollments', 'resources', 'payment_methods'
    ).order_by('title')

    if query:
        courses_qs = courses_qs.filter(title__icontains=query)

    # Build per-course stats list from filtered queryset
    course_stats = []
    for course in courses_qs:
        enrollments = course.enrollments.all()
        student_count = enrollments.filter(student__role='student').count()
        course_stats.append({
            'course': course,
            'total_students': student_count,
        })

    paginator = Paginator(course_stats, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'query': query,
        'total_courses': courses_qs.count(),
    }
    return render(request, 'courses/instructor_courses.html', context)


@login_required
def course_students(request, course_id):
    """List all students enrolled in a specific course with payment status, search, filter, pagination."""
    from django.core.paginator import Paginator
    from payments.models import Payment

    course = get_object_or_404(Course, id=course_id, instructor=request.user)

    enrollments = Enrollment.objects.filter(
        course=course, student__role='student'
    ).select_related('student').prefetch_related('payment').order_by('-enrolled_at')

    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        enrollments = enrollments.filter(
            Q(student__username__icontains=search_query) |
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query)
        )

    # Filter by payment status
    status_filter = request.GET.get('status', '')
    if status_filter == 'approved':
        enrollments = enrollments.filter(payment__approved=True)
    elif status_filter == 'pending':
        enrollments = enrollments.filter(payment__approved=False, payment__rejected=False)
    elif status_filter == 'rejected':
        enrollments = enrollments.filter(payment__rejected=True)
    elif status_filter == 'no_payment':
        enrollments = enrollments.filter(payment__isnull=True)

    # Stats (always from unfiltered set for this course)
    all_enrollments = Enrollment.objects.filter(course=course, student__role='student')
    total_count    = all_enrollments.count()
    approved_count = all_enrollments.filter(payment__approved=True).count()
    rejected_count = all_enrollments.filter(payment__rejected=True).count()
    pending_count  = all_enrollments.filter(payment__approved=False, payment__rejected=False, payment__isnull=False).count()
    no_payment_count = all_enrollments.filter(payment__isnull=True).count()

    filtered_count = enrollments.count()

    paginator  = Paginator(enrollments, 10)
    page_obj   = paginator.get_page(request.GET.get('page'))

    context = {
        'course': course,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'search_query': search_query,
        'status': status_filter,
        'filtered_count': filtered_count,
        'total_count': total_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_count': pending_count,
        'no_payment_count': no_payment_count,
    }
    return render(request, 'courses/course_students.html', context)


@login_required
def instructor_students(request):
    """Display all students enrolled in instructor's courses with search, filter, and pagination."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can view this page.")
        return redirect('courses:course_list')

    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    course_filter = request.GET.get('course', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # Get all instructor's courses
    instructor_courses = Course.objects.filter(instructor=request.user).order_by('title')

    # Get enrollments from instructor's courses
    enrollments_qs = Enrollment.objects.filter(
        course__instructor=request.user,
        student__role='student'
    ).select_related('course', 'student').order_by('student__first_name', 'student__last_name')

    # Apply course filter
    if course_filter:
        try:
            course_id = int(course_filter)
            enrollments_qs = enrollments_qs.filter(course_id=course_id)
        except ValueError:
            pass

    # Apply enrollment status filter
    if status_filter == 'pending':
        enrollments_qs = enrollments_qs.filter(approved=False)
    elif status_filter == 'approved':
        enrollments_qs = enrollments_qs.filter(approved=True)
    elif status_filter == 'completed':
        enrollments_qs = enrollments_qs.filter(completed=True)

    # Apply search filter (search by student name)
    if search_query:
        enrollments_qs = enrollments_qs.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__username__icontains=search_query) |
            Q(course__title__icontains=search_query)
        )

    filtered_count = enrollments_qs.count()
    total_students = Enrollment.objects.filter(
        course__instructor=request.user, student__role='student'
    ).count()

    # Pagination
    paginator = Paginator(enrollments_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'total_students': total_students,
        'filtered_count': filtered_count,
        'instructor_courses': instructor_courses,
        'search_query': search_query,
        'course_filter': course_filter,
        'status_filter': status_filter,
    }
    return render(request, 'courses/instructor_students.html', context)


@login_required
def create_course(request):
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can create courses.")
        return redirect('courses:course_list')
    if request.method == 'POST':
        form = CourseForm(request.POST)
        payment_formset = PaymentMethodFormSet(request.POST, queryset=PaymentMethod.objects.none())
        
        # Validate course form
        if not form.is_valid():
            messages.error(request, "Course form has errors.")
            return render(request, 'courses/course_form.html', {'form': form, 'payment_formset': payment_formset})
        
        # Save course first
        course = form.save(commit=False)
        course.instructor = request.user
        course.save()
        
        # Validate formset to populate cleaned_data
        payment_formset.is_valid()
        
        # Get the formset prefix
        prefix = payment_formset.prefix
        
        # Process payment methods
        saved_count = 0
        for i, form_instance in enumerate(payment_formset.forms):
            try:
                # Get cleaned data if available
                if hasattr(form_instance, 'cleaned_data') and form_instance.cleaned_data:
                    method_type = form_instance.cleaned_data.get('method_type')
                else:
                    # Extract directly from POST data using the correct prefix
                    field_name = f'{prefix}-{i}-method_type'
                    method_type = request.POST.get(field_name, '').strip()
                
                # Only save if method_type is provided
                if method_type:
                    payment = form_instance.save(commit=False)
                    payment.course = course
                    payment.save()
                    saved_count += 1
            except Exception as e:
                print(f"Error saving payment method {i}: {str(e)}")
                continue
        
        messages.success(request, f"Course created successfully with {saved_count} payment method(s).")
        return redirect('courses:instructor_courses')
    else:
        form = CourseForm()
        payment_formset = PaymentMethodFormSet(queryset=PaymentMethod.objects.none())
    return render(request, 'courses/course_form.html', {'form': form, 'payment_formset': payment_formset})


@login_required
def edit_course(request, pk):
    # Fetch the course by PK first
    course = get_object_or_404(Course, pk=pk)

    # Check if user is the course owner or superuser
    is_owner = course.instructor == request.user or request.user.is_superuser
    is_instructor = request.user.is_instructor()
    
    # If not the owner and is an instructor, show ownership narrative
    if is_instructor and not is_owner:
        context = {
            'course': course,
            'course_owner': course.instructor,
            'is_ownership_page': True
        }
        return render(request, 'courses/course_ownership.html', context)
    
    # If not instructor and not superuser, block access
    if not is_instructor and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to edit this course.")

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        payment_formset = PaymentMethodFormSet(request.POST, queryset=PaymentMethod.objects.filter(course=course))
        
        # Validate course form
        if not form.is_valid():
            messages.error(request, "Course form has errors.")
            return render(request, 'courses/course_form.html', {'form': form, 'payment_formset': payment_formset})
        
        # Save course
        form.save()
        
        # Get the formset prefix
        prefix = payment_formset.prefix
        
        # Process payment methods
        saved_count = 0
        deleted_count = 0
        
        # Get all existing payment methods for this course
        existing_payment_methods = {pm.id: pm for pm in PaymentMethod.objects.filter(course=course)}
        
        for i, form_instance in enumerate(payment_formset.forms):
            try:
                # Get the DELETE field value from POST
                delete_field_name = f'{prefix}-{i}-DELETE'
                delete_flag = delete_field_name in request.POST
                
                # Get method_type from POST data
                method_type_field_name = f'{prefix}-{i}-method_type'
                method_type = request.POST.get(method_type_field_name, '').strip()
                
                # Get merchant_id and merchant_name from POST
                merchant_id_field_name = f'{prefix}-{i}-merchant_id'
                merchant_name_field_name = f'{prefix}-{i}-merchant_name'
                merchant_id = request.POST.get(merchant_id_field_name, '').strip()
                merchant_name = request.POST.get(merchant_name_field_name, '').strip()
                
                # If DELETE is checked and method_type exists, delete by method_type
                if delete_flag and method_type:
                    try:
                        payment = PaymentMethod.objects.get(course=course, method_type=method_type)
                        payment.delete()
                        deleted_count += 1
                        print(f"Deleted payment method {i}: {method_type}")
                    except PaymentMethod.DoesNotExist:
                        print(f"Payment method {method_type} not found for deletion")
                # If not marked for deletion and method_type is provided, save
                elif method_type and not delete_flag:
                    # Use get_or_create to handle existing payment methods with same type
                    payment, created = PaymentMethod.objects.get_or_create(
                        course=course,
                        method_type=method_type,
                        defaults={
                            'merchant_id': merchant_id,
                            'merchant_name': merchant_name
                        }
                    )
                    
                    # If already existed, update the merchant info
                    if not created:
                        payment.merchant_id = merchant_id
                        payment.merchant_name = merchant_name
                        payment.save()
                    
                    saved_count += 1
                    action = "Created" if created else "Updated"
                    print(f"{action} payment method {i}: {method_type}")
                    
            except Exception as e:
                print(f"Error processing payment method {i}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        success_msg = "Course updated successfully"
        if saved_count > 0 or deleted_count > 0:
            success_msg += f" ({saved_count} added/updated, {deleted_count} deleted)"
        success_msg += "."
        messages.success(request, success_msg)
        return redirect('courses:instructor_courses')
    else:
        form = CourseForm(instance=course)
        payment_formset = PaymentMethodFormSet(queryset=PaymentMethod.objects.filter(course=course))
    return render(request, 'courses/course_form.html', {'form': form, 'payment_formset': payment_formset})


@login_required
def delete_course(request, pk):
    # Fetch the course by PK first
    course = get_object_or_404(Course, pk=pk)

    # Explicitly check permission
    if course.instructor != request.user and not request.user.is_superuser:
         raise PermissionDenied("You do not have permission to delete this course.")

    course.delete()
    messages.success(request, "Course deleted.")
    return redirect('courses:instructor_courses')


@login_required
def upload_resource(request, course_id):
    # Fetch the course by PK first
    course = get_object_or_404(Course, pk=course_id)

    # Check if user is the course owner or superuser
    is_owner = course.instructor == request.user or request.user.is_superuser
    is_instructor = request.user.is_instructor()
    
    # If not the owner and is an instructor, show ownership narrative
    if is_instructor and not is_owner:
        context = {
            'course': course,
            'course_owner': course.instructor,
            'is_ownership_page': True,
            'action': 'upload_resource'
        }
        return render(request, 'courses/course_ownership.html', context)
    
    # If not instructor and not superuser, block access
    if not is_instructor and not request.user.is_superuser:
        raise PermissionDenied("You do not have permission to upload resources to this course.")

    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)
        if form.is_valid():
            resource = form.save(commit=False)
            resource.course = course
            resource.save()
            messages.success(request, "Resource uploaded successfully.")
            return redirect('courses:course_detail', pk=course_id)
    else:
        form = ResourceForm()
    return render(request, 'courses/upload_resource.html', {'form': form, 'course': course})


@login_required
def instructor_resource_view(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    # Check if the user is the instructor or a superuser, or has AdminAccessControl view permission
    if course.instructor != request.user and not request.user.is_superuser:
        if not AdminAccessControl.has_permission(request.user, 'resource', 'view'):
            raise PermissionDenied("You do not have permission to view this page.")

    resources = course.resources.all()

    return render(request, 'courses/instructor_resource_view.html', {
        'course': course,
        'resources': resources,
    })


@login_required
def delete_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)

    # Check if the user is the instructor, a superuser, or has AdminAccessControl delete permission
    if resource.course.instructor != request.user and not request.user.is_superuser:
        if not AdminAccessControl.has_permission(request.user, 'resource', 'delete'):
            raise PermissionDenied("You do not have permission to delete this resource.")

    resource.delete()
    messages.success(request, "Resource deleted successfully.")
    return redirect('courses:course_detail', pk=resource.course.id)


@login_required
@never_cache
def preview_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)

    # Permission checks
    is_instructor = resource.course.instructor == request.user or request.user.is_superuser
    is_staff_viewer = request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser and AdminAccessControl.has_permission(request.user, 'resource', 'view')

    if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser and resource.course.instructor != request.user and not is_staff_viewer:
        raise PermissionDenied("Admin staff access denied for this resource")

    if not (is_instructor or is_staff_viewer):
        if not request.user.is_student():
            _staff_permission_denied(request, "❌ Unauthorized Access: Only students and instructors can preview course resources.")
            messages.error(request, "❌ Unauthorized Access: Only students and instructors can preview course resources.")
            return redirect('courses:course_list')

        enrollment = Enrollment.objects.filter(course=resource.course, student=request.user).first()
        if not enrollment:
            _staff_permission_denied(request, "📚 Not Enrolled: You must be enrolled in this course to access this resource.")
            messages.error(request, "📚 Not Enrolled: You must be enrolled in this course to access this resource. Please enroll first.")
            return redirect('courses:course_detail', pk=resource.course.id)

        # Check if student is approved (either via admin approval or payment approval)
        from payments.models import Payment
        payment = Payment.objects.filter(enrollment=enrollment, approved=True).first()
        is_approved = enrollment.approved or payment
        if not is_approved:
            _staff_permission_denied(request, "⏳ Payment Pending: Your payment is still pending approval.")
            messages.error(request, "⏳ Payment Pending: Your payment is still pending approval. You'll gain access once it's approved by the instructor.")
            return redirect('courses:course_detail', pk=resource.course.id)
    else:
        if resource.course.instructor != request.user and not request.user.is_superuser and not is_staff_viewer:
            _staff_permission_denied(request, "🔒 Access Denied: You can only access resources from your own courses.")
            messages.error(request, "🔒 Access Denied: You can only access resources from your own courses. This resource belongs to another instructor.")
            return redirect('courses:instructor_courses')

    # File metadata
    file_name = resource.file.name
    file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''

    # URLs
    file_url = f'/courses/resource/{resource.id}/serve/'

    # Determine preview type for template
    # Only PDF files can be previewed; all other files show download option
    preview_type = 'pdf' if file_ext == 'pdf' else 'download'

    context = {
        'resource': resource,
        'preview_type': preview_type,
        'file_url': file_url,
        'file_ext': file_ext,
        'file_name': file_name,
        'course': resource.course,
    }

    return render(request, 'courses/preview_resource.html', context)


@login_required
@never_cache
def serve_file(request, resource_id):
    """Serve file inline (for preview) without triggering download"""
    try:
        resource = get_object_or_404(Resource, id=resource_id)

        # Check if the user has permission to access the resource
        is_instructor = resource.course.instructor == request.user or request.user.is_superuser
        is_staff_viewer = request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser and AdminAccessControl.has_permission(request.user, 'resource', 'view')

        # If not instructor and not authorized staff viewer, check if student has approved payment
        if not (is_instructor or is_staff_viewer):
            if not request.user.is_student():
                raise PermissionDenied("❌ Unauthorized Access: Only students and instructors can preview course resources.")
            
            # Check if student is enrolled
            enrollment = Enrollment.objects.filter(course=resource.course, student=request.user).first()
            if not enrollment:
                raise PermissionDenied("📚 Not Enrolled: You must be enrolled in this course to access its resources.")
            
            # Check if student is approved (either via admin approval or payment approval)
            from payments.models import Payment
            payment = Payment.objects.filter(enrollment=enrollment, approved=True).first()
            is_approved = enrollment.approved or payment
            if not is_approved:
                raise PermissionDenied("⏳ Payment Pending: Your payment is still pending approval. You'll gain access once approved.")
        else:
            # For course owner instructors (or superusers) only
            if resource.course.instructor != request.user and not request.user.is_superuser:
                raise PermissionDenied("🔒 Access Denied: You can only access resources from your own courses.")

        # Get file extension and content type
        file_name = resource.file.name
        file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        # Determine content type based on file extension
        content_types = {
            'pdf': 'application/pdf',
        }
        
        content_type = content_types.get(file_ext, 'application/octet-stream')
        
        # Read the file and serve with HttpResponse
        try:
            # Read file content
            file_content = resource.file.read()
            
            # Check if file has content
            if not file_content:
                raise PermissionDenied("File is empty or could not be read")
            
            # Create response with file content
            response = HttpResponse(file_content, content_type=content_type)
            
            # Serve PDF inline for preview
            response['Content-Disposition'] = 'inline; filename="{}"'.format(file_name)
            
            # Aggressive caching for faster loads on subsequent requests
            # Browser will cache for 30 days (2592000 seconds)
            response['Cache-Control'] = 'public, max-age=2592000, immutable'
            response['Pragma'] = 'cache'
            response['Expires'] = 'Sun, 31 Dec 2026 23:59:59 GMT'
            
            # Security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'SAMEORIGIN'
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Content-Length header for progress tracking
            response['Content-Length'] = str(len(file_content))
            
            # Enable compression if supported
            response['Vary'] = 'Accept-Encoding'
            
            return response
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise PermissionDenied(f"Error reading file: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Redirect to 403 if something unexpected happens
        raise PermissionDenied("Unable to serve file.")



@login_required
def download_resource(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)

    # Check if the user has permission to download the resource
    is_instructor = resource.course.instructor == request.user or request.user.is_superuser
    is_staff_exporter = request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser and AdminAccessControl.has_permission(request.user, 'resource', 'export')

    # Admin staff who don't have export permission cannot download resources not owned by them
    if request.user.is_authenticated and request.user.is_staff and not request.user.is_superuser and resource.course.instructor != request.user and not is_staff_exporter:
        raise PermissionDenied("Admin staff access denied for this resource")

    # If not instructor and not staff exporter, check if student has approved payment and download is allowed
    if not (is_instructor or is_staff_exporter):
        if not request.user.is_student():
            _staff_permission_denied(request, "❌ Unauthorized: Only students and instructors can download course resources.")
            messages.error(request, "❌ Unauthorized: Only students and instructors can download course resources.")
            return redirect('courses:course_list')
        
        # Check if student is enrolled
        enrollment = Enrollment.objects.filter(course=resource.course, student=request.user).first()
        if not enrollment:
            _staff_permission_denied(request, "📚 Not Enrolled: You must be enrolled in this course to download its resources.")
            messages.error(request, "📚 Not Enrolled: You must be enrolled in this course to download its resources. Please enroll first.")
            return redirect('courses:course_detail', pk=resource.course.id)
        
        # Check if student is approved (either via admin approval or payment approval)
        from payments.models import Payment
        payment = Payment.objects.filter(enrollment=enrollment, approved=True).first()
        is_approved = enrollment.approved or payment
        if not is_approved:
            _staff_permission_denied(request, "⏳ Payment Pending: Your payment is still pending approval.")
            messages.error(request, "⏳ Payment Pending: Your payment is still pending approval. Downloads will be available once approved.")
            return redirect('courses:course_detail', pk=resource.course.id)
        
        # Check if resource download is allowed by instructor
        if not resource.download_allowed:
            _staff_permission_denied(request, "🔒 Downloads Disabled: The instructor has not allowed downloads for this resource yet.")
            messages.error(request, "🔒 Downloads Disabled: The instructor has not allowed downloads for this resource yet. Please try again later or contact the instructor.")
            return redirect('courses:course_detail', pk=resource.course.id)
    else:
        # For instructors: check if they own this course or are superuser
        if resource.course.instructor != request.user and not request.user.is_superuser and not is_staff_exporter:
            _staff_permission_denied(request, "🔒 Access Denied: You can only download resources from your own courses.")
            messages.error(request, "🔒 Access Denied: You can only download resources from your own courses. This resource belongs to another instructor.")
            return redirect('courses:instructor_courses')

    # Log the download for analytics (students only)
    if request.user.is_student():
        ResourceDownload.objects.create(resource=resource, student=request.user)

    # Read file and return as attachment for download
    try:
        from core.file_utils import serve_file_response
        return serve_file_response(resource.file, force_download=True)
    except Exception as e:
        raise PermissionDenied(f"Error reading file: {str(e)}")


@login_required
def download_lesson_resource(request, lesson_id):
    """Serve a lesson attachment as a download and track it for students."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    if not lesson.resource_file:
        messages.error(request, "This lesson has no attachment file.")
        return redirect('courses:lesson_detail', lesson_id=lesson_id)

    is_instructor = course.instructor == request.user or request.user.is_superuser

    if not is_instructor:
        enrollment = Enrollment.objects.filter(course=course, student=request.user).first()
        if not enrollment:
            messages.error(request, "You must be enrolled in this course to download lesson files.")
            return redirect('courses:course_detail', pk=course.id)

        from payments.models import Payment
        payment = Payment.objects.filter(enrollment=enrollment, approved=True).first()
        is_approved = enrollment.approved or payment
        if not is_approved:
            messages.error(request, "Your payment is still pending approval. Downloads will be available once approved.")
            return redirect('courses:course_detail', pk=course.id)

    # Track download for students only
    if not is_instructor:
        LessonResourceDownload.objects.create(lesson=lesson, student=request.user)

    try:
        from core.file_utils import serve_file_response
        return serve_file_response(lesson.resource_file, force_download=True)
    except Exception as e:
        raise PermissionDenied(f"Error reading file: {str(e)}")


@login_required
def toggle_resource_download(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id)

    # Check if the user is the instructor, a superuser, or has AdminAccessControl edit permission
    if resource.course.instructor != request.user and not request.user.is_superuser:
        if not AdminAccessControl.has_permission(request.user, 'resource', 'edit'):
            raise PermissionDenied("You do not have permission to modify this resource.")

    # Toggle the download permission
    resource.download_allowed = not resource.download_allowed
    resource.save()

    # Determine the message based on the new state
    status = "enabled" if resource.download_allowed else "disabled"
    messages.success(request, f"Download permission {status} for '{resource.title}'.")

    return redirect('courses:instructor_resource_view', course_id=resource.course.id)

# ============================================================================
# COURSE COMPLETION & CERTIFICATE VIEWS
# ============================================================================

@login_required
@login_required
def mark_course_complete(request, enrollment_id):
    """Mark a course as completed by instructor."""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Only instructor or superuser can mark course complete
    if enrollment.course.instructor != request.user and not request.user.is_superuser:
        raise PermissionDenied("You don't have permission to mark this course complete.")
    
    # Check if instructor has permission to mark courses complete (unless superuser)
    if not request.user.is_superuser and request.user.is_staff:
        from core.models import InstructorCoursePermission
        try:
            perm = InstructorCoursePermission.objects.get(instructor=request.user)
            if not perm.can_mark_complete:
                messages.error(
                    request,
                    "❌ You don't have permission to mark courses as complete. Please contact your system administrator."
                )
                return render(request, 'courses/mark_complete_confirm.html', {
                    'enrollment': enrollment,
                    'course': enrollment.course,
                    'student': enrollment.student,
                    'permission_denied': True,
                })
        except InstructorCoursePermission.DoesNotExist:
            messages.error(
                request,
                "❌ Your permission to mark courses as complete hasn't been set up yet. Please contact your system administrator."
            )
            return render(request, 'courses/mark_complete_confirm.html', {
                'enrollment': enrollment,
                'course': enrollment.course,
                'student': enrollment.student,
                'permission_denied': True,
            })
    
    if request.method == 'POST':
        # Quiz gate: check required quizzes are passed before marking complete
        from quizzes.models import Quiz as QuizModel
        blocking_quizzes = []
        for quiz in enrollment.course.quizzes.filter(is_published=True, require_pass_for_completion=True):
            if not quiz.student_passed(enrollment.student):
                blocking_quizzes.append(quiz.title)
        if blocking_quizzes:
            quiz_list_str = ', '.join(f'"{q}"' for q in blocking_quizzes)
            messages.warning(
                request,
                f"Cannot mark complete: student has not passed required quiz: {quiz_list_str}."
            )
            return render(request, 'courses/mark_complete_confirm.html', {
                'enrollment': enrollment,
                'course': enrollment.course,
                'student': enrollment.student,
                'blocking_quizzes': blocking_quizzes,
            })

        # Mark course as completed
        was_completed = enrollment.mark_completed()

        if was_completed:
            messages.success(request, f"Course marked as completed for {enrollment.student.get_full_name()}.")
        else:
            messages.info(request, "Course was already marked as completed.")
        
        # Redirect to confirmation page
        return render(request, 'courses/mark_complete_confirm.html', {
            'enrollment': enrollment,
            'course': enrollment.course,
            'student': enrollment.student,
            'now': enrollment.completed_at,
        })
    
    # GET request - show confirmation page
    return render(request, 'courses/mark_complete_confirm.html', {
        'enrollment': enrollment,
        'course': enrollment.course,
        'student': enrollment.student,
        'now': enrollment.completed_at,
    })


@login_required
def generate_certificate(request, enrollment_id):
    """Generate certificate for completed course."""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Check permissions - student must own the enrollment or be instructor/superuser
    is_owner = enrollment.student == request.user
    is_instructor = enrollment.course.instructor == request.user or request.user.is_superuser
    
    if not (is_owner or is_instructor):
        raise PermissionDenied("You don't have permission to access this certificate.")
    
    # Check if eligible for certificate
    if not enrollment.can_award_certificate():
        reasons = []
        if enrollment.certificate_generated:
            reasons.append("Certificate already generated")
        elif enrollment.completion_percentage < 100:
            reasons.append(f"Completion percentage is {enrollment.completion_percentage}% (must be 100%)")
        elif not enrollment.instructor_marked_completed:
            reasons.append("Instructor has not marked this course as completed")
        else:
            from core.models import CertificateSettings
            try:
                cert_settings = CertificateSettings.objects.get(course=enrollment.course)
                if not cert_settings.is_enabled:
                    reasons.append("Certificates are not enabled for this course")
            except CertificateSettings.DoesNotExist:
                reasons.append("Certificates are not enabled for this course")
        
        reason_text = " • ".join(reasons) if reasons else "Not eligible for certificate"
        messages.error(request, f"❌ Cannot generate certificate: {reason_text}")
        return redirect('courses:enrollment_detail', enrollment_id=enrollment.id)
    
    # Generate certificate
    try:
        pdf_buffer = enrollment.generate_certificate()
        
        if not pdf_buffer:
            messages.error(request, "Error generating certificate. Please try again.")
            return redirect('courses:enrollment_detail', enrollment_id=enrollment.id)
        
        # Return PDF response
        student_name = enrollment.student.get_full_name() or enrollment.student.username
        course_name = enrollment.course.title.replace(' ', '_')
        filename = f"{student_name}_{course_name}_certificate.pdf"
        
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        messages.success(request, "✅ Certificate generated successfully!")
        return response
    except Exception as e:
        import logging
        logging.error(f"Error generating certificate for enrollment {enrollment.id}: {str(e)}")
        messages.error(request, f"Error generating certificate: {str(e)}")
        return redirect('courses:enrollment_detail', enrollment_id=enrollment.id)


@login_required
def download_certificate(request, enrollment_id):
    """Download an already-generated certificate without re-running eligibility checks."""
    from courses.certificate import generate_certificate_pdf

    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    is_owner = enrollment.student == request.user
    is_instructor = enrollment.course.instructor == request.user or request.user.is_superuser
    if not (is_owner or is_instructor):
        raise PermissionDenied("You don't have permission to access this certificate.")

    # If certificate was never generated yet, fall through to the normal generate flow
    if not enrollment.certificate_generated:
        return generate_certificate(request, enrollment_id)

    # Re-render the PDF from data (certificates are not stored as files, they are generated on demand)
    try:
        pdf_buffer = generate_certificate_pdf(enrollment)
        if not pdf_buffer:
            messages.error(request, "Error generating certificate. Please try again.")
            return redirect('courses:enrollment_detail', enrollment_id=enrollment.id)

        student_name = enrollment.student.get_full_name() or enrollment.student.username
        course_name  = enrollment.course.title.replace(' ', '_')
        filename     = f"{student_name}_{course_name}_certificate.pdf"

        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        import logging
        logging.error(f"Error downloading certificate for enrollment {enrollment.id}: {str(e)}")
        messages.error(request, f"Error downloading certificate: {str(e)}")
        return redirect('courses:enrollment_detail', enrollment_id=enrollment.id)


@login_required
def enrollment_detail(request, enrollment_id):
    """Show enrollment details including completion status and certificate."""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Check permissions
    is_owner = enrollment.student == request.user
    is_instructor = enrollment.course.instructor == request.user or request.user.is_superuser
    
    if not (is_owner or is_instructor):
        raise PermissionDenied("You don't have permission to view this enrollment.")
    
    # Get payment info if available
    from payments.models import Payment
    payment = Payment.objects.filter(enrollment=enrollment).first()
    
    # Recalculate completion percentage to ensure it's current
    enrollment.recalculate_completion_percentage()
    
    context = {
        'enrollment': enrollment,
        'course': enrollment.course,
        'student': enrollment.student,
        'payment': payment,
        'is_owner': is_owner,
        'is_instructor': is_instructor,
        'completion_percentage': enrollment.completion_percentage,
    }
    
    return render(request, 'courses/enrollment_detail.html', context)


@login_required
def get_student_courses(request):
    """API endpoint to fetch filtered courses for a student."""
    from django.http import JsonResponse
    
    if not request.user.is_student():
        return JsonResponse({'success': False, 'message': 'Only students can access this endpoint.'}, status=403)
    
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Only GET requests are allowed.'}, status=400)
    
    try:
        filter_type = request.GET.get('filter', 'all').lower()
        
        # Get all enrollments for the student
        enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__instructor')
        
        # Apply filter based on filter_type
        if filter_type == 'enrolled':
            # All enrolled courses (approved or not)
            filtered_enrollments = enrollments
        elif filter_type == 'pending_payments':
            # Courses with pending payments (enrolled but not approved)
            filtered_enrollments = enrollments.filter(approved=False)
        elif filter_type == 'paid':
            # Courses with approved payments (paid/active)
            filtered_enrollments = enrollments.filter(approved=True, completed=False)
        elif filter_type == 'completed':
            # Completed courses
            filtered_enrollments = enrollments.filter(completed=True)
        else:  # 'all' as default
            filtered_enrollments = enrollments
        
        # Build response data
        courses_data = []
        for enrollment in filtered_enrollments:
            course = enrollment.course
            
            # Get payment info
            from payments.models import Payment
            payment = Payment.objects.filter(enrollment=enrollment).first()
            
            course_data = {
                'id': course.id,
                'title': course.title,
                'instructor': f"{course.instructor.first_name} {course.instructor.last_name}".strip() or course.instructor.username,
                'price': str(course.price),
                'status': 'Completed' if enrollment.completed else ('Approved' if enrollment.approved else 'Pending'),
                'enrollment_id': enrollment.id,
                'approved': enrollment.approved,
                'completed': enrollment.completed,
                'enrolled_at': enrollment.enrolled_at.strftime('%Y-%m-%d'),
            }
            
            # Add payment info if available
            if payment:
                course_data['has_payment'] = True
                course_data['payment_approved'] = payment.approved
            else:
                course_data['has_payment'] = False
                course_data['payment_approved'] = False
            
            courses_data.append(course_data)
        
        return JsonResponse({
            'success': True,
            'filter': filter_type,
            'count': len(courses_data),
            'courses': courses_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE VIEWS  (instructor)
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def module_manager(request, course_id):
    """Instructor: manage modules & lessons for a course."""
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    modules = course.modules.prefetch_related('lessons').order_by('order', 'created_at')
    return render(request, 'courses/module_manager.html', {
        'course':  course,
        'modules': modules,
    })


@login_required
def create_module(request, course_id):
    """Instructor: create a new module inside a course."""
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not title:
            messages.error(request, 'Module title is required.')
        else:
            last_order = course.modules.order_by('-order').values_list('order', flat=True).first() or 0
            Module.objects.create(
                course=course, title=title, description=description,
                order=last_order + 1,
            )
            try:
                from notifications.utils import notify_many
                from django.contrib.auth import get_user_model
                User = get_user_model()
                student_ids = Enrollment.objects.filter(
                    course=course, approved=True
                ).values_list('student_id', flat=True)
                students = User.objects.filter(pk__in=student_ids)
                notify_many(
                    recipients=students,
                    notif_type='assignment_new',
                    title=f'New module added: {title}',
                    message=f'A new module was added to {course.title}.',
                    link=reverse('courses:course_detail', args=[course.pk]),
                )
            except Exception:
                pass
            messages.success(request, f'Module "{title}" created.')
    return redirect('courses:module_manager', course_id=course.pk)


@login_required
def edit_module(request, module_id):
    """Instructor: edit module title / description / published state."""
    module = get_object_or_404(Module, pk=module_id, course__instructor=request.user)
    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        is_published = request.POST.get('is_published') == 'on'
        if title:
            module.title        = title
            module.description  = description
            module.is_published = is_published
            module.save(update_fields=['title', 'description', 'is_published'])
            messages.success(request, 'Module updated.')
    return redirect('courses:module_manager', course_id=module.course_id)


@login_required
def delete_module(request, module_id):
    """Instructor: delete a module (and all its lessons)."""
    module    = get_object_or_404(Module, pk=module_id, course__instructor=request.user)
    course_id = module.course_id
    if request.method == 'POST':
        module.delete()
        messages.success(request, 'Module deleted.')
    return redirect('courses:module_manager', course_id=course_id)


@login_required
def reorder_modules(request):
    """AJAX: save new module order. POST body: order=id,id,id"""
    from django.http import JsonResponse
    if request.method != 'POST' or not request.user.is_instructor():
        return JsonResponse({'success': False}, status=403)
    ids = [i for i in request.POST.get('order', '').split(',') if i.strip().isdigit()]
    for idx, mod_id in enumerate(ids):
        Module.objects.filter(pk=int(mod_id), course__instructor=request.user).update(order=idx)
    return JsonResponse({'success': True})


# ═══════════════════════════════════════════════════════════════════════════════
# LESSON VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def create_lesson(request, module_id):
    """Instructor: create a new lesson inside a module."""
    module = get_object_or_404(Module, pk=module_id, course__instructor=request.user)
    if request.method == 'POST':
        title            = request.POST.get('title', '').strip()
        content          = request.POST.get('content', '').strip()
        youtube_url      = request.POST.get('youtube_url', '').strip()
        dur_raw          = request.POST.get('duration_minutes', '').strip()
        is_published     = request.POST.get('is_published') == 'on'
        resource_file    = request.FILES.get('resource_file')

        if not title:
            messages.error(request, 'Lesson title is required.')
            return render(request, 'courses/lesson_form.html', {
                'module': module, 'course': module.course, 'action': 'Create'
            })

        last_order = module.lessons.order_by('-order').values_list('order', flat=True).first() or 0
        lesson = Lesson.objects.create(
            module=module,
            title=title,
            content=content,
            youtube_url=youtube_url,
            resource_file=resource_file,
            order=last_order + 1,
            duration_minutes=int(dur_raw) if dur_raw.isdigit() else None,
            is_published=is_published,
        )
        try:
            from notifications.utils import notify_many
            from django.contrib.auth import get_user_model
            User = get_user_model()
            student_ids = Enrollment.objects.filter(
                course=module.course, approved=True
            ).values_list('student_id', flat=True)
            students = User.objects.filter(pk__in=student_ids)
            notify_many(
                recipients=students,
                notif_type='assignment_new',
                title=f'New lesson: {title}',
                message=f'{module.title} in {module.course.title} has a new lesson.',
                link=reverse('courses:lesson_detail', args=[lesson.pk]),
            )
        except Exception:
            pass
        messages.success(request, f'Lesson "{title}" created.')
        return redirect('courses:module_manager', course_id=module.course_id)

    return render(request, 'courses/lesson_form.html', {
        'module': module, 'course': module.course, 'action': 'Create'
    })


@login_required
def edit_lesson(request, lesson_id):
    """Instructor: edit an existing lesson."""
    lesson = get_object_or_404(Lesson, pk=lesson_id, module__course__instructor=request.user)
    module = lesson.module
    if request.method == 'POST':
        lesson.title        = request.POST.get('title', lesson.title).strip()
        lesson.content      = request.POST.get('content', '').strip()
        lesson.youtube_url  = request.POST.get('youtube_url', '').strip()
        lesson.is_published = request.POST.get('is_published') == 'on'
        dur = request.POST.get('duration_minutes', '').strip()
        lesson.duration_minutes = int(dur) if dur.isdigit() else None
        if request.FILES.get('resource_file'):
            lesson.resource_file = request.FILES['resource_file']
        if request.POST.get('clear_resource') == 'yes' and lesson.resource_file:
            lesson.resource_file.delete(save=False)
            lesson.resource_file = None
        lesson.save()
        messages.success(request, 'Lesson updated.')
        return redirect('courses:module_manager', course_id=module.course_id)

    return render(request, 'courses/lesson_form.html', {
        'lesson': lesson, 'module': module,
        'course': module.course, 'action': 'Edit',
    })


@login_required
def delete_lesson(request, lesson_id):
    """Instructor: delete a lesson."""
    lesson    = get_object_or_404(Lesson, pk=lesson_id, module__course__instructor=request.user)
    course_id = lesson.module.course_id
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, 'Lesson deleted.')
    return redirect('courses:module_manager', course_id=course_id)


@login_required
def reorder_lessons(request):
    """AJAX: save lesson order within a module."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)
    ids = [i for i in request.POST.get('order', '').split(',') if i.strip().isdigit()]
    for idx, lesson_id in enumerate(ids):
        Lesson.objects.filter(
            pk=int(lesson_id), module__course__instructor=request.user
        ).update(order=idx)
    return JsonResponse({'success': True})


@login_required
def lesson_detail(request, lesson_id):
    """Student (and instructor preview): view a single lesson."""
    lesson = get_object_or_404(Lesson, pk=lesson_id, is_published=True)
    module = lesson.module
    course = module.course

    # Access: enrolled+approved student OR the course instructor
    is_instructor_preview = request.user.is_instructor() and course.instructor == request.user
    enrollment = None
    if request.user.is_student():
        enrollment = Enrollment.objects.filter(
            student=request.user, course=course, approved=True
        ).first()
        if not enrollment:
            messages.error(request, 'You must be enrolled in this course to view lessons.')
            return redirect('courses:course_detail', pk=course.pk)

    is_completed = (
        LessonCompletion.objects.filter(student=request.user, lesson=lesson).exists()
        if request.user.is_student() else False
    )

    # Record / refresh last-accessed timestamp for this student+lesson
    if request.user.is_student() and enrollment:
        lp, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
        lp.save()  # triggers auto_now on last_accessed

    # Prev / Next navigation within the module
    module_lessons = list(module.lessons.filter(is_published=True).order_by('order', 'created_at'))
    current_idx    = next((i for i, l in enumerate(module_lessons) if l.pk == lesson.pk), 0)
    prev_lesson    = module_lessons[current_idx - 1] if current_idx > 0 else None
    next_lesson    = module_lessons[current_idx + 1] if current_idx < len(module_lessons) - 1 else None

    # Full course outline for sidebar
    all_modules = course.modules.filter(is_published=True).prefetch_related('lessons')

    # Which lessons has this student already completed?
    completed_ids = set(
        LessonCompletion.objects.filter(
            student=request.user,
            lesson__module__course=course,
        ).values_list('lesson_id', flat=True)
    ) if request.user.is_student() else set()

    return render(request, 'courses/lesson_detail.html', {
        'lesson':               lesson,
        'module':               module,
        'course':               course,
        'enrollment':           enrollment,
        'is_completed':         is_completed,
        'prev_lesson':          prev_lesson,
        'next_lesson':          next_lesson,
        'all_modules':          all_modules,
        'completed_ids':        completed_ids,
        'embed_url':            lesson.get_youtube_embed_url(),
        'is_instructor_preview': is_instructor_preview,
    })


@login_required
def mark_lesson_complete(request, lesson_id):
    """AJAX POST: toggle lesson completion for the logged-in student."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)
    if not request.user.is_student():
        return JsonResponse({'success': False, 'message': 'Students only'}, status=403)

    lesson = get_object_or_404(Lesson, pk=lesson_id, is_published=True)
    enrollment = Enrollment.objects.filter(
        student=request.user, course=lesson.module.course, approved=True
    ).first()
    if not enrollment:
        return JsonResponse({'success': False, 'message': 'Not enrolled'}, status=403)

    obj, created = LessonCompletion.objects.get_or_create(
        student=request.user, lesson=lesson
    )
    if not created:
        obj.delete()
        completed = False
    else:
        completed = True

    pct        = enrollment.get_completion_percentage()
    done, total = enrollment.get_lesson_stats()

    return JsonResponse({
        'success':   True,
        'completed': completed,
        'progress':  pct,
        'done':      done,
        'total':     total,
    })


# ─── Time tracking ────────────────────────────────────────────────────────────

@login_required
def log_lesson_time(request, lesson_id):
    """AJAX POST: add seconds spent on a lesson page to LessonProgress."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    lesson = get_object_or_404(Lesson, pk=lesson_id, is_published=True)
    if not request.user.is_student():
        return JsonResponse({'ok': True})  # silently ignore instructors
    try:
        seconds = int(request.POST.get('seconds', 0))
    except (ValueError, TypeError):
        seconds = 0
    if seconds <= 0:
        return JsonResponse({'ok': True})
    lp, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
    lp.time_spent_seconds += seconds
    lp.save()
    return JsonResponse({'ok': True, 'total_seconds': lp.time_spent_seconds})


# ─── Student course progress ──────────────────────────────────────────────────

@login_required
def course_progress(request, course_id):
    """Detailed lesson-by-lesson progress page for an enrolled student."""
    from django.db.models import Prefetch
    from quizzes.models import Quiz, QuizAttempt
    from assignments.models import Assignment, AssignmentSubmission

    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(Enrollment, course=course, student=request.user, approved=True)

    # Build per-module data
    modules = (
        course.modules.filter(is_published=True)
        .prefetch_related(
            Prefetch('lessons', queryset=Lesson.objects.filter(is_published=True).order_by('order'))
        )
        .order_by('order')
    )
    completed_ids = set(
        LessonCompletion.objects.filter(
            student=request.user, lesson__module__course=course
        ).values_list('lesson_id', flat=True)
    )
    progress_map = {
        lp.lesson_id: lp
        for lp in LessonProgress.objects.filter(
            student=request.user, lesson__module__course=course
        )
    }

    module_data = []
    for module in modules:
        lessons = list(module.lessons.filter(is_published=True).order_by('order'))
        lesson_rows = []
        module_done = 0
        for lesson in lessons:
            done = lesson.pk in completed_ids
            if done:
                module_done += 1
            prog = progress_map.get(lesson.pk)
            lesson_rows.append({
                'lesson': lesson,
                'is_completed': done,
                'last_accessed': prog.last_accessed if prog else None,
                'time_spent_display': prog.time_spent_display() if prog else None,
                'time_spent_seconds': prog.time_spent_seconds if prog else 0,
            })
        total = len(lessons)
        module_data.append({
            'module': module,
            'lesson_rows': lesson_rows,
            'done_count': module_done,
            'total_count': total,
            'pct': int(module_done / total * 100) if total else 0,
        })

    done_lessons, total_lessons = enrollment.get_lesson_stats()
    overall_pct = enrollment.get_completion_percentage()

    # Total time spent across course
    total_time_seconds = LessonProgress.objects.filter(
        student=request.user, lesson__module__course=course
    ).aggregate(total=Sum('time_spent_seconds'))['total'] or 0

    # Last activity
    last_lp = LessonProgress.objects.filter(
        student=request.user, lesson__module__course=course
    ).order_by('-last_accessed').first()

    # Quizzes
    quizzes = Quiz.objects.filter(course=course, is_published=True)
    quiz_rows = []
    for quiz in quizzes:
        best = quiz.student_best_attempt(request.user)
        quiz_rows.append({
            'quiz': quiz,
            'best_attempt': best,
            'passed': quiz.student_passed(request.user),
        })

    # Assignments
    assignments = Assignment.objects.filter(course=course, is_active=True)
    assignment_rows = []
    for assignment in assignments:
        try:
            sub = AssignmentSubmission.objects.get(assignment=assignment, student=request.user)
        except AssignmentSubmission.DoesNotExist:
            sub = None
        assignment_rows.append({'assignment': assignment, 'submission': sub})

    context = {
        'course': course,
        'enrollment': enrollment,
        'module_data': module_data,
        'done_lessons': done_lessons,
        'total_lessons': total_lessons,
        'overall_pct': overall_pct,
        'total_time_seconds': total_time_seconds,
        'last_activity': last_lp.last_accessed if last_lp else None,
        'quiz_rows': quiz_rows,
        'assignment_rows': assignment_rows,
    }
    return render(request, 'courses/course_progress.html', context)


# ─── Instructor live sessions list ────────────────────────────────────────────

@login_required
def instructor_live_sessions(request):
    """All live sessions (upcoming + recent past) across the instructor's courses."""
    from django.utils import timezone
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can view live sessions.")
        return redirect('dashboard:index')

    courses = Course.objects.filter(instructor=request.user)
    now = timezone.now()

    upcoming = (
        LiveSession.objects
        .filter(course__in=courses, scheduled_at__gte=now)
        .select_related('course')
        .order_by('scheduled_at')
    )
    past = (
        LiveSession.objects
        .filter(course__in=courses, scheduled_at__lt=now)
        .select_related('course')
        .order_by('-scheduled_at')[:20]
    )

    context = {
        'upcoming': upcoming,
        'past': past,
        'courses': courses,
        'upcoming_count': upcoming.count(),
    }
    return render(request, 'courses/instructor_live_sessions.html', context)


# ─── Instructor analytics ─────────────────────────────────────────────────────

@login_required
def analytics_overview(request):
    """Lists all instructor courses so the instructor can pick one to analyse."""
    from django.core.paginator import Paginator
    from payments.models import Payment

    if not request.user.is_instructor():
        messages.error(request, "Only instructors can view analytics.")
        return redirect('courses:course_list')

    query = request.GET.get('q', '').strip()
    courses_qs = Course.objects.filter(instructor=request.user).prefetch_related(
        'enrollments', 'resources'
    ).order_by('title')

    if query:
        courses_qs = courses_qs.filter(title__icontains=query)

    course_rows = []
    for course in courses_qs:
        enrollments = course.enrollments.all()
        approved = Payment.objects.filter(enrollment__course=course, approved=True).count()
        revenue = float(course.price) * approved
        course_rows.append({
            'course': course,
            'total_enrollments': enrollments.count(),
            'approved': approved,
            'revenue': revenue,
        })

    paginator = Paginator(course_rows, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'total_courses': courses_qs.count(),
    }
    return render(request, 'courses/analytics_overview.html', context)


@login_required
def instructor_analytics(request, course_id):
    """Analytics dashboard for an instructor's course."""
    from django.http import JsonResponse
    from django.db.models import Count, Avg
    from django.db.models.functions import TruncMonth
    from datetime import timedelta
    from quizzes.models import Quiz, QuizAttempt
    from assignments.models import Assignment, AssignmentSubmission

    course = get_object_or_404(Course, pk=course_id)
    if not (course.instructor == request.user or request.user.is_superuser):
        raise PermissionDenied

    twelve_months_ago = timezone.now() - timedelta(days=365)
    seven_days_ago = timezone.now() - timedelta(days=7)

    # ── Enrollment trends (last 12 months) ───────────────────────────────────
    trend_qs = (
        Enrollment.objects.filter(course=course, enrolled_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('enrolled_at'))
        .values('month')
        .annotate(total=Count('id'), approved=Count('id', filter=Q(approved=True)))
        .order_by('month')
    )
    trend_labels   = [e['month'].strftime('%b %Y') for e in trend_qs]
    trend_totals   = [e['total']    for e in trend_qs]
    trend_approved = [e['approved'] for e in trend_qs]

    # ── Revenue (approved enrollments × course price, monthly) ───────────────
    rev_qs = (
        Enrollment.objects.filter(course=course, approved=True, enrolled_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('enrolled_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    revenue_labels = [e['month'].strftime('%b %Y') for e in rev_qs]
    revenue_values = [float(e['count'] * course.price) for e in rev_qs]
    total_revenue  = float(Enrollment.objects.filter(course=course, approved=True).count() * course.price)

    # ── Payment methods ───────────────────────────────────────────────────────
    payment_methods = list(course.payment_methods.all())

    # ── Completion rates ──────────────────────────────────────────────────────
    total_approved  = Enrollment.objects.filter(course=course, approved=True).count()
    total_completed = Enrollment.objects.filter(course=course, approved=True, completed=True).count()
    completion_rate = int(total_completed / total_approved * 100) if total_approved else 0

    # ── Quiz pass rates ───────────────────────────────────────────────────────
    quizzes = Quiz.objects.filter(course=course, is_published=True)
    quiz_stats = []
    for quiz in quizzes:
        attempts = QuizAttempt.objects.filter(quiz=quiz, is_complete=True)
        total_att = attempts.count()
        passed_att = attempts.filter(passed=True).count()
        avg_score = attempts.aggregate(avg=Avg('score'))['avg'] or 0
        quiz_stats.append({
            'quiz': quiz,
            'total_attempts': total_att,
            'passed_attempts': passed_att,
            'pass_rate': int(passed_att / total_att * 100) if total_att else 0,
            'avg_score': round(float(avg_score), 1),
        })

    # ── Resource downloads ────────────────────────────────────────────────────
    resource_stats = []
    for resource in course.resources.all():
        resource_stats.append({
            'resource': resource,
            'download_count': resource.downloads.count(),
        })

    # ── Student breakdown ─────────────────────────────────────────────────────
    approved_enrollments = (
        Enrollment.objects.filter(course=course, approved=True)
        .select_related('student')
        .order_by('enrolled_at')
    )
    student_data = []
    for enrollment in approved_enrollments:
        done, total_l = enrollment.get_lesson_stats()
        pct = enrollment.get_completion_percentage()
        last_lp = (
            LessonProgress.objects
            .filter(student=enrollment.student, lesson__module__course=course)
            .order_by('-last_accessed')
            .first()
        )
        total_time = (
            LessonProgress.objects
            .filter(student=enrollment.student, lesson__module__course=course)
            .aggregate(t=Sum('time_spent_seconds'))['t'] or 0
        )
        is_active    = last_lp and last_lp.last_accessed >= seven_days_ago
        is_struggling = pct < 30 and (last_lp is not None)
        is_at_risk   = last_lp is None and not enrollment.completed

        quiz_passed = sum(1 for q in quizzes if q.student_passed(enrollment.student))
        assign_submitted = AssignmentSubmission.objects.filter(
            assignment__course=course, student=enrollment.student
        ).count()

        h, rem = divmod(total_time, 3600)
        m_disp = divmod(rem, 60)[0]
        time_display = f"{h}h {m_disp}m" if h else (f"{m_disp}m" if m_disp else "—")

        student_data.append({
            'student': enrollment.student,
            'enrollment': enrollment,
            'pct': pct,
            'done_lessons': done,
            'total_lessons': total_l,
            'last_activity': last_lp.last_accessed if last_lp else None,
            'time_display': time_display,
            'is_active': is_active,
            'is_struggling': is_struggling,
            'is_at_risk': is_at_risk,
            'quiz_passed': quiz_passed,
            'quiz_total': quizzes.count(),
            'assign_submitted': assign_submitted,
        })
    student_data.sort(key=lambda x: x['pct'], reverse=True)

    active_count    = sum(1 for s in student_data if s['is_active'])
    struggling_count = sum(1 for s in student_data if s['is_struggling'])
    at_risk_count   = sum(1 for s in student_data if s['is_at_risk'])

    context = {
        'course': course,
        'total_approved': total_approved,
        'total_completed': total_completed,
        'completion_rate': completion_rate,
        'total_revenue': total_revenue,
        'trend_labels': trend_labels,
        'trend_totals': trend_totals,
        'trend_approved': trend_approved,
        'revenue_labels': revenue_labels,
        'revenue_values': revenue_values,
        'payment_methods': payment_methods,
        'quiz_stats': quiz_stats,
        'resource_stats': resource_stats,
        'student_data': student_data,
        'active_count': active_count,
        'struggling_count': struggling_count,
        'at_risk_count': at_risk_count,
    }
    return render(request, 'courses/instructor_analytics.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# LIVE SESSIONS - Instructor: Add, Edit, Delete
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def add_session(request, course_id):
    """Instructor adds a live session to a course."""
    course = get_object_or_404(Course, pk=course_id)
    
    # Check if user is the instructor
    if request.user != course.instructor:
        messages.error(request, "You don't have permission to add sessions to this course.")
        return redirect('courses:course_detail', pk=course_id)
    
    if request.method == 'POST':
        form = LiveSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            messages.success(request, f"Live session '{session.title}' created successfully!")
            return redirect('courses:instructor_live_sessions')
    else:
        form = LiveSessionForm()
    
    return render(request, 'courses/session_form.html', {
        'form': form,
        'course': course,
        'action': 'Add',
    })


@login_required
def edit_session(request, session_id):
    """Instructor edits a live session."""
    session = get_object_or_404(LiveSession, pk=session_id)
    course = session.course
    
    # Check if user is the instructor
    if request.user != course.instructor:
        messages.error(request, "You don't have permission to edit this session.")
        return redirect('courses:course_detail', pk=course.id)
    
    if request.method == 'POST':
        form = LiveSessionForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f"Live session '{session.title}' updated successfully!")
            return redirect('courses:instructor_live_sessions')
    else:
        form = LiveSessionForm(instance=session)
    
    return render(request, 'courses/session_form.html', {
        'form': form,
        'course': course,
        'action': 'Edit',
        'session': session,
    })


@login_required
def delete_session(request, session_id):
    """Instructor deletes a live session."""
    session = get_object_or_404(LiveSession, pk=session_id)
    course = session.course
    session_title = session.title
    
    # Check if user is the instructor
    if request.user != course.instructor:
        messages.error(request, "You don't have permission to delete this session.")
        return redirect('courses:course_detail', pk=course.id)
    
    if request.method == 'POST':
        session.delete()
        messages.success(request, f"Live session '{session_title}' deleted successfully!")
        return redirect('courses:instructor_live_sessions')
    
    return render(request, 'courses/session_confirm_delete.html', {
        'session': session,
        'course': course,
    })


# ─────────────────────────────────────────────────────────────────────────────
# COUPON MANAGEMENT - Instructor/Admin: Create, Edit, Delete
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def coupon_list(request):
    """List all coupons (admin/instructor view)."""
    if not (request.user.is_superuser or request.user.is_instructor()):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('courses:course_list')
    
    # Base query
    if request.user.is_superuser:
        coupons = Coupon.objects.all()
    else:
        coupons = Coupon.objects.filter(created_by=request.user)
    
    # Apply filters
    search_query = request.GET.get('search', '').strip()
    if search_query:
        coupons = coupons.filter(code__icontains=search_query)
    
    status_filter = request.GET.get('status', '').strip()
    if status_filter == 'active':
        coupons = coupons.filter(is_active=True)
    elif status_filter == 'inactive':
        coupons = coupons.filter(is_active=False)
    elif status_filter == 'expired':
        now = timezone.now()
        coupons = coupons.filter(valid_until__lt=now, is_active=True)
    
    type_filter = request.GET.get('type', '').strip()
    if type_filter == 'percentage':
        coupons = coupons.filter(discount_type='percentage')
    elif type_filter == 'fixed':
        coupons = coupons.filter(discount_type='fixed')
    
    # Order by created date
    coupons = coupons.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(coupons, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    filtered_count = coupons.count()

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'filtered_count': filtered_count,
        'is_admin': request.user.is_superuser,
        'now': timezone.now(),
        'search_query': search_query,
        'status_filter': status_filter,
        'type_filter': type_filter,
    }
    return render(request, 'courses/coupon_list.html', context)


@login_required
def create_coupon(request):
    """Create a new coupon code."""
    if not (request.user.is_superuser or request.user.is_instructor()):
        messages.error(request, "You don't have permission to create coupons.")
        return redirect('courses:course_list')
    
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save(commit=False)
            coupon.created_by = request.user
            coupon.save()
            form.save_m2m()  # Save M2M relationships (courses)
            messages.success(request, f"Coupon '{coupon.code}' created successfully!")
            return redirect('courses:coupon_list')
    else:
        form = CouponForm()
    
    # For instructors, limit courses to their own courses
    if not request.user.is_superuser:
        form.fields['courses'].queryset = Course.objects.filter(instructor=request.user)
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'courses/coupon_form.html', context)


@login_required
def edit_coupon(request, coupon_id):
    """Edit an existing coupon."""
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    
    # Check permissions
    if not (request.user.is_superuser or coupon.created_by == request.user):
        messages.error(request, "You don't have permission to edit this coupon.")
        return redirect('courses:coupon_list')
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f"Coupon '{coupon.code}' updated successfully!")
            return redirect('courses:coupon_list')
    else:
        form = CouponForm(instance=coupon)
    
    # For instructors, limit courses to their own courses
    if not request.user.is_superuser:
        form.fields['courses'].queryset = Course.objects.filter(instructor=request.user)
    
    context = {
        'form': form,
        'coupon': coupon,
        'action': 'Edit',
    }
    return render(request, 'courses/coupon_form.html', context)


@login_required
def delete_coupon(request, coupon_id):
    """Delete a coupon."""
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    
    # Check permissions
    if not (request.user.is_superuser or coupon.created_by == request.user):
        messages.error(request, "You don't have permission to delete this coupon.")
        return redirect('courses:coupon_list')
    
    if request.method == 'POST':
        coupon_code = coupon.code
        coupon.delete()
        messages.success(request, f"Coupon '{coupon_code}' deleted successfully!")
        return redirect('courses:coupon_list')
    
    context = {
        'coupon': coupon,
    }
    return render(request, 'courses/coupon_confirm_delete.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# COUPON VALIDATION API - AJAX Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def validate_coupon_api(request):
    """API endpoint to validate a coupon code and return discount info."""
    import json
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        coupon_code = data.get('code', '').strip().upper()
        course_id = data.get('course_id')
        
        if not coupon_code or not course_id:
            return JsonResponse({
                'valid': False,
                'error': 'Missing coupon code or course ID'
            })
        
        # Get the course
        course = get_object_or_404(Course, pk=course_id)
        
        # Get the coupon
        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'error': 'Coupon code not found'
            })
        
        # Validate the coupon
        is_valid, message = coupon.is_valid()
        if not is_valid:
            return JsonResponse({
                'valid': False,
                'error': f'Coupon is {message.lower()}'
            })
        
        # Check if coupon applies to this course
        if not coupon.is_valid_for_course(course):
            return JsonResponse({
                'valid': False,
                'error': 'This coupon does not apply to this course'
            })
        
        # Calculate discount
        discount = coupon.calculate_discount(course.price)
        final_price = coupon.get_final_price(course.price)
        
        return JsonResponse({
            'valid': True,
            'coupon_code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount_value': float(coupon.discount_value),
            'discount_amount': float(discount),
            'original_price': float(course.price),
            'final_price': float(final_price),
            'savings': float(discount),
            'message': f'Great! You saved {coupon.discount_type.lower() if coupon.discount_type == "PERCENTAGE" else "TZS"}'
        })
    
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': f'Error: {str(e)}'
        }, status=500)
