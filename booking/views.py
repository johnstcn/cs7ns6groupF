from flask import Blueprint, render_template, redirect, url_for, request, flash
from forms.login import LoginForm
from models import *
import db_operation
import os
from ipc import *
import threading
from example import *

sv = Blueprint("sv", __name__)  # initialise a Blueprint instance


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
    rpc_client, peer = raft_set_up()                                          # Initialise RPC Client
    u = Room.query.filter(Room.RoomState == 'unoccupied').all()
    labels = ['RoomID']
    room_id = [i.RoomID for i in u]
    if request.method == 'POST':
        result = dict()
        for idx in room_id:
            if request.values.get(idx) == 'Y':
                result[idx] = db_operation.update(idx)
                message_sent, success = rpc_client.send(peer, b"db %d" % int(idx))
                return redirect(url_for('.success_book', message=message_sent, s=success))

        if len(result):
            for idx, flag in result.items():
                if flag:
                    print(1)
                    flash('Room {} successfully booked'.format(idx))
                else:
                    print(0)
                    flash('Room {} not available'.format(idx))

    return render_template('search.html', labels=labels, content=room_id)

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

def ipc_test():
    id = int(os.environ['PEER_ID'])
    print(id)
    peers_value = os.environ['PEERS'].split(' ')
    print(peers_value)
    peers = list(map(parse_hostport, peers_value))
    print(peers)
    p = Process(id, peers)
    ipc_thread = threading.Thread(target=p.run)
    ipc_thread.start()
    return p


def raft_set_up():
    peer_value = os.environ['PEERS']
    peer_id, host, port = parse_peer(peer_value)
    p = Peer(peer_id, host, port)
    client = RpcClient()

    return client, p
