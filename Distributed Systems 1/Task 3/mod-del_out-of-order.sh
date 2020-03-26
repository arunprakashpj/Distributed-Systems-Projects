#!/usr/bin/env bash

# MODIFY=0, DELETE=1
# /propagate/<action>/<entry_id>

# modify entry with id=5
curl -d 'orig_node_id=1&entry=modify_vessel1' -X 'POST' "http://10.1.0.1:80/propagate/0/5"

#for i in `seq 1 5`; do
#    curl -d 'entry=from_vessel1_'${i} -X 'POST' 'http://10.1.0.1:80/board' &
#done
