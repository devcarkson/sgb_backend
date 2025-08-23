from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import patch_vary_headers

class NoCacheForAuthenticatedAPIMiddleware(MiddlewareMixin):
    """
    Ensures that all authenticated API responses are never cached by browsers, proxies, or CDNs.
    Applies to any path under /api/ when the user is authenticated or an Authorization header is used (e.g., JWT).
    """
    API_PREFIX = '/api/'

    def process_response(self, request, response):
        try:
            path = request.path or ''
            is_api = path.startswith(self.API_PREFIX)
            has_auth_header = 'HTTP_AUTHORIZATION' in request.META or 'Authorization' in request.headers
            is_authenticated = getattr(request, 'user', None) and request.user.is_authenticated

            if is_api and (is_authenticated or has_auth_header):
                # Strong cache-busting headers
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private, max-age=0'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'

                # Ensure proxies vary on auth; prevents cross-user cache bleed
                patch_vary_headers(response, ('Authorization', 'Cookie'))
            return response
        except Exception:
            # Fail open: do not block responses if middleware errors
            return response
