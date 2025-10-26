# Makefile

# Specify the Python version
PYTHON_VERSION := python3.13
LAMBDA_VENV := .lambda_venv
PACKAGE_NAME := invocation_lambda_package.zip
LAMBDA_FUNCTION := index.py agent.py

# Default target executed when no arguments are given to make.
default: clean package

# Setup a virtual environment
venv:
	$(PYTHON_VERSION) -m venv $(LAMBDA_VENV)
	$(LAMBDA_VENV)/bin/pip install -U pip

# Install dependencies into the virtual environment
dependencies: venv
	$(LAMBDA_VENV)/bin/pip install -r requirements.txt

# Package the virtual environment libraries and your lambda function into a zip
package: dependencies
	# Adding python packages
	cd $(LAMBDA_VENV)/lib/$(PYTHON_VERSION)/site-packages; zip -r9 $(CURDIR)/$(PACKAGE_NAME) .
	# Adding your lambda function and any additional files
	zip -g $(PACKAGE_NAME) $(LAMBDA_FUNCTION)

# Clean up the environment
clean:
	rm -rf $(LAMBDA_VENV)
	rm -f $(PACKAGE_NAME)

.PHONY: default venv dependencies package