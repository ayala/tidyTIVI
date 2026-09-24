"""A narrow callback route registered by Dispatcharr's plugin startup discovery."""
from html import escape


def callback(request):
    from django.http import HttpResponse
    from apps.plugins.models import PluginConfig
    from .cloud_auth import finish
    message='Sign-in could not be completed. Start Connect cloud storage again.';status=400
    if request.method!='GET':status=405
    elif not PluginConfig.objects.filter(key='tidytivi',enabled=True).exists():
        message='Enable tidyTIVI before connecting cloud storage.';status=403
    else:
        try:
            name=finish(request.GET.get('state',''),request.GET.get('code',''),request.GET.get('error',''))
            message=name+' is connected. You can close this tab and the temporary localhost connection. Return to tidyTIVI and enable automatic cloud upload.';status=200
        except ValueError as exc:message=str(exc)
        except Exception:pass  # Never expose codes, account credentials or provider responses.
    body='<!doctype html><meta charset="utf-8"><title>tidyTIVI cloud connection</title><h1>tidyTIVI</h1><p>'+escape(message)+'</p>'
    r=HttpResponse(body,status=status,content_type='text/html; charset=utf-8')
    r['Cache-Control']='no-store';r['Referrer-Policy']='no-referrer'
    r['Content-Security-Policy']="default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return r


def install():
    from django.urls import path,clear_url_caches
    from apps.plugins import api_urls
    name='tidytivi-cloud-callback'
    # Replace on plugin reload rather than accumulating stale module references.
    api_urls.urlpatterns[:]=[p for p in api_urls.urlpatterns if getattr(p,'name',None)!=name]
    api_urls.urlpatterns.insert(0,path('tidytivi/cloud/callback/',callback,name=name))
    clear_url_caches()
