#!/usr/bin/python
import os
from subprocess import check_output

import yaml
import json
import smtplib


def send_mail(subject, msg):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(source_email_address, source_email_address_password)
    full_msg = 'Subject: {0}\n\n{1}'.format(subject, msg)
    server.sendmail(source_email_address, destination_email_address, full_msg)
    server.quit()


def get_project_list():
    output = check_output(
        ["openstack", "project", "list", "--long", "--format=json"])
    projects = json.loads(output)
    return filter(lambda project: 'ID' in project and 'Name' in project,
                  projects)


def list_servers(project_name):
    os.environ['OS_PROJECT_NAME'] = project_name
    output = check_output(
        ["openstack", "server", "list", "--long", "--format=json"])
    servers = json.loads(output)
    return filter(lambda server: 'Status' in server
                                 and server['Status'] == 'ACTIVE'
                                 and 'Name' in server,
                  servers)


def set_environ_vars(config_file):
    with open(config_file) as config:
        conf_vars = yaml.load(config.read())
    for key, value in conf_vars['ENV_VARS'].items():
        os.environ[key] = value
    flavor_count = conf_vars['flavors']
    destination_email_address = conf_vars['destination_email_address']
    source_email_address = conf_vars['source_email_address']
    source_email_address_password = conf_vars['source_email_address_password']
    global flavor_count
    global metric_suffix
    global destination_email_address
    global source_email_address
    global source_email_address_password


def get_data(config_file):
    set_environ_vars(config_file)
    projects_names = get_project_list()
    tenants_instances = {}
    total_instances = 0
    for project in projects_names:
        instances_count = 0
        instances = list_servers(project['Name'])
        total_instances += 0
        tenants_instances[project['Name']] = 0

        for instance in instances:
            if 'ACTIVE' == instance['Status']:
                total_instances += 1
                tenants_instances[project['Name']] += 1
                instances_count += 1
                flavor = instance['Flavor Name']
                if flavor in flavor_count:
                    flavor_count[flavor] += 1
                else:
                    flavor_count[flavor] = 1
    tenants_instances['Total'] = total_instances
    return flavor_count, tenants_instances


def main():
    filename = os.path.basename(__file__).split('.')[0]
    config_file = '{0}.yaml'.format(filename)
    flavor_count, tenants_instances = get_data(config_file)
    msg = ''
    for key, value in sorted(tenants_instances.items(), key=lambda e: e[1],
                             reverse=True):
        msg += str(key) + '\t' + str(value) + '\n'
    msg += '\n\n'
    for key, value in sorted(flavor_count.items(), key=lambda e: e[1],
                             reverse=True):
        msg += str(key) + '\t' + str(value) + '\n'

    send_mail(subject="Memset Daily Report", msg=msg)


if __name__ == '__main__':
    main()
