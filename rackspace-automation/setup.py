from setuptools import setup, find_packages

setup(name='rackspace_rule_automation', version='1.0', packages=find_packages(),
      install_requires=[
          "python-keystoneclient==3.16.0",
          "python-novaclient==10.2.0",
          "oauth2client==4.1.2",
          "gspread==3.0.0",
          "boto3==1.7.12"
      ])