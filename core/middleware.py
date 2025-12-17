
import re

class MobileDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.mobile_pattern = re.compile(r'Mobile|iP(hone|od|ad)|Android|BlackBerry|IEMobile|Kindle|NetFront|Silk-Accelerated|(hpw|web)OS|Fennec|Minimo|Opera M(obi|ini)|Blazer|Dolfin|Dolphin|Skyfire|Zune', re.I)

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        request.is_mobile = bool(self.mobile_pattern.search(user_agent))
        response = self.get_response(request)
        return response
