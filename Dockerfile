FROM ubuntu:18.04
ARG download_url

WORKDIR /
RUN apt-get -qq update > /dev/null && apt-get -qq install -y unzip patch curl > /dev/null
RUN /bin/bash -c "curl ${download_url} -o nRF5_SDK.zip && mkdir nrf-sdk && unzip -qq nRF5_SDK.zip -d nrf-sdk && rm nRF5_SDK.zip;cd /nrf-sdk;shopt -s dotglob;mv nRF5_SDK_*/* .;rmdir nRF5_SDK_*;:;"
