import csv
import json

import netaddr
from sys import argv

ASN_INPUT_PATH_ARG = 1
CIDR_TO_ORG_DB_PATH = 2


def calc_cidr(ip_start, ip_end):
    return netaddr.iprange_to_cidrs(ip_start, ip_end)


def main():
    print('Calculating CIDRs...')
    cidr_to_org = {}
    with open(argv[ASN_INPUT_PATH_ARG], 'r') as f:
        reader = csv.reader(f, delimiter='\t')
        for line in reader:
            if 'Not routed' not in line[4]:
                for ip_network in calc_cidr(line[0], line[1]):
                    cidr_to_org[str(ip_network)] = line[4]

    print('Dumping json file...')
    with open(argv[CIDR_TO_ORG_DB_PATH], 'w') as f:
        json.dump(cidr_to_org, f)


if __name__ == '__main__':
    main()
