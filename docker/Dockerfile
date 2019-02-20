FROM python:3.6-alpine

RUN apk add git

RUN pip install --upgrade pip

RUN pip install --no-cache pytz pyyaml python-dateutil
RUN pip install --no-cache git+https://github.com/sandiegodata/cityiq

ADD city-iq.yaml $USER/.city-iq.yaml
