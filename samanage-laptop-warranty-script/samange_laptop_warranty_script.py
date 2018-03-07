import os
import urllib2
import logging
import datetime
import dateutil.parser
import xml.etree.ElementTree as ET

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ses_client = boto3.client('ses', region_name='eu-west-1')

BASE_URL = 'https://api.samanage.com/'
SOURCE = os.getenv('SOURCE', None)
if not SOURCE:
    raise Exception('No SOURCE env var was set.')
TO_ADDRESSES = [os.getenv('TO_ADDRESSES', None)]
if not TO_ADDRESSES:
    raise Exception('No TO_ADDRESSES env var was set.')
DESTINATION = {'ToAddresses': TO_ADDRESSES}
SUBJECT = os.getenv('SUBJECT', None)
if not SUBJECT:
    raise Exception('No SUBJECT env var was set.')


# e = xml.etree.ElementTree.parse('thefile.xml').getroot()
# contents = urllib2.urlopen("http://example.com/foo/bar").read()


def get_xml_response(url, token):
    """Sends a GET request to samanage with the given url suffix.

    :param url: url to send requests to.
    :param token: Samanage API token
    :return: the parsed XML of the response
    """
    logger.debug('Request URL is {0}'.format(url))
    request = urllib2.Request(url)
    request.add_header('X-Samanage-Authorization', 'Bearer {0}'.format(token))
    request.add_header('Accept', 'application/vnd.samanage.v2.1+xml')
    logger.debug('Sending the request...')
    response = urllib2.urlopen(request).read()
    logger.debug('Received a response.')
    return ET.fromstring(response)


def list_hardware(token):
    """Lists all hardware items.

    :param token: Samanage API token.
    :return: the parsed XML of the response.
    """
    logger.info('Listing hardware...')
    return get_xml_response('{0}hardwares.xml'.format(BASE_URL), token)


def is_about_to_expire(warranty_end_date, expiration_threshold):
    """
    :param warranty_end_date: warranty info of the item (XML root).
    :param expiration_threshold: the expiration threshold for the item to be
     included in the email (days).
    :return: whether the item warranty is about to expire.
    """
    expiration_date = datetime.datetime.utcnow() - datetime.timedelta(
        days=expiration_threshold)
    return warranty_end_date - expiration_date <= datetime.timedelta(0)


def send_email(about_to_expire, no_warranty_date):
    """Sends an email with the warranty about to expire list and no warranty
    date list.

    :param about_to_expire: a list of hardware items  (XML roots) that warranty
     is about to expire where each item is a tuple, [0] is the item name and
     [1] is the end date.
    :param no_warranty_date: a list of hardware items  (XML roots) that don't
     have a warranty date enetered for them.
    :return:
    """
    message_html = """
    <html>
    <head>
    <style>
    table {
        font-family: arial, sans-serif;
        border-collapse: collapse;
        width: 100%;
    }

    td, th {
        border: 1px solid #dddddd;
        text-align: left;
        padding: 8px;
    }

    tr:nth-child(even) {
        background-color: #dddddd;
    }
    </style>
    </head>
    <body>

    """
    message_html += "<h2>Hardware that is about to expire</h2>"
    message_html += """<table>
    <tr>
    <th>Hardware name</th>
    <th>Warranty end date</th>
    </tr>"""
    for item in about_to_expire:
        message_html += '<tr>'

        message_html += '<td>'
        message_html += item[0].find('name').text
        message_html += '</td>'

        message_html += '<td>'
        message_html += str(item[1])
        message_html += '</td>'

        message_html += '</tr>'
    message_html += "</table>"

    if len(no_warranty_date) > 0:
        message_html += "<h2>Hardware that that has no warranty end date</h2>"
        message_html += """<table>
        <tr>
        <th>Hardware name</th>
        </tr>"""
        for item in no_warranty_date:
            message_html += '<tr>'

            message_html += '<td>'
            message_html += item.find('name').text
            message_html += '</td>'
            
            message_html += '</tr>\n'
        message_html += "</table>"

    message_html += "</body></html>"
    message_id = ses_client.send_email(Source=SOURCE, Destination=DESTINATION,
                                       Message={
                                           'Subject': {'Data': SUBJECT},
                                           'Body': {
                                               'Html': {'Data': message_html}}
                                       })['MessageId']
    logger.info('Sent a message, ID: ' + message_id)


def get_warranty_end_date(item_info, token):
    """
    :param item_info: item to get info for (XML root).
    :param token: token to get info with.
    :return: the hardware item info, or None if it is corrupt.
    """
    name_element = item_info.find('name')
    href_element = item_info.find('href')
    if name_element is not None:
        logger.info(
            'Getting item warranties info for {0}'.format(
                name_element.text.encode('utf-8')))
    else:
        return None
    if href_element is not None and href_element.text is not None:
        hardware_id = href_element.text.split('/')[-1].split('.')[0]
        url = '{0}/hardwares/{1}/warranties.xml'.format(BASE_URL, hardware_id)
        response = get_xml_response(url, token)
        latest_end_date = None
        for warranty in response:
            if warranty.find('end_date') is not None \
                    and warranty.find('end_date').text is not None:
                curr_end_date = dateutil.parser.parse(
                    warranty.find('end_date').text).replace(tzinfo=None)
                if latest_end_date is None:
                    latest_end_date = curr_end_date
                else:
                    if latest_end_date < curr_end_date:
                        latest_end_date = curr_end_date
        return latest_end_date
    return None


def main(event, context):
    """Main function to run, make sure that the environmental variable TOKEN is
     setup properly
     """
    token = os.getenv('TOKEN', None)
    if not token:
        raise Exception('No TOKEN env var was set.')
    expiration_threshold = int(os.getenv('EXPIRATION_THRESHOLD', None))
    if not expiration_threshold:
        raise Exception('No EXPIRATION_THRESHOLD (days) env var was set.')
    hardware_list = list_hardware(token)
    about_to_expire = []
    no_warranty_date = []
    for item_info in hardware_list.findall('hardware'):
        warranty_end_date = get_warranty_end_date(item_info, token)
        if warranty_end_date is None:
            no_warranty_date.append(item_info)
        elif is_about_to_expire(warranty_end_date, expiration_threshold):
            about_to_expire.append((item_info, warranty_end_date))
    send_email(about_to_expire, no_warranty_date)
    return True
