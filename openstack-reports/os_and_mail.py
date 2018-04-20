#!/usr/bin/python
import os
import smtplib
import datetime
import dateutil.parser

import yaml
from keystoneauth1 import session

from keystoneauth1.identity import v3
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient

TOTAL_STR = 'Total'
DOWN_THRESHOLD = 10
ACCOUNT_NAMES = ['rackspace']
path = os.path.dirname(os.path.realpath(__file__))

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_mail(msg):
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(source_email_address, source_email_address_password)
    server.sendmail(source_email_address, destination_email_address, msg)
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
    global destination_email_address
    global source_email_address
    source_email_address = conf_vars['source_email_address']
    global source_email_address_password
    source_email_address_password = conf_vars['source_email_address_password']
    flavor_count = conf_vars[dict_name]['flavors']
    project_name = conf_vars[dict_name]['project']
    OS_AUTH_URL = conf_vars[dict_name]['OS_AUTH_URL']
    OS_USERNAME = conf_vars[dict_name]['OS_USERNAME']
    OS_PASSWORD = conf_vars[dict_name]['OS_PASSWORD']
    destination_email_address = conf_vars['destination_email_address']


def is_down_above_threshold(instance):
    updated_at = dateutil.parser.parse(instance.updated).replace(tzinfo=None)
    expiration_threshold = datetime.datetime.utcnow() - \
                           datetime.timedelta(days=DOWN_THRESHOLD)
    return updated_at - expiration_threshold <= datetime.timedelta(0)


def get_data(config_file, account_name):
    set_global_var(config_file, dict_name=account_name)
    projects_names = get_project_names(OS_USERNAME, OS_PASSWORD,
                                       OS_AUTH_URL, project_name)
    tenants_instances = {}
    total_instances = 0
    down_instances = {}
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
                    flavor = nova.flavors.get(
                        instance.flavor['id']).name.encode('ascii')
                    try:
                        flavor_count[flavor] += 1
                    except KeyError:
                        flavor_count[flavor] = 1
                if is_down_above_threshold(instance):
                    if project not in down_instances:
                        down_instances[project] = list()
                    down_instances[project].append(instance.name)


    tenants_instances[TOTAL_STR] = total_instances
    return flavor_count, tenants_instances, down_instances


def build_msg(flavor_count, tenants_instances, down_instances):
    email = MIMEMultipart('alternative')
    email['From'] = source_email_address
    email['To'] = destination_email_address
    email['Subject'] = "Rackspace Daily Report"
    html_msg = """
    <html>
    <head>
    <style>
    .cust_table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
    }
    thead, td {
        padding: 5px;
        text-align: center;
    }
    </style>
    </head>
    <body>
    <table border="0" align="left" >
    <tr>
    <td style="vertical-align: top; text-align: left;">
    <table class="cust_table">
    <thead>
    <tr>
    <th>Tenant Name</th>
    <th>Number of instances</th>
    </tr>
    """
    html_msg += '<tr><th>Total</th><th>' + str(tenants_instances[
                                                   TOTAL_STR]) + '</th></tr></thead>'

    cells = ('<td>{}</td>' * 2)
    for key, value in filter(lambda (key, value): key != TOTAL_STR,
                             sorted(tenants_instances.items(),
                                    key=lambda e: e[1], reverse=True)):
        html_msg += '<tr>'
        html_msg += cells.format(str(key), value)
        html_msg += '</tr>'
    html_msg += '</table><br><br>'

    html_msg += """
    </td>
    <td style="vertical-align: top; text-align: left;">
    <table class="cust_table">
    <th>Flavor Name</th>
    <th>Number of instances with this flavor</th>
    """
    cells = ('<td>{}</td>' * 2)
    for key, value in sorted(flavor_count.items(), key=lambda e: e[1],
                             reverse=True):
        html_msg += '<tr>'
        html_msg += cells.format(str(key), value)
        html_msg += '</tr>'
    html_msg += '</table></td>'

    html_msg += """
    <td style="vertical-align: top; text-align: left;"  >
    <table>
    <thead>
    <tr>
    <th></th>
    <th>Instances that are shutdown for more than {} days<th>
    </tr>
    <tr>
    <th>Project name</th>
    <th>Instances names</th>
    </tr>
    </thead>
    """.format(DOWN_THRESHOLD)

    cells = ('<td>{}</td>' * 2)
    instance_name_list_format = ', {}'
    for key, value in sorted(down_instances.items(), key=lambda e: e[1],
                             reverse=True):
        html_msg += '<tr>'
        sorted_valued = sorted(value)
        instance_name_list = sorted_valued[0]
        for name in sorted_valued[1:]:
            instance_name_list \
                += instance_name_list_format.format(name.encode('utf-8'))
        html_msg += cells.format(str(key), instance_name_list)
        html_msg += '</tr>'

    html_msg += '</table></td><tr></table>'
    html_msg += '</body></html>'
    email.attach(MIMEText(html_msg, 'html'))

    return email.as_string()


def main():
    filename = os.path.basename(__file__).split('.')[0]
    config_file = '{0}.yaml'.format(filename)
    for account_name in ACCOUNT_NAMES:
        flavor_count, tenants_instances, down_instances = \
            get_data(config_file, account_name)
        send_mail(build_msg(flavor_count, tenants_instances, down_instances))


if __name__ == '__main__':
    main()
