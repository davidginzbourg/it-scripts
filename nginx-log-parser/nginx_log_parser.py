import re
import sys
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool

import csv
import json
import iptools
import geoip2.database

LOG_PATH = 1
OUTPUT_PATH = 2
GEOLITE_CITY_DB_PATH = 3
CIDR_TO_ORG_DB_PATH = 4

TIME_OUTPUT_FORMAT='%Y-%m-%d %H:%M:%S'


def get_matching_cidrs(ip):
    ip_bits = bin(iptools.ipv4.ip2long(ip))[2:]
    ip_bits = ('0' * (32 - len(ip_bits))) + ip_bits
    cidrs = []
    for i in range(32):
        prefix = '0b' + ip_bits[:i + 1]
        suffix = '0' * (32 - (i + 1))
        ip = int(prefix + suffix, base=2)
        cidr = str(iptools.ipv4.long2ip(ip)) + '/' + str(i + 1)
        cidrs.append(cidr)
    return cidrs


def get_org(ip, cidr_to_org_dict):
    for cidr in get_matching_cidrs(ip):
        if cidr in cidr_to_org_dict:
            return cidr_to_org_dict[cidr]


def get_ip_dict(ip, geoip2_reader, cidr_to_org_dict):
    response = geoip2_reader.city(ip)
    return {
        'country_name': response.country.name,
        'city_name': response.city.name,
        'organization': get_org(ip, cidr_to_org_dict)}


def parse_line_wrapper(responses, init_output, geoip2_reader,
                       cidr_to_org_dict):
    def parse_line(line):
        path_matcher = re.search('"([^"]+)"', line)
        path_match = path_matcher.group(1) if path_matcher else 'Unknown'
        path_refined_matcher = re.search('\w+\s([^ ]+)\s+?', path_match)
        path = path_refined_matcher.group(
            1) if path_refined_matcher else 'Unknown'
        ip_matcher = re.search('(\d{1,3}([.]\d{1,3})+){1}', line)
        ip = ip_matcher.group(0) if ip_matcher else 'Unknown'
        time_matcher = re.search('\[(.+?)\]', line)
        t = time_matcher.group(1) if time_matcher else '01/Jan/1970:00:00:00'
        time_instance = datetime.strptime(
            re.sub('\s(\+|-)\d{4}', '', t),
            '%d/%b/%Y:%H:%M:%S')
        time_str = time_instance.strftime(TIME_OUTPUT_FORMAT)
        if ip not in responses:
            responses[ip] = get_ip_dict(
                ip,
                geoip2_reader,
                cidr_to_org_dict)
            for key, value in responses[ip].items():
                if responses[ip][key]:
                    responses[ip][key] = responses[ip][key].encode('utf8')
                else:
                    responses[ip][key] = 'None'
        tpl = (
            time_str,
            path,
            ip,
            responses[ip]['country_name'],
            responses[ip]['city_name'],
            responses[ip]['organization'])
        if tpl in init_output:
            init_output[tpl] += 1
        else:
            init_output[tpl] = 1

    return parse_line


def main():
    print('Loading log...')
    init_output = {}
    responses = {}
    content = []
    with open(sys.argv[LOG_PATH], 'r') as f:
        for line in f:
            content.append(line)

    with open(sys.argv[CIDR_TO_ORG_DB_PATH], 'r') as f:
        print('Loading CIDR to Org. DB...')
        cidr_to_org_dict = json.load(f)
    print('Loaded CIDR to Org. DB.')
    geoip2_reader = geoip2.database.Reader(sys.argv[GEOLITE_CITY_DB_PATH])

    print('Processing IPs...')
    # pool = ThreadPool()
    # pool.map(
    #     parse_line_wrapper(
    #         responses,
    #         init_output,
    #         geoip2_reader,
    #         cidr_to_org_dict),
    #     content)
    process_func = arse_line_wrapper(
            responses,
            init_output,
            geoip2_reader,
            cidr_to_org_dict)
    for line in content:
    	process_func(line)

    geoip2_reader.close()

    print('Processing output...')
    output = map(
        lambda x: (
            x[0][0],
            x[0][1],
            x[0][2],
            x[1],
            x[0][3],
            x[0][4],
            x[0][5]),
        sorted(
            init_output.items(),
            key=lambda y: tuple(
                [datetime.strptime(y[0][0], TIME_OUTPUT_FORMAT)] + list(
                    y[0][1:]))))
    print('Writing output...')
    with open(sys.argv[OUTPUT_PATH], 'w') as f:
        writer = csv.writer(f, dialect='excel')
        for item in output:
            if item:
                writer.writerow(item)


if __name__ == '__main__':
    main()
