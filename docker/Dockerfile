FROM python:3.6-alpine

RUN pip install --upgrade pip

RUN pip install --no-cache pytz pyyaml python-dateutil
RUN pip install --no-cache cityiq

ADD city-iq.yaml $USER/.city-iq.yaml
