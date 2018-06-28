PYTHON_PKG_PATH_PATTERN=\
~/.virtualenvs/rackspace-automation-min/lib/python2.7/site-packages/*
CREDENTIALS_PATH=gspread_credentials.json

zip: gspread_credentials.json rackspace_automation.py
	zip -d rackspace_automation.zip $(CREDENTIALS_PATH) \
	rackspace_automation.py $(PYTHON_PKG_PATH_PATTERN) -r