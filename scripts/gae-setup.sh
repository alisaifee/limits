#!/bin/bash
PY3=$(echo "$(python --version | grep -E -o '([0-9\.]+){2}' | awk -F . '{print $1"."$2}') >= 3" | bc);
if [ ! -e google-cloud-sdk ];
then
    if [ $PY3 -eq 0 ];
    then
        export CLOUDSDK_PYTHON=$(which python)
        wget https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-167.0.0-linux-x86_64.tar.gz -P /var/tmp/;
        tar -xzf /var/tmp/google-cloud-sdk-167.0.0-linux-x86_64.tar.gz;
        yes Y | google-cloud-sdk/bin/gcloud components install app-engine-python;
        ln -s google-cloud-sdk/platform/google_appengine/google google;
    fi;
fi;
