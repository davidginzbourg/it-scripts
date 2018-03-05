import os
import urllib2
import xml.etree.ElementTree as ET
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ses_client = boto3.client('ses', region_name='eu-west-1')


# e = xml.etree.ElementTree.parse('thefile.xml').getroot()
# contents = urllib2.urlopen("http://example.com/foo/bar").read()


def get_xml_response(url_suffix, token):
    """Sends a GET request to samanage with the given url suffix.

    :param url_suffix: url suffix.
    :param token: Samange API token
    :return: the parsed XML of the response
    """
    url = 'https://api.samanage.com/{0}'.format(url_suffix)
    logger.debug('Request URL is {0}'.format(url))
    request = urllib2.Request(url)
    request.add_header('X-Samanage-Authorization', 'Bearer {0}'.format(token))
    request.add_header('Accept', 'application/vnd.samanage.v2.1+xml')
    logger.debug('Sending the request...')
    response = request.read()
    logger.debug('Received a response.')
    return ET.fromstring(response).getroot()


def list_hardware(token):
    """Lists all hardware items.

    :param token: Samanage API token.
    :return: the parsed XML of the response.
    """
    logger.info('Listing hardware...')
    return get_xml_response('hardwares.xml', token)


def has_warranty_date(hardware_item):
    """
    :param hardware_item: item to check.
    :return: whether the item has a warranty date.
    """
    pass


def is_about_to_expire(hardware_item, expiration_threshold):
    """
    :param hardware_item: item to check.
    :param expiration_threshold: the expiration threshold for the item to be
     included in the email.
    :return: whether the item warranty is about to expire.
    """
    pass


def send_email(about_to_expire, no_warranty_date):
    """Sends an email with the warranty about to expire list and no warranty
    date list.

    :param about_to_expire: a list of hardware items that warranty is about to
      expire.
    :param no_warranty_date:
    :return:
    """
    pass


def main():
    """Main function to run, make sure that the environmental variable TOKEN is
     setup properly
     """
    token = os.getenv('TOKEN', None)
    if not token:
        raise Exception('No TOKEN env var was found.')
    expiration_threshold = os.getenv('EXPIRATION_THRESHOLD', None)
    if not expiration_threshold:
        raise Exception('No EXPIRATION_THRESHOLD env var was found.')
    hardware_list = list_hardware(token)
    about_to_expire = []
    no_warranty_date = []
    for item in hardware_list:
        if not has_warranty_date(item):
            no_warranty_date.append(item)
        elif is_about_to_expire(item, expiration_threshold):
            about_to_expire.append(item)
    send_email(about_to_expire, no_warranty_date)
    return True
