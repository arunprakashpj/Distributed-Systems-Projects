# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 - Lab 1
# server/server.py
# Input: Node_ID total_number_of_ID
# Student: Badiuzzaman Iskhandar / Arun Prakash
# ------------------------------------------------------------------------------------------------------
import traceback
import sys
import time
import json
import argparse
import threading
import logging

from bottle import Bottle, run, request, template
import requests
# ------------------------------------------------------------------------------------------------------
try:
    app = Bottle()

    # Use python array of hashes
    # [ {'id': integer, 'entry': 'User input'}, {...}, {...}, ...]
    # board = [{'id': 0, 'entry': 'Hello0'},
    #             {'id': 1, 'entry': 'Hello1'}]
    board = [{'id': 0, 'entry': "First"}]

    # ------------------------------------------------------------------------------------------------------
    # BOARD FUNCTIONS
    # Should nopt be given to the student
    # ------------------------------------------------------------------------------------------------------
    def add_new_element_to_store(element, is_propagated_call=False):
        global board, node_id
        success = False
        try:
            board.append(element)
            success = True
        except Exception as e:
            print e
        return success

    def modify_element_in_store(entry_id, modified_element, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            for elem in board:
                if elem['id'] == entry_id:
                    board[entry_id]['entry'] = modified_element

            success = True
        except Exception as e:
            print e
        return success

    def delete_element_from_store(entry_id, is_propagated_call = False):
        global board, node_id
        success = False
        try:
            board = [elem for elem in board if not elem['id'] == entry_id]
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
        try:
            if 'POST' in req:
                res = requests.post('http://{}{}'.format(vessel_ip, path), json=payload)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(vessel_ip, path))
            else:
                print 'Non implemented feature!'
            # result is in res.text or res.json()
            print(res.text)
            if res.status_code == 200:
                success = True
        except Exception as e:
            print e
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


    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id
        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=board, members_name_string='Badiuzzaman Iskhandar / Arun Prakash')

    @app.get('/board')
    def get_board():
        global board, node_id
        print board
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
            entry_id = len(board)
            new_entry = {'id': entry_id, 'entry': request.forms.get('entry')}
            add_new_element_to_store(new_entry)
            logging.debug("Added new entry, entry_id=%d, entry=%s", entry_id, new_entry['entry'])

            # Propagate changes to all vessels
            endpoint = "/board/{}".format(entry_id)
            # action: 0=modify, 1=delete, 2=add
            payload = {'entry': new_entry['entry'], 'action': 2}
            thr = threading.Thread(target=propagate_to_vessels, args=(endpoint, payload, 'POST'))
            thr.daemon = True
            thr.start()

            return str("")
        except Exception as e:
            print e
        return str(False)

    @app.post('/board/<entry_id>')
    def client_action_received(entry_id):
        global board, node_id
        entry_id = int(entry_id)

        # extract JSON POSTed to this endpoint
        entry_text = request.json['entry']
        action = int(request.json['action'])

        logging.debug("client_action_received: entry=%s, entry_id=%d, action=%d",
                      entry_text, entry_id, action)

        # action: 0=modify, 1=delete, 2=add
        if action == 0:
            modify_element_in_store(entry_id, entry_text)
        elif action == 1:
            delete_element_from_store(entry_id)
        elif action == 2:
            add_new_element_to_store({'id': entry_id, 'entry': entry_text})

    # Capture 'action' from update/delete form. If user press modify, pass value=0
    @app.post('/propagate/<action>/<entry_id>')
    def propagation_received(action, entry_id):
        global board, node_id
        action = int(action)
        entry_id = int(entry_id)
        entry_text = request.forms.get('entry')
        logging.debug("propagation_received: action=%s, entry_id=%s", action, entry_id)

        # action: 0=modify, 1=delete, 2=add
        if action == 0:
            modify_element_in_store(entry_id, entry_text)
        elif action == 1:
            delete_element_from_store(entry_id)

        # Distribute changes
        endpoint = "/board/{}".format(entry_id)
        payload = {'entry': entry_text, 'action': action}
        thr = threading.Thread(target=propagate_to_vessels, args=(endpoint, payload, 'POST'))
        thr.daemon = True
        thr.start()

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
        logging.basicConfig(filename='log_vessel{}.txt'.format(node_id), level=logging.DEBUG, format='%(asctime)s:%(levelname)s: %(message)s')
        logging.debug('\n\n========== Starting server ===========\n\n')
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        try:
            run(app, host=vessel_list[str(node_id)], port=port, reloader=True, debug=True)
        except Exception as e:
            print e
    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)
