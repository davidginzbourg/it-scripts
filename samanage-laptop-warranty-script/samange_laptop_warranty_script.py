import os
import urllib2
import xml.etree.ElementTree as ET
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ses_client = boto3.client('ses', region_name='eu-west-1')

BASE_URL = 'https://api.samanage.com/'


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
    response = request.read()
    logger.debug('Received a response.')
    return ET.fromstring(response).getroot()


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
     included in the email.
    :return: whether the item warranty is about to expire.
    """
    pass


def send_email(about_to_expire, no_warranty_date):
    """Sends an email with the warranty about to expire list and no warranty
    date list.

    :param about_to_expire: a list of hardware items  (XML roots) that warranty
     is about to expire [a tuple, [0] is the item name
    :param no_warranty_date: a list of hardware items  (XML roots) that don't
     have a warranty date enetered for them.
    :return:
    """
    pass


def get_warranty_end_date(item_info, token):
    """
    :param item_info: item to get info for (XML root).
    :param token: token to get info with.
    :return: the hardware item info, or None if it is corrupt.
    """
    if 'name' in item_info:
        logger.info(
            'Getting item warranties info for {0}'.format(item_info['name']))
    elif 'href' in item_info:
        logger.info(
            'Getting item warranties info for {0}'.format(item_info['href']))
    else:
        return None
    if 'href' in item_info:
        return get_xml_response(item_info['href'], token)


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
    for item_info in hardware_list:
        warranty_date = get_warranty_end_date(item_info, token)
        if not warranty_date:
            no_warranty_date.append(item_info)
        elif is_about_to_expire(warranty_date, expiration_threshold):
            about_to_expire.append((item_info, warranty_date))
    send_email(about_to_expire, no_warranty_date)
    return True
