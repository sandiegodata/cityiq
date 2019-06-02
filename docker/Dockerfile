FROM python:3.6-alpine

# Userids to match Jupyter
# https://github.com/jupyter/docker-stacks/blob/master/base-notebook/Dockerfile
#ARG NB_USER="jovyan"
#ARG NB_UID="1000"
#ARG NB_GROUP="users"
#ARG NB_GID="100"

ARG NB_USER="eric502"
ARG NB_UID="502"
ARG NB_GROUP="users"
ARG NB_GID="100"

RUN apk add git
RUN pip install --upgrade pip
RUN pip install --no-cache pytz pyyaml python-dateutil
RUN pip install --no-cache git+https://github.com/sandiegodata/cityiq #3


RUN adduser -D -u ${NB_UID} -G ${NB_GROUP}  ${NB_USER}

ADD city-iq.yaml /home/$NB_USER/.city-iq.yaml

USER ${NB_USER}
