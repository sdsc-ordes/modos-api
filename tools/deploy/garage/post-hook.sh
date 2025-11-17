#!/usr/bin/env bash

sleep 5
garage layout assign -z dc1 -c 1G $(garage status | tail -n1 | cut -f1 -d' ' )
garage layout apply --version 1
garage bucket create ${S3_BUCKET}
garage bucket create ${REFERENCE_BUCKET}
garage key import --yes ${CLIENT_ID} ${CLIENT_SECRET} -n demo
garage bucket allow --read --write --owner ${S3_BUCKET} --key ${CLIENT_ID}
garage bucket allow --read --write --owner ${REFERENCE_BUCKET} --key ${CLIENT_ID}
