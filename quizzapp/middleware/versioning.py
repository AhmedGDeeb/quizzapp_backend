from django.utils.deprecation import MiddlewareMixin

class VersioningMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        print(request.headers)

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.
        
        # Add supported version
        response['X-Api-Version'] = '0.0'
        
        return response
