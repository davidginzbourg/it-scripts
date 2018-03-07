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
DESTINATION = os.getenv('DESTINATION', None)
if not DESTINATION:
    raise Exception('No DESTINATION env var was set.')
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


def is_about_to_expire(warranty_info, expiration_threshold):
    """
    :param warranty_info: warranty info of the item (XML root).
    :param expiration_threshold: the expiration threshold for the item to be
     included in the email (days).
    :return: whether the item warranty is about to expire.
    """
    warranty_end_date = dateutil.parser.parse(
        warranty_info.find('end_date').text).replace(tzinfo=None)
    expiration_date = datetime.datetime.utcnow() - datetime.timedelta(
        days=expiration_threshold)
    return warranty_end_date - expiration_date <= datetime.timedelta(0)


def send_email(about_to_expire, no_warranty_date):
    """Sends an email with the warranty about to expire list and no warranty
    date list.

    :param about_to_expire: a list of hardware items  (XML roots) that warranty
     is about to expire [a tuple, [0] is the item name
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
        message_html += item[0]['name']
        message_html += '</td>'

        message_html += '<td>'
        message_html += str(
            dateutil.parser.parse(item[1].find('end_date').text).replace(
                tzinfo=None))
        message_html += '</td>'

        message_html += '</tr>'
    message_html += "</table>"

    message_html += "<h2>Hardware that that has no warranty end date</h2>"
    message_html += """<table>
    <tr>
    <th>Hardware name</th>
    </tr>"""
    for item in about_to_expire:
        message_html += '<tr>'

        message_html += '<td>'
        message_html += item.fine('name').text
        message_html += '</td>'

        message_html += '</tr>'
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
    if href_element is not None:
        response = get_xml_response(href_element.text, token)
        if response.find('end_date') is not None:
            return response
    return None


def main():
    """Main function to run, make sure that the environmental variable TOKEN is
     setup properly
     """
    token = os.getenv('TOKEN', None)
    if not token:
        raise Exception('No TOKEN env var was set.')
    expiration_threshold = os.getenv('EXPIRATION_THRESHOLD', None)
    if not expiration_threshold:
        raise Exception('No EXPIRATION_THRESHOLD (days) env var was set.')
    hardware_list = list_hardware(token)
    about_to_expire = []
    no_warranty_date = []
    for item_info in hardware_list:
        warranty_info = get_warranty_end_date(item_info, token)
        if warranty_info is None:
            no_warranty_date.append(item_info)
        elif is_about_to_expire(warranty_info, expiration_threshold):
            about_to_expire.append((item_info, warranty_info))
    send_email(about_to_expire, no_warranty_date)
    return True
