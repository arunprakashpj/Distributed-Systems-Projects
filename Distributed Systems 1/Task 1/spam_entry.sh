#!/usr/bin/env bash

for i in `seq 1 5`; do
    curl -d 'entry=from_curl'${i} -X 'POST' 'http://10.1.0.1:80/board' &
done
for i in `seq 1 5`; do
    curl -d 'entry=from_curl'${i} -X 'POST' 'http://10.1.0.2:80/board' &
done
for i in `seq 1 5`; do
    curl -d 'entry=from_curl'${i} -X 'POST' 'http://10.1.0.3:80/board' &
done
