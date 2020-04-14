from flask import Blueprint, render_template, redirect, url_for, request, flash
from forms.login import LoginForm
import operation
import os
from raft_example import *
from raft_peer import Peer
from raft_rpc_client import RpcClient
import random
import socketserver
import threading

sv = Blueprint("sv", __name__)  # initialise a Blueprint instance


def raft_init():
    peer_value = os.environ['PEERS'].split(' ')
    self_info = os.environ['SELF']
    node_id, self_host, self_port = parse_peer(self_info)
    random.seed(node_id) # for some measure of predictability
    state = './state.json'
    socketserver.TCPServer.allow_reuse_address = True
    peers = []
    for i, peer_str in enumerate(peer_value):
        peer_id, host, port = parse_peer(peer_str)
        p = Peer(peer_id, host, port)
        peers.append(p)

    prev_state = NodePersistentState.load(state)
    state_machine = DummyStateMachine()
    node = Node(node_id, prev_state, peers, state_machine)
    node_thread = threading.Thread(target=node.start, args=[self_host, self_port])
    node_thread.daemon = True
    node_thread.start()


raft_init()

@sv.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@sv.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if request.method == 'GET':
            username = request.args.get('username')
        else:
            username = request.form.get('username')
        return redirect('/search')
    return render_template('login.html', form=form)


@sv.route('/search', methods=['GET', 'POST'])
def search():
    rpc_client, peer = rpc_set_up()
    conn = operation.connect('./test.db')
    table_name = 'room'
    unoccupied = operation.select(conn, table_name)
    occupied = operation.select(conn, table_name, 'occupied')
    labels = ['RoomID']
    occupied_room_id = [i[1] for i in occupied]
    unoccupied_room_id = [i[1] for i in unoccupied]
    if request.method == 'POST':
        result = dict()
        for idx in unoccupied_room_id:
            if request.values.get(str(idx)) == 'Y':
                # result[idx] = operation.update(conn, table_name, idx)
                message_sent, success = rpc_client.send(peer, b"db %d" % int(idx))
                if success == 'False':
                    if message_sent != 0:
                        if message_sent is not unoccupied_room_id:
                            # Assuming leader ID --> Re-send request to leader
                            peer_id, host, port = parse_peer(message_sent)
                            p = Peer(peer_id, host, port)
                            message_sent, success = rpc_client.send(p, b"db %d" % int(idx))
                        else:
                            return redirect(url_for('.success_book', message=message_sent, s=success))
                    else:
                        # By pass conditional for now until can receive leader id.
                        return redirect(url_for('.success_book', message="redirection to leader", s=False))
                else:
                    return redirect(url_for('.success_book', message=message_sent, s=success))

        if len(result):
            for idx, flag in result.items():
                if flag:
                    flash('Room {} successfully booked'.format(idx))
                else:
                    flash('Room {} not available'.format(idx))

    return render_template('search.html', labels=labels, content=unoccupied_room_id, content1=occupied_room_id)


@sv.route('/test_raft', methods=['GET'])
def test_raft():
    rpcClient, peer = raft_set_up()
    t, s = rpcClient.send(peer, b"db 101")
    data = {"Message Sent": t, "Success:": s}
    return data


@sv.route('/success', methods=['GET'])
def success_book():
    messages = request.args['message']
    success = request.args['s']
    if success == 'True':
        return "Successfully booked " + messages + " room"
    else:
        return "Unsuccessfully booked " + messages + " room"


def rpc_set_up():
    peer_value = os.environ['SELF']
    peer_id, host, port = parse_peer(peer_value)
    p = Peer(peer_id, host, port)
    client = RpcClient()

    return client, p