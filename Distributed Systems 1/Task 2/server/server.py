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

from bottle import Bottle, run, request, template, response
import requests
from random import randint
from operator import itemgetter

# ------------------------------------------------------------------------------------------------------
# Constants
# action: 0=modify, 1=delete, 2=add
MODIFY = 0;
DELETE = 1;
ADD    = 2;

# ------------------------------------------------------------------------------------------------------
# Global variables
candidate_id = None
candidates = []
elected_leader = None
max_id = 0
# ------------------------------------------------------------------------------------------------------

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
            # Sort based on id
            board = sorted(board, key=itemgetter('id'))
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
            # rearrange id to account for deleted items. Just shift by -1
            for elem in board:
                if elem['id'] > entry_id:
                    elem['id'] -= 1
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

    def contact_vessel_thread(vessel_ip, path, payload, req):
        thread = threading.Thread(target=contact_vessel, args=(vessel_ip, path, payload, req))
        thread.daemon = True
        thread.start()

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

    def propagate_to_next_neighbor(path, payload, req = "POST"):
        """
        Contact next neighbor, particularly in ring leader election
        since a node can only send message to its next neighbor.
        The next neighbor is simply (current_ip % N)+1
        """
        global node_id, vessel_list
        # Use modulus for wraparound e.g. n=5, 10.1.0.5 will send to 10.1.0.1
        next_neighbor = "10.1.0.{}".format(node_id % len(vessel_list) + 1)
        logging.debug("propagate_to_next_neighbor: path=%s, payload=%s neighborIP=%s",
                      path, str(payload['candidates']), next_neighbor)
        contact_vessel_thread(next_neighbor, path, payload, req='POST')

    def propagate_to_leader(path, payload, req="POST"):
        global elected_leader
        contact_vessel_thread("10.1.0.{}".format(elected_leader), path, payload, req)

    # ------------------------------------------------------------------------------------------------------
    # ROUTES
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for post
    # ------------------------------------------------------------------------------------------------------
    @app.route('/')
    def index():
        global board, node_id, elected_leader, max_id

        return template('server/index.tpl', board_title='Vessel {}'.format(node_id), board_dict=board,
                        members_name_string='Badiuzzaman Iskhandar / Arun Prakash',
                        elected_leader=elected_leader, max_id=max_id)

    @app.get('/board')
    def get_board():
        global board, node_id, candidate_id, elected_leader, max_id
        print >> sys.stderr, "candidate_id =", candidate_id, ", node_id =", node_id
        return template('server/boardcontents_template.tpl', board_title='Vessel {}'.format(node_id),
            board_dict=board, elected_leader=elected_leader, max_id=max_id)
    # ------------------------------------------------------------------------------------------------------
    @app.post('/board')
    def client_add_received():
        """
        Adds a new element to the board
        Called directly when a user is doing a POST request on /board
        """
        global board, node_id, elected_leader
        try:
            # action: 0=modify, 1=delete, 2=add
            entry_text = request.forms.get('entry')
            logging.debug("client_add_received: ADD entry=%s", entry_text)

            if elected_leader == node_id:
                entry_text = request.forms.get('entry') or request.json.get('entry')
                entry_id = len(board)
                endpoint = "/board/{}".format(entry_id)
                new_entry = {'id': entry_id, 'entry': entry_text}
                payload = {'entry': entry_text, 'action': ADD}
                add_new_element_to_store(new_entry)
                propagate_to_vessels_thread(endpoint, payload, 'POST')
            else:
                # Non-leader will POST to leader /board
                entry_text = request.forms.get('entry')
                payload = {'entry': entry_text, 'action': ADD}
                endpoint = "/board"
                logging.debug("client_add_received: NonLeader add entry, entry=%s", entry_text)
                propagate_to_leader(endpoint, payload, "POST")

            response.status = 200
            return
        except Exception as e:
            response.status = 401
            print e

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
        if action == MODIFY:
            modify_element_in_store(entry_id, entry_text)
        elif action == DELETE:
            delete_element_from_store(entry_id)
        elif action == ADD:
            add_new_element_to_store({'id': entry_id, 'entry': entry_text})

    # Capture 'action' from update/delete form. If user press modify, pass value=0
    @app.post('/propagate/<action>/<entry_id>')
    def propagation_received(action, entry_id):
        global board, node_id
        action = int(action)
        entry_id = int(entry_id)

        # NOTE: leader will receive updated info via json, so forms.get will be None
        entry_text = request.forms.get('entry') or request.json.get('entry')
        logging.debug("propagation_received: action=%s, entry_id=%s", action, entry_id)

        if node_id == elected_leader:
            if action == MODIFY:
                modify_element_in_store(entry_id, entry_text)
            elif action == DELETE:
                delete_element_from_store(entry_id)
            endpoint = "/board/{}".format(entry_id)
            payload = {'entry': entry_text, 'action': action}
            propagate_to_vessels_thread(endpoint, payload, "POST")
        else:
            # NonLeader, notify the Leader of the changes you want to be made
            endpoint = "/propagate/{}/{}".format(action, entry_id)
            payload = {'entry': entry_text, 'action': action}
            propagate_to_leader(endpoint, payload, "POST")

    # ------------------------------------------------------------------------------------------------------
    # LEADER ELECTION INTERFACES
    # ------------------------------------------------------------------------------------------------------
    @app.post('/leaderelec/')
    def leaderelec_handler():
        global node_id, candidates, candidate_id, vessel_list, elected_leader, max_id
        recv_candidates = request.json['candidates']
        fingerprint = request.json.get('fingerprint')
        elected_leader = request.json.get('elected_leader')
        # join lists and remove dups. If not payload will be huge
        candidates = list(set(candidates) | set(recv_candidates))

        # Terminating condition for leader election. Else, we are not done
        # yet so continue sending to next neighbor
        if fingerprint == node_id:
            max_id = max(candidates)
            logging.debug("leaderelec_handler: recv_candidates=%s\n\t\tcandidates=%s\n\t\t"
                          "fingerprint=%d, elected_leader=%d",
                          str(recv_candidates), str(candidates), fingerprint, elected_leader)
            logging.debug("leaderelec_handler: DONE election, max_id=%d, elected_leader=%d",
                          max_id, elected_leader)
        else:
            # NOTE: Why <= not < ? Remember that you yourself (candidate_id) is in the candidates list!
            if all(candidate <= candidate_id for candidate in candidates):
                elected_leader = node_id
            endpoint = "/leaderelec/"
            payload = {'candidates': candidates, 'fingerprint': fingerprint,
                       'elected_leader': elected_leader}

            logging.debug("leaderelec_handler: recv_candidates=%s\n\t\tcandidates=%s\n\t\t"
                          "fingerprint=%d, elected_leader=%d",
                          str(recv_candidates), str(candidates), fingerprint, elected_leader)

            propagate_to_next_neighbor(endpoint, payload)

    def election_season(candidate_id):
        """
        Starting point for Leader Election algorithm
        """
        global elected_leader, candidates
        endpoint = "/leaderelec/"

        # Add a unique fingerprint in the packet so we can check it for
        # to stop LE algo
        # Since this is the first message, elected_leader is itself
        payload = {'candidates': candidates, 'fingerprint': node_id,
                   'elected_leader': node_id}

        logging.debug("election_season(): node_id={}, candidate_id={}, candidates={}".format(
            node_id, candidate_id, str(candidates)))

        propagate_to_next_neighbor(endpoint, payload)


    # ------------------------------------------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------------------------------------------
    # a single example (index) should be done for get, and one for postGive it to the students-----------------------------------------------------------------------------------------------------
    # Execute the code
    def main():
        global vessel_list, node_id, app, candidate_id, elected_leader, candidates, max_id

        port = 80
        parser = argparse.ArgumentParser(description='Your own implementation of the distributed blackboard')
        parser.add_argument('--id', nargs='?', dest='nid', default=1, type=int, help='This server ID')
        parser.add_argument('--vessels', nargs='?', dest='nbv', default=1, type=int, help='The total number of vessels present in the system')
        args = parser.parse_args()
        node_id = args.nid
        vessel_list = dict()
        logging.basicConfig(filename='log_vessel{}.txt'.format(node_id),level=logging.DEBUG,
                            format='%(threadName)s:%(levelname)s: %(message)s')
        logging.debug('\n\n========== Starting server ===========\n\n')
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, args.nbv):
            vessel_list[str(i)] = '10.1.0.{}'.format(str(i))

        # set to large enough number to avoid collision.
        candidate_id = randint(1, 100000)
        # max_id will be modified once LE election is done
        max_id = candidate_id
        # append node's own id here instead of at election_season(), observed some timing problem
        # where election_season() is not executed yet but node already received the first message
        candidates.append(candidate_id)
        elected_leader = node_id # initially, a node is the only candidate so elect itself
        logging.debug("main(): candidate_id=%d, node_id=%d", candidate_id, node_id)
        try:
            # NOTE:HERE_BE_DRAGONS: Do NOT enable debug and reloader if launching Bottle server in threads.
            # In log you will see election_season() called twice although you called it once
            thr = threading.Thread(target=run, kwargs=dict(app=app, host=vessel_list[str(node_id)],
                port=port))
            thr.start()
            time.sleep(1)  # wait for all nodes to comes up
            election_season(candidate_id)
        except Exception as e:
            print e

    # ------------------------------------------------------------------------------------------------------
    if __name__ == '__main__':
        main()
except Exception as e:
        traceback.print_exc()
        while True:
            time.sleep(60.)
