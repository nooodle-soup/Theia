FROM python:3.12-alpine

WORKDIR /usr/development

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./dev_requirements.txt .
RUN pip install -r dev_requirements.txt
