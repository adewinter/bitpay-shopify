from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
import shopify
from shopify_app.decorators import shop_login_required
import logging
import requests
import urlparse
import json

APP_URL = settings.get('APP_URL', '')

logger = logging.getLogger(__name__)

def welcome(request):
    return render_to_response('home/welcome.html', {
        'callback_url': "http://%s/login/finalize" % (request.get_host()),
    }, context_instance=RequestContext(request))


@shop_login_required
def index(request):
    products = shopify.Product.find(limit=3)
    orders = shopify.Order.find(limit=3, order="created_at DESC")
    return render_to_response('home/index.html', {
        'products': products,
        'orders': orders,
    }, context_instance=RequestContext(request))

@shop_login_required
def alterorder(request, order_id):
    order = shopify.Order.get(id=order_id)
    print 'Found the order! %s' % order
    return redirect('/')

@shop_login_required
def register_hooks(request):
    logger.debug('Registering Webhooks')
    webhook = shopify.Webhook()
    webhook.format = 'json'
    webhook.address = '%s/hook/order/' % APP_URL
    webhook.topic = 'orders/create'
    webhook.save()
    logger.debug('Made webhook: %s' % webhook)
    logger.debug('Dir webhook: %s' % dir(webhook))
    logger.debug('Webhook errors: %s' % webhook.errors)
    logger.debug('Webhook is valid %s' % webhook.is_valid)
    return redirect('/')

@csrf_exempt
def order_hook(request):
    logger.debug('===============================')
    logger.debug('Received an ORDER HOOK!')
    logger.debug('Request Object: %s' % request)
    logger.debug('Request body: %s' % request.body)
    logger.debug('Reqest Method: %s' % request.method)
    logger.debug('Attempting to make a bitpay invoice...')
    logger.debug('===================================')
    make_bitpay_invoice(request, json.loads(request.body))
    return HttpResponse('Hook Call received')

BITPAY_API_KEY = settings.get('BITPAY_API_KEY', '')

@shop_login_required
def make_bitpay_invoice(request, hook_data):
    currency = "USD"
    price = hook_data['total_price']
    order_id = hook_data['order_number']
    #TODO: Make a HTTPS url for bitpay notify webhook!
    # notification_url = "https://example.com/bitpay_invoice_change/%s/" % order_id
    notification_url = '%s/%s/%s/' % (APP_URL, 'hook/bitpay/', order_id)
    shop_url = request.session.get('shopify')['shop_url']
    url_parts = list(urlparse.urlparse(shop_url))
    url_parts[2] = 'account/orders/%s/' % hook_data['token']
    if url_parts[0] == '':
        url_parts[0] = 'http' #set scheme to http if it hasn't been set
    redirect_url = urlparse.urlunparse(url_parts) #use urlparse to make sure we join the path right
    customer = hook_data['customer']
    customer_name = '%s %s' % (customer['first_name'], customer['last_name'])
    shipping_address = hook_data['shipping_address']
    req_obj = {
        'currency': currency,
        'price': price,
        'posData': json.dumps(hook_data),
        'notificationUrl': notification_url,
        'redirectUrl': redirect_url,
        'orderID': order_id,
        'itemDesc': 'Order for %s %s on %s' % (customer_name, shop_url),
        'buyerName': customer_name,
        'buyerAddress1': shipping_address['address1'],
        'buyerAddress2': shipping_address['address2'],
        'buyerCity': shipping_address['city'],
        'buyerState': shipping_address['province'],
        'buyerZip': shipping_address['zip'],
        'buyerCountry': shipping_address['country'],
        'buyerEmail': hook_data['email'],
        'buyerPhone': shipping_address['phone'],
    }
    headers = {'content-type': 'application/json'}
    r = requests.post("https://bitpay.com/api/invoice", 
                        data=json.dumps(req_obj),
                        headers=headers,
                        auth=(BITPAY_API_KEY, ''))
    logger.debug('=======================')
    logger.debug('CREATED BITPAY INVOICE!')
    logger.debug('Request text: %s' % r.text)
    logger.debug('=======================')


@csrf_exempt
def bitpay_hook(request, order_id):
    logger.debug('===============================')
    logger.debug('Received a BITPAY HOOK!')
    logger.debug('Request Object: %s' % request)
    logger.debug('Request body: %s' % request.body)
    logger.debug('Reqest Method: %s' % request.method)
    logger.debug('ORDER_ID: %s' % order_id)
    logger.debug('===================================')
    return HttpResponse('Hook Call received')

def design(request):
    return render_to_response('home/design.html', {},
                              context_instance=RequestContext(request))
