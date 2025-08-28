from django.http import JsonResponse

def status(request):
    data = {
        'status': 'success',
        'code': '200'
    }
    return JsonResponse(data)
