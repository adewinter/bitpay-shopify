from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseServerError
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import shopify
from shopify_app.decorators import shop_login_required
import logging
import requests
import urlparse
import json
import urllib
import aamnotifs as notifs
logging.getLogger('pika').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

notifier = None


def connectNotifier():
    global notifier
    logger.debug('=========== NOTIFIER ========== %s' % notifier)
    logger.debug('Attempting to establish a connection to AMQP Server: amqp://adewinter:qsczse12@base102.net:5672/%2f')
    notifier = notifs.Notifs("amqp://adewinter:qsczse12@base102.net:5672/%2f")

APP_URL = getattr(settings, 'APP_URL', '')


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
def clear_hooks(request):
    shop_url = request.session.get('shopify')['shop_url']
    shop_url = urllib.quote(shop_url)
    hooks = shopify.Webhook.find()
    logger.debug('Found these hooks: %s' % hooks)
    for hook in hooks:
        logger.debug('Destroying Hook: %s' % hook)
        hook.destroy()
    return redirect('/')

@shop_login_required
def register_hooks(request):
    shop_url = request.session.get('shopify')['shop_url']
    shop_url = urllib.quote(shop_url)
    logger.debug('Registering Webhooks for Shop: %s' % shop_url)
    webhook = shopify.Webhook()
    webhook.format = 'json'
    webhook.address = '%s/hook/order/%s/' % (APP_URL, shop_url)
    webhook.topic = 'orders/create'
    webhook.save()
    logger.debug('Made webhook: %s:: format: %s, address: %s, topic: %s, errors %s' % (webhook, webhook.format, webhook.address, webhook.topic, webhook.errors.full_messages()))
    logger.debug('Webhook is valid %s' % webhook.is_valid())
    return redirect('/')

@csrf_exempt
def order_hook(request, shop_url):
    logger.debug('===============================')
    logger.debug('Received an ORDER HOOK!')
    logger.debug('Raw shop url is: %s, unquoted: %s' % (shop_url, urllib.unquote(shop_url)))
    logger.debug('Request body: %s' % request.body)
    logger.debug('Reqest Method: %s' % request.method)
    logger.debug('Attempting to make a bitpay invoice...')
    logger.debug('===================================')
    make_bitpay_invoice(urllib.unquote(shop_url), json.loads(request.body))
    return HttpResponse('Hook Call received')

BITPAY_API_KEY = getattr(settings, 'BITPAY_API_KEY', '')

# @shop_login_required
def make_bitpay_invoice(shop_url, hook_data):
    logger.debug('=======================')
    logger.debug('hook_data: %s' % hook_data)
    currency = "USD"
    price = hook_data['total_price']
    order_id = hook_data['order_number']
    #TODO: Make a HTTPS url for bitpay notify webhook!
    # notification_url = "https://example.com/bitpay_invoice_change/%s/" % order_id
    notification_url = '%s/%s/%s/' % (APP_URL, 'hook/bitpay', order_id)
    logger.debug('notification url: %s' % notification_url)
    url_parts = ['','','','','','']
    url_parts[2] = 'account/orders/%s/' % hook_data['token']
    url_parts[1] = shop_url
    url_parts[0] = 'https' 
    redirect_url = urlparse.urlunparse(url_parts) #use urlparse to make sure we join the path right
    logger.debug('redirect_url: %s' % redirect_url)
    customer = hook_data['customer']
    customer_name = '%s %s' % (customer['first_name'], customer['last_name'])
    shipping_address = hook_data['shipping_address']
    req_obj = {
        'currency': currency,
        'price': price,
        # 'posData': json.dumps(hook_data),
        'notificationUrl': notification_url,
        'redirectUrl': redirect_url,
        'orderID': order_id,
        'itemDesc': 'Order for %s on %s' % (customer_name, shop_url),
        'buyerName': customer_name,
        'buyerAddress1': shipping_address['address1'],
        'buyerAddress2': shipping_address['address2'],
        'buyerCity': shipping_address['city'],
        'buyerState': shipping_address['province'],
        'buyerZip': shipping_address['zip'],
        'buyerCountry': shipping_address['country'],
        'buyerEmail': hook_data['email'],
        'buyerPhone': shipping_address['phone'],
        'transactionSpeed': 'high', #NB!!
    }
    logger.debug('Request Object: %s' % req_obj)
    headers = {'content-type': 'application/json'}
    r = requests.post("https://bitpay.com/api/invoice", 
                        data=json.dumps(req_obj),
                        headers=headers,
                        auth=(BITPAY_API_KEY, ''))
    bitpay_response = r.text
    logger.debug('CREATED BITPAY INVOICE!')
    logger.info('Bitpay Invoice API Response: %s' % bitpay_response)
    logger.debug('=======================')
    bitpay_response = json.loads(bitpay_response)
    logger.debug('Attempting to send invoice email')
    send_bitpay_invoice_email(hook_data['email'], customer_name, bitpay_response['url'], shop_url)

def send_bitpay_invoice_email(to_addr, name, invoice_url, shop_url):
    subject = '%s Order: Bitcoin Payment Instructions' % shop_url 
    from_email, to = 'orders@basetentwo.com', to_addr
    text_content = """
        Thank your for your order %s!
        Please click on the following URL (or paste it into your browser address bar):
        %s

        Once you have sent your bitcoin payment, you will be sent a confirmation email to let you know that everything is in order.

        Please let us know if you have any questions or concerns by sending email to orders@basetentwo.com! We would be more than happy to assist!

        Thanks again,
        Base Ten Two Inc.
    """ % (name, invoice_url)
    html_content = """
        <h1>Thank your for your order %s!</h1><br />
        Please click on the following URL (or paste it into your browser address bar):<br />
        <a href="%s">%s</a><br /><br />

        Once you have sent your bitcoin payment, you will be sent a confirmation email to let you know that everything is in order. <br />

        <p>
        Please let us know if you have any questions or concerns by sending email to orders@basetentwo.com! We would be more than happy to assist!

        </p>
        <br />
        Thanks again,<br />
        Base Ten Two Inc.
    """ % (name, invoice_url, invoice_url)
    logger.info('Sending email To:%s, Customer_Name:%s, Shop_URL:%s, Invoice_URL:%s' % (to_addr, name, shop_url, invoice_url))
    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    logger.debug('Email Sent!')
@csrf_exempt
def bitpay_hook(request, order_id):
    logger.debug('===============================')
    logger.debug('BITPAY_HOOK Received a BITPAY HOOK!')
    logger.info('BITPAY_HOOK Request Object: %s' % request)
    logger.debug('BITPAY_HOOK Request body: %s' % request.body)
    logger.debug('BITPAY_HOOK Reqest Method: %s' % request.method)
    logger.debug('BITPAY_HOOK ORDER_ID: %s' % order_id)
    logger.debug('===================================')
    return HttpResponse('Hook Call received')

def design(request):
    return render_to_response('home/design.html', {},
                              context_instance=RequestContext(request))

@csrf_exempt
def sms_received(request):
    """
    An SMS was received on the android device.  A notification get_host
    sent to the AMQP Server
    """
    if request.method == "POST" and request.body:
        json_data = json.loads(request.body)
        message = json_data.get('message',None)
        number = json_data.get('number', None)
    else:
        message = 'Error getting message (or fake amqp req)'
        number = 'ERROR'

    logger.info('POST SMS RECEIVED: %s :: %s' % (request.body, request.method))
    logger.info('Sending to AMQP: number, message:: %s, %s' % (number, message))
    if not notifier or not notifier.connection.is_open:
        logger.debug('Notifier appears to be dead. Attempting to re-open connection to AMQP')
        logger.debug('Here is the notifier: %s' % notifier)
        connectNotifier()
    logger.debug('Attempting to send message, number: %s, %s' % (message, number))
    notifier.send("sms_notification", number, message)
    logger.debug('Message sent!')   
    return HttpResponse('SUCCESS')



@csrf_exempt
def sms_send(request):
    """
    A non-android client would like to send an SMS message
    via an android device.  Takes an HTTP POST and uses PARSE push notification
    framework to communicate with the android device
    """
    if request.method == "POST" and request.body:
        json_data = json.loads(request.body)
        message = json_data.get('message',None)
        number = json_data.get('number', None)
    else:
        message = 'Error getting message'
        number = 'ERROR'

    logger.info('POST Hook to SEND SMS: %s :: %s' % (request.body, request.method))
    logger.info('Attempting to do a POST to Parse PUSH Api')

    headers = {
        "X-Parse-Application-Id": getattr(settings, 'PARSE_APP_ID', ''),
        "X-Parse-REST-API-Key": getattr(settings, 'PARSE_REST_API_KEY', ''),
        "Content-Type": "application/json"
    }
    url = getattr(settings, 'PARSE_PUSH_URL')
    data = {
        "action": "com.basetentwo.smstohttp.SEND_SMS",
        "alert": "Sending an SMS",
        "message": message,
        "number": number,
        "title": "RMac Activity"
    }

    payload = {
        'data': data,
        'channels': ['send_sms']
    }

    r = requests.post(url, data=json.dumps(payload), headers=headers)


    logger.info('Parse Response code: %s, Response Body: %s' % (r.status_code, r.text))
    if r.status_code==200:
        return HttpResponse('SUCCESS')
    else:
        return HttpResponseServerError('There was an error. \nParse Response code: %s, Response Body: %s' % (r.status_code, r.text))
