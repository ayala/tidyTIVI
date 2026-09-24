"""Same-origin Dropbox setup UI; all account operations use authenticated plugin APIs."""
from pathlib import Path
import sys


def setup(request):
    from django.http import HttpResponse, HttpResponseNotAllowed
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    response = HttpResponse(Path(__file__).with_name('setup.html').read_text(), content_type='text/html; charset=utf-8')
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    return response


def install():
    api_urls = sys.modules.get('apps.plugins.api_urls')
    if api_urls is None:
        try:
            from importlib import import_module
            api_urls = import_module('apps.plugins.api_urls')
        except Exception:
            return
    if not hasattr(api_urls, 'urlpatterns'):
        return
    from django.urls import path, clear_url_caches
    name = 'tidytivi-setup'
    api_urls.urlpatterns[:] = [p for p in api_urls.urlpatterns if getattr(p, 'name', None) != name]
    api_urls.urlpatterns.insert(0, path('tidytivi/setup/', setup, name=name))
    clear_url_caches()
