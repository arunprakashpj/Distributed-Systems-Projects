# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: Badiuzzaman Iskhandar / Arun Prakash
# ------------------------------------------------------------------------------------------------------
import os
import traceback
import sys
import time
import json
import argparse
import threading
import logging

from bottle import Bottle, run, request, template
import requests
from operator import itemgetter

# ------------------------------------------------------------------------------------------------------
# Constants
# action: 0=modify, 1=delete, 2=add
MODIFY = 0;
DELETE = 1;
ADD    = 2;

# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # Use python array of hashes
    # board = [{'id': 0, 'entry': 'Hello0', 'sender_id': 1, 'orig_node_id': 1},
    #          {...},
    #         ]
    #   orig_node_id is the node_id for the original creator of the id
    board = [{'id': 0, 'entry': "First", 'sender_id': 1, 'orig_node_id': 1}]

    # list that stores pending action to be done
    # Each element is a hash with:
    #   { 'action': <modify|delete>, 'id': <entry_id>,
    #     'orig_node_id': <node_id from creator of this entry>
    #     'newtext': <modified_text|None> }
    action_queue = []

    # sequence_number, the logical clock that will 'tick' whenever
    # a new entry is added
    # Starts from 1 because of dummy id=0 entry above
    seq_num = 1

    node_id = None

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(new_entry):
        global board, node_id, seq_num, action_queue
        success = False

        try:
            # Ex. cases: pending modify, two nodes delete the same message
            logging.debug("add_new_element_to_store: BEFORE action_queue=%s", str(action_queue))
            pending_act = find_pending_action(new_entry['id'], new_entry['orig_node_id'])
            if pending_act:
                logging.debug("add_new_element_to_store: pending action for id=%d orig_nid=%d action=%d",
                              pending_act['id'], pending_act['orig_node_id'], pending_act['action'])
                if pending_act['action'] == MODIFY:
                    seq_num += 1
                    new_entry['entry'] = pending_act['newtext']
                    board.append(new_entry)
                    action_queue.remove(pending_act)
                elif pending_act['action'] == DELETE:
                    # No need to add? Duplicate delete action is checked in delete_element_from_store
                    # Since no element added, seq_num logical clock remains unchanged
                    logging.debug("add_new_element_to_store: pending delete, SKIP add")
                    action_queue.remove(pending_act)
            else:
                seq_num += 1
                board.append(new_entry)

            logging.debug("add_new_element_to_store: AFTER action_queue=%s", str(action_queue))
            # sort board array based on entry_id
            # board = sorted(board, key=itemgetter('id'))
            logging.debug("seq_num=%d", seq_num)
            success = True
        except Exception as e:
            print e

        return success

    def find_pending_action(entry_id, orig_node_id):
        global action_queue

        pending_act = None
        for action in action_queue:
            if action['orig_node_id'] == orig_node_id and action['id'] == entry_id:
                pending_act = action

        return pending_act

    def sort_by_senderid_entryid(entry1, entry2):
        """
        Custom comparator function for board.
        If ids for entry1 and entry2 conflicts, then break ties by having larger node wins
        """
        if entry1['id'] > entry2['id']:
            return 1
        elif entry1['id'] == entry2['id']:
            if entry1['sender_id'] >= entry2['sender_id']:
                return -1
            else:
                return 1
        else:
            return -1

    def modify_element_in_store(entry_id, orig_node_id, modified_element):
        global board, node_id, action_queue
        success = False
        found_entry = False
        try:
            for elem in board:
                if elem['id'] == entry_id and elem['orig_node_id'] == orig_node_id:
                    found_entry = True
                    elem['entry'] = modified_element

            # We haven't received the packet to create this particular entry yet,
            # so store this modify_action as pending and execute it once we
            # receive the add entry packet
            if not found_entry:
                logging.debug("modify_element_in_store: NOT FOUND entry_id=%d, orig_nid=%s",
                              entry_id, str(orig_node_id))
                action_queue.append({'action': MODIFY,'orig_node_id': orig_node_id,
                                     'newtext': modified_element, 'id': entry_id})
            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_id, orig_node_id):
        global board, node_id, action_queue, seq_num
        success = False
        found_entry = False
        try:
            # board[:] means to create a copy. Why? Because we want to delete some element in it
            for elem in board[:]:
                if elem['id'] == entry_id and elem['orig_node_id'] == orig_node_id:
                    found_entry = True
                    board.remove(elem)

            # If we can't find the entry to delete, then record the action if not duplicate
            # Determine duplicate action by checking the time skew
            if not found_entry:
                pending_act = find_pending_action(entry_id, orig_node_id)
                action = pending_act['action'] if pending_act else None # WA to avoid crash
                logging.debug("BEFORE action_q=%s", str(action_queue))

                if pending_act and action == DELETE:
                    # If there is a pending delete, then check the time
                    # skew by comparing logical clock. If the diff is small, then
                    # assume two concurrent deletes and don't record the action.
                    # E.g., user accidentally press delete to an item twice. It's safer to be
                    # more conservative on delete
                    skew = seq_num - entry_id
                    if skew > 3:
                        logging.debug("delete_element_from_store: skew>3, NOT FOUND entry_id=%d, orig_nid=%s",
                                      entry_id, str(orig_node_id))
                        action_queue.append({'action': DELETE, 'orig_node_id': orig_node_id,
                                             'newtext': None, 'id': entry_id})
                    else:
                        logging.debug("delete_element_from_store: skew<3, SKIP action entry_id=%d, orig_nid=%s",
                                      entry_id, str(orig_node_id))
                else:
                    logging.debug("delete_element_from_store: NOT FOUND entry_id=%d, orig_nid=%s",
                                  entry_id, str(orig_node_id))
                    action_queue.append({'action': DELETE, 'orig_node_id': orig_node_id,
                                         'newtext': None, 'id': entry_id})

                logging.debug("AFTER action_q=%s", str(action_queue))

            success = True
        except Exception as e:
            print e
        return success

    # ------------------------------------------------------------------------------------------------------
    # DISTRIBUTED COMMUNICATIONS FUNCTIONS
    # should be given to the students?
    # ------------------------------------------------------------------------------------------------------
    def contact_vessel(vessel_ip, path, payload=None, req='POST'):
        # Try to contact another server (vessel) through a POST or GET, once
        success = False
        trial = 1
        while not success:
            try:
                if 'POST' in req:
                    res = requests.post('http://{}{}'.format(vessel_ip, path), json=payload)
                elif 'GET' in req:
                    res = requests.get('http://{}{}'.format(vessel_ip, path))
                else:
                    print 'Non implemented feature!'
                print(res.text)
                if res.status_code == 200:
                    logging.debug("contact_vessel:OK: dest=%s, path=%s, payload=%s",
                        vessel_ip, path, str(payload))
                    success = True
            except Exception as e:
                logging.error("contact_vessel:KO: trial=%d, dest=%s, path=%s, payload=%s",
                    trial, vessel_ip, path, str(payload))
                logging.error("contact_vessel: %s", e)
                print e
                time.sleep(1)
                trial += 1
        return success

    def propagate_to_vessels(path, payload = None, req = 'POST'):
        global vessel_list, node_id

        logging.debug("propagate_to_vessels +")
        for vessel_id, vessel_ip in vessel_list.items():
            if int(vessel_id) != node_id: # don't propagate to yourself
                success = contact_vessel(vessel_ip, path, payload, req)
                if not success:
                    print "\n\nCould not contact vessel {}\n\n".format(vessel_id)

        logging.debug("propagate_to_vessels -")

    def propagate_to_vessels_thread(path, payload, req):
        thr = threading.Thread(target=propagate_to_vessels, args=(path, payload, req))
        thr.daemon = True
        thr.start()


    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        board = sorted(board, cmp=sort_by_senderid_entryid)
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=board, members_name_string='Badiuzzaman Iskhandar / Arun Prakash')

    @app.get('/board')
    def get_board():
        global board, node_id
        # print board
        board = sorted(board, cmp=sort_by_senderid_entryid)
        return template('server/boardcontents_template.tpl',board_title='Vessel {}'.format(node_id), board_dict=board)
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        """
        Adds a new element to the board
        Called directly when a user is doing a POST request on /board
        """
        global board, node_id
        try:
            # seq_num will be incremented on each entry
            entry_id = seq_num
            new_entry = {'id': entry_id, 'entry': request.forms.get('entry'),
                         'sender_id': node_id, 'orig_node_id': node_id}
            add_new_element_to_store(new_entry)
            logging.debug("Added new entry, entry_id=%d, entry=%s", entry_id, new_entry['entry'])

            # Propagate changes to all vessels
            endpoint = "/board/{}".format(entry_id)
            # action: 0=modify, 1=delete, 2=add
            payload = {'entry': new_entry['entry'], 'action': ADD,
                       'sender_id': node_id, 'orig_node_id': node_id}
            propagate_to_vessels_thread(endpoint, payload, 'POST')

            return str("")
        except Exception as e:
            print e
        return str(False)

    @app.post('/board/<entry_id>')
    def client_action_received(entry_id):
        global board, node_id
        entry_id = int(entry_id)

        # extract JSON POSTed to this endpoint
        entry_text = request.json.get('entry')
        action = int(request.json.get('action'))
        sender_id = int(request.json.get('sender_id'))
        orig_node_id = int(request.json.get('orig_node_id'))

        logging.debug("client_action_received: entry=%s, entry_id=%d, action=%d, sender_id=%d, orig_node_id=%d",
                      entry_text, entry_id, action, sender_id, orig_node_id)

        # action: 0=modify, 1=delete, 2=add
        if action == MODIFY:
            modify_element_in_store(entry_id, orig_node_id, entry_text)
        elif action == DELETE:
            delete_element_from_store(entry_id, orig_node_id)
        elif action == ADD:
            add_new_element_to_store({'id': entry_id, 'entry': entry_text,
                                      'sender_id': sender_id, 'orig_node_id': orig_node_id})

    # Capture 'action' from update/delete form. If user press modify, pass value=0
    @app.post('/propagate/<action>/<entry_id>')
    def form_modify_delete(action, entry_id):
        global board, node_id
        action = int(action)
        entry_id = int(entry_id)
        entry_text = request.forms.get('entry')
        orig_node_id = int(request.forms.get('orig_node_id'))
        logging.debug("form_modify_delete: action=%s, entry_id=%s, orig_node_id=%d", action, entry_id, orig_node_id)

        # action: 0=modify, 1=delete, 2=add
        if action == MODIFY:
            modify_element_in_store(entry_id, orig_node_id, entry_text)
        elif action == DELETE:
            delete_element_from_store(entry_id, orig_node_id)

        # Distribute changes
        endpoint = "/board/{}".format(entry_id)
        payload = {'entry': entry_text, 'action': action, 'sender_id': node_id, 'orig_node_id': orig_node_id}
        propagate_to_vessels_thread(endpoint, payload, 'POST')

    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for postGive it to the students-----------------------------------------------------------------------------------------------------
    # Execute the code
    def main():
        global vessel_list, node_id, app

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        os.system("echo > log_vessel{}.txt".format(node_id)) # force to cleanup log upon server restart
        logging.basicConfig(filename="log_vessel{}.txt".format(node_id), level=logging.DEBUG,
                            format='%(threadName)s:%(levelname)s: %(message)s')
        logging.debug('\n\n========== Starting server ===========\n\n')
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port, debug=True)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)
