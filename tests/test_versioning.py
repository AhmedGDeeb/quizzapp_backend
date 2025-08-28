from django.test import TestCase
from quizzapp.middleware.versioning import *

from django.http import JsonResponse
from django.urls import path
from django.test import TestCase, RequestFactory

def foo(request):
    return JsonResponse({})

urlpatterns = [
    path('test/middlware/versioning', foo),
]

class VersioningMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = VersioningMiddleware(foo)
    
    def test_x_api_version_header_present(self):
        """Test that X-Api-Version header is added to response"""
        # Create a request
        request = self.factory.get('test/middlware/versioning')
        
        # Process the request through middleware
        response = self.middleware(request)
        
        # Check that the header exists
        self.assertIn('X-Api-Version', response)

        # self.assertEqual(response['X-Api-Version'], '0.0')
