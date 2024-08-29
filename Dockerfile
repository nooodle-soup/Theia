# Use an official Python runtime based on Alpine as a parent image
FROM python:3.12-alpine

# Set the working directory to /usr/dev
WORKDIR /usr/dev

# Install necessary build tools and dependencies
# RUN apk update && apk add --no-cache \ build-base \ libffi-dev \ openssl-dev \ python3-dev \ musl-dev \ gcc \ make

# Create a virtual environment in /usr/dev
RUN python -m venv venv

# Upgrade pip and setuptools in the virtual environment
RUN ./venv/bin/pip install --upgrade pip setuptools wheel

# Copy the project files to the working directory
COPY . /usr/dev/theia-project

# Set the working directory to the project directory
WORKDIR /usr/dev/theia-project

# Install the project in editable mode with dev dependencies
RUN /usr/dev/venv/bin/pip install -e .[dev]

# Set the entrypoint to use the virtual environment
ENTRYPOINT ["/bin/sh"]
