#!/usr/bin/env bash

sleep 5
garage layout assign -z dc1 -c 1G $(garage status | tail -n1 | cut -f1 -d' ' )
garage layout apply --version 1
garage bucket create modos-demo
garage key import --yes ${CLIENT_ID} ${CLIENT_SECRET} -n demo
garage bucket allow --read --write --owner modos-demo --key ${CLIENT_ID}
