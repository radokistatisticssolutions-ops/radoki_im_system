from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .forms import RegisterForm, ProfileUpdateForm
import logging

logger = logging.getLogger(__name__)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('core:home')
    
    # Get referral code from URL parameter
    referral_code = request.GET.get('ref', None)
    referral_link = None
    
    # Validate referral code if provided
    if referral_code:
        from referrals.models import ReferralLink
        try:
            referral_link = ReferralLink.objects.get(code=referral_code)
        except ReferralLink.DoesNotExist:
            messages.warning(request, 'Invalid referral code. Registering without referral.')
            referral_code = None
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Create referral record if code was provided
                if referral_code and referral_link:
                    from referrals.models import Referral
                    try:
                        Referral.objects.create(
                            referral_link=referral_link,
                            referred_user=user,
                            status=Referral.Status.PENDING
                        )
                        messages.success(request, f'Account created! You were referred by someone earning them a reward!')
                    except Exception as e:
                        logger.warning(f'Failed to create referral record: {str(e)}')
                        messages.success(request, 'Account created successfully! Please log in.')
                else:
                    messages.success(request, 'Account created successfully! Please log in.')
                
                return redirect('accounts:login')
            except Exception as e:
                logger.error(f'Registration error: {str(e)}', exc_info=True)
                messages.error(request, f'Registration failed: {str(e)}')
    else:
        form = RegisterForm()
    
    context = {
        'form': form,
        'referral_code': referral_code,
        'referral_link': referral_link,
    }
    
    return render(request, 'accounts/register.html', context)


def login_view(request):
    from django.contrib.auth import authenticate, login
    
    # If already authenticated, keep admin users in admin zone; normal users go to site home.
    if request.user.is_authenticated:
        if request.path.startswith('/admin/') and request.user.is_staff:
            return redirect('/admin/')
        if request.session.get('_normal_site_auth'):
            return redirect('core:home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            # Signal the next page to play a login beep (consumed once by context processor).
            request.session['just_logged_in'] = True
            # Mark that this user explicitly logged in via the normal site login form.
            # For admin login, do not set _normal_site_auth, to avoid redirect loops to normal home.
            if not request.path.startswith('/admin/'):
                request.session['_normal_site_auth'] = True
            
            # ✅ Distinguish between admin login vs normal login
            if request.path.startswith('/admin/'):
                # Admin login page → go to admin panel
                if user.is_superuser:
                    return redirect('/admin/')
                elif user.is_staff:
                    # Staff but not superuser → limited admin access
                    return redirect('/admin/')
                else:
                    # Non-staff/non-superuser trying admin login → send them to normal dashboard
                    return redirect('dashboard:index')
            else:
                # Normal login page → role-based dashboards
                if user.is_instructor():
                    return redirect('dashboard:index')
                elif user.is_superuser:
                    # Superuser with instructor role → dashboard
                    return redirect('dashboard:index')
                elif user.is_staff:
                    # Staff but not superuser logging in via normal page → dashboard
                    return redirect('dashboard:index')
                else:
                    # Students and other users
                    return redirect('dashboard:index')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')



def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('accounts:login')


def auto_logout_view(request):
    """AJAX endpoint for client-side inactivity logout. Invalidates session server-side."""
    from django.contrib.auth import logout
    from django.http import JsonResponse
    if request.method == 'POST' and request.user.is_authenticated:
        logout(request)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'ignored'}, status=400)


@login_required
def profile_preview(request, student_id=None):
    """Display user's profile information in read-only mode.
    
    If student_id is provided, instructor can view that student's profile.
    Otherwise, view the current user's profile.
    """
    from django.shortcuts import get_object_or_404
    from courses.models import Course, Enrollment
    
    if student_id:
        # Instructor is trying to view a student's profile
        if not request.user.is_instructor():
            messages.error(request, "Only instructors can view student profiles.")
            return redirect('accounts:profile_preview')
        
        # Get the student
        target_user = get_object_or_404(request.user.__class__, id=student_id, role='student')
        
        # Check if the student is enrolled in any of the instructor's courses
        is_enrolled = Enrollment.objects.filter(
            student=target_user,
            course__instructor=request.user
        ).exists()
        
        if not is_enrolled:
            messages.error(request, "This student is not enrolled in any of your courses.")
            return redirect('courses:instructor_students')
        
        # Use the student profile view template
        context = {
            'viewed_student': target_user,
        }
        return render(request, 'accounts/student_profile_view.html', context)
    else:
        # View own profile
        context = {
            'user': request.user,
            'is_preview': True,
        }
        return render(request, 'accounts/profile_preview.html', context)


@login_required
def profile_update(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile_update')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})


# Debug view to preview password reset email template
def preview_password_reset_email(request):
    """Preview the password reset email template without sending an actual email"""
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.first()  # Get first user or create a test one
    
    if not user:
        # Create a test user if none exists
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
    
    # Generate token and uid
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    
    # Render email template with context (matching Django's PasswordResetView context)
    context = {
        'user': user,
        'protocol': request.scheme,
        'domain': request.get_host(),
        'uid': uid,  # Must be 'uid' not 'uidb64' to match template
        'token': token,
        'site_name': 'Radoki IM System'
    }
    
    email_html = render_to_string('accounts/password_reset_email.html', context)
    
    return render(request, 'accounts/email_preview.html', {
        'email_html': email_html,
        'user': user
    })


# ✅ New helper view for role-based redirect after login
def role_based_redirect(request):
    """Redirect users based on role after login"""
    user = request.user
    if user.is_superuser or user.is_staff:
        return redirect('/admin/')
    else:
        return redirect('dashboard:index')
