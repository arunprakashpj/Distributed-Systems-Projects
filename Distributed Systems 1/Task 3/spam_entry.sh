#!/usr/bin/env bash

for i in `seq 1 5`; do
    curl -d 'entry=from_vessel1_'${i} -X 'POST' 'http://10.1.0.1:80/board' &
done
for i in `seq 1 5`; do
    curl -d 'entry=from_vessel2_'${i} -X 'POST' 'http://10.1.0.2:80/board' &
done
for i in `seq 1 5`; do
    curl -d 'entry=from_vessel3_'${i} -X 'POST' 'http://10.1.0.3:80/board' &
done
