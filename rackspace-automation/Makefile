PYTHON_PKG_PATH_PATTERN=site-packages
CREDENTIALS_PATH=gspread_credentials.json
ZIP_PATH=/home/david/development/it-scripts/rackspace-automation/rackspace_automation.zip

zip: gspread_credentials.json rackspace_automation.py clean
	zip $(ZIP_PATH) rackspace_automation.py $(CREDENTIALS_PATH)
	cd $(PYTHON_PKG_PATH_PATTERN);\
	zip -u $(ZIP_PATH) . -r;\
	cd -

clean:
	rm -f $(ZIP_NAME)