#!/usr/bin/python
import os
import smtplib

import yaml
from keystoneauth1 import session

from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient

gmail_source_mail = '<Gmail username)'
gmail_app_password = '<Gmail app-password>'
path = os.path.dirname(os.path.realpath(__file__))


def send_mail(subject, email_address_destination, filename):
    file_path = str(os.path.join(path, filename))
    file_cont = open(file_path).read()
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(gmail_source_mail, gmail_app_password)
    full_msg = 'Subject: {0}\n\n{1}'.format(subject, file_cont)
    server.sendmail(gmail_source_mail, email_address_destination, full_msg)
    server.quit()


def get_password_session(usernamme, password, url, project):
    auth = v3.Password(auth_url=url,
                       username=usernamme,
                       password=password,
                       user_domain_name='Default',
                       project_name=project,
                       project_domain_name='Default')
    return session.Session(auth=auth)


def get_project_names(usernamme, password, url, project_name):
    password_session = get_password_session(usernamme=usernamme,
                                            password=password,
                                            url=url,
                                            project=project_name)
    keystone = keystoneclient.Client(session=password_session)

    projects_name = []
    projects_list = keystone.projects.list(user=password_session.get_user_id())

    for project in projects_list:
        projects_name.append(project.name.encode('ascii'))
    return projects_name


def set_global_var(config_file, dict_name):
    with open(config_file) as config:
        conf_vars = yaml.load(config.read())
    global OS_AUTH_URL
    global OS_USERNAME
    global OS_PASSWORD
    global project_name
    global flavor_count
    global email_address_destination
    flavor_count = conf_vars[dict_name]['flavors']
    project_name = conf_vars[dict_name]['project']
    OS_AUTH_URL = conf_vars[dict_name]['OS_AUTH_URL']
    OS_USERNAME = conf_vars[dict_name]['OS_USERNAME']
    OS_PASSWORD = conf_vars[dict_name]['OS_PASSWORD']
    email_address_destination = conf_vars['email_address_destination']


def get_data(config_file, account_name):
    set_global_var(config_file, dict_name=account_name)
    projects_names = get_project_names(OS_USERNAME, OS_PASSWORD,
                                       OS_AUTH_URL, project_name)
    tenants_instances = {}
    total_instances = 0
    for project in projects_names:
        instances_count = 0
        password_session = get_password_session(OS_USERNAME, OS_PASSWORD,
                                                OS_AUTH_URL, project)
        nova = novaclient.Client(version='2.0', session=password_session)
        instances_list = nova.servers.list()
        total_instances += 0
        tenants_instances[project] = 0

        if len(instances_list) > 0:
            for instance in instances_list:
                if 'ACTIVE' in instance.status:
                    total_instances += 1
                    tenants_instances[project] += 1
                    instances_count += 1
                    flavor = \
                        nova.flavors.get(instance.flavor['id']).name.encode('ascii')
                    try:
                        flavor_count[flavor] += 1
                    except KeyError:
                        flavor_count[flavor] = 1
    tenants_instances['Total'] = total_instances
    return flavor_count, tenants_instances


def main(account_name):
    config_file = os.path.join(path, 'os_and_mail.yaml')
    flavor, tenants = get_data(config_file, account_name)
    filename = '{0}.txt'.format(account_name)
    with open(filename, 'w') as outfile:
        for key, value in sorted(tenants.items(), key=lambda e: e[1], reverse=True):
            outfile.write(str(key) + '\t' + str(value) + '\n')
        outfile.write('\n\n')
        for key, value in sorted(flavor.items(), key=lambda e: e[1], reverse=True):
            outfile.write(str(key) + '\t' + str(value) + '\n')

    if account_name == 'rackspace':
        subject = "Cloudify RackSpace dailly report"
    else:
        subject = "Cloudify Datacentred-{0} dailly report".format(account_name)
    send_mail(subject, email_address_destination, filename)


main('ps')
main('rnd')
main('rackspace')