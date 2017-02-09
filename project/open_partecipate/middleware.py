from django.conf import settings

from .models import EntePartecipatoCronologia

class DefaultYearMiddleware(object):
    """
    Defines the default_year, accessible in the view
    """
    def process_request(self, request):

        referer = request.META.get('HTTP_REFERER', '')
        is_dev_env = False and any(key in referer for key in ['amazonaws.com', 'localhost'])
        if is_dev_env:
            default_year = EntePartecipatoCronologia.objects.anni_riferimento().last()
        else:
            default_year = settings.DEFAULT_YEAR

        request.default_year = default_year
        request.is_dev_env = is_dev_env

