from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth.models import AnonymousUser


class AuthenticationMiddleware:
    """
    Separates admin sessions from normal-site sessions.

    Logging into /admin/ does NOT grant access to the normal user site.
    The user must explicitly log in via /accounts/login/ which sets the
    '_normal_site_auth' session flag.

    For every non-admin request, if that flag is absent we mask the user
    as AnonymousUser so all views, templates and context processors treat
    them as logged out — even if an admin session exists in the same browser.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_urls = [
            '/accounts/login/',
            '/accounts/register/',
            '/accounts/password_reset/',
            '/accounts/password_reset/done/',
            '/accounts/reset/',
            '/static/',
            '/media/',
            '/admin/login/',
            '/',
        ]

    def __call__(self, request):
        if not request.path.startswith('/admin/'):
            # On the normal site, only treat the user as authenticated if they
            # explicitly logged in here (not just via the admin panel).
            if request.user.is_authenticated and not request.session.get('_normal_site_auth'):
                request.user = AnonymousUser()

        # Redirect unauthenticated users away from protected pages.
        if not self._is_public_url(request.path):
            if request.path.startswith('/admin/'):
                if not request.user.is_authenticated:
                    return redirect('admin:login')
            else:
                if not request.user.is_authenticated:
                    return redirect('accounts:login')

        return self.get_response(request)
    
    def _is_public_url(self, path):
        """Check if URL is in the public URLs list or matches a pattern"""
        for public_url in self.public_urls:
            if path == public_url or path.startswith(public_url):
                return True
        
        # Allow password reset flows
        if '/accounts/reset/' in path:
            return True
        
        return False
