PYTHON_PKG_PATH_PATTERN=\
~/.virtualenvs/rackspace-automation-min/lib/python2.7/site-packages/*
CREDENTIALS_PATH=gspread_credentials.json
ZIP_NAME=rackspace_automation.zip

zip: gspread_credentials.json rackspace_automation.py clean
	zip $(ZIP_NAME) $(CREDENTIALS_PATH) \
	rackspace_automation.py $(PYTHON_PKG_PATH_PATTERN) -r

clean:
	rm -f $(ZIP_NAME)