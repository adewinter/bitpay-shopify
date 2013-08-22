from django.conf.urls.defaults import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    url(r'^$', 'home.views.index', name='root_path'),
    url(r'^design/$', 'home.views.design'),
    url(r'^welcome/$', 'home.views.welcome'),
    url(r'^alterorder/(\d+)/$', 'home.views.alterorder'),
    url(r'^hook/order/(.*)/$', 'home.views.order_hook'),
    url(r'^hook/register/$', 'home.views.register_hooks'),
    url(r'^hook/clear/$', 'home.views.clear_hooks'),
    url(r'^hook/bitpay/(\d+)/$', 'home.views.bitpay_hook'),
    url(r'^postsms/$', 'home.views.sms_received'),
)


urlpatterns += staticfiles_urlpatterns()