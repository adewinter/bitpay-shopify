from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'home.views.index', name='root_path'),
    url(r'^design/$', 'home.views.design'),
    url(r'^welcome/$', 'home.views.welcome'),
    url(r'^alterorder/(\d+)/$', 'home.views.alterorder'),
    url(r'^hook/order/$', 'home.views.order_hook'),
    url(r'^hook/register/$', 'home.views.register_hooks'),
    url(r'^hook/bitpay/(\d+)/$', 'home.views.bitpay_hook'),
)
