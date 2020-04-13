#!/usr/bin/env python
import inspect
import logging
import random
import threading
import time
from typing import List, Optional, Dict, Callable, Tuple

from messages import AppendEntriesMessage, VoteMessage, DbEntriesMessage
from state_machine import StateMachine, DummyStateMachine
from peer import Peer
from rpc_client import RpcClient
from rpc_server import RpcServer
from states import NodePersistentState, NodeVolatileState, LeaderVolatileState, Entry

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class NoisyLock(object):
    """
    NoisyLock is just like threading.Lock except it noisily spams info about who locks and unlocks it.
    Useful for debugging, not so useful in prod.
    """

    def __init__(self):
        self._lock = threading.Lock()

    def __enter__(self):
        curr_frame = inspect.currentframe()
        call_frame = inspect.getouterframes(curr_frame, 2)
        call_name = call_frame[1][3]
        LOG.debug("LOCK ENTER: " + call_name)
        self._lock.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        curr_frame = inspect.currentframe()
        call_frame = inspect.getouterframes(curr_frame, 2)
        call_name = call_frame[1][3]
        LOG.debug("LOCK EXIT: " + call_name)
        self._lock.__exit__(exc_type, exc_val, exc_tb)


class Node(object):
    STATE_FOLLOWER = 0
    STATE_CANDIDATE = 1
    STATE_LEADER = 2

    def __init__(self, node_id: int, persistent_state: 'NodePersistentState', peers: List[Peer],
                 state_machine: StateMachine,
                 election_timeout_ms_min: int = 2000, election_timeout_ms_max: int = 10000,
                 loop_interval_ms: int = 1000):
        LOG.debug("Node init node_id: %d peers:%s persistent_state: %s", node_id, peers, persistent_state._fpath)
        self._node_id: int = node_id
        self._node_persistent_state: NodePersistentState = persistent_state
        self._node_volatile_state: NodeVolatileState = NodeVolatileState()
        self._leader_volatile_state: Optional[LeaderVolatileState] = None
        self._peers: List[Peer] = peers
        self._server: Optional[RpcServer] = None
        self._client: RpcClient = RpcClient()
        self._state: int = Node.STATE_FOLLOWER
        # self._lock: threading.Lock = threading.Lock()
        self._lock: NoisyLock = NoisyLock()
        self._last_heartbeat: float = 0.0
        self._state_machine: StateMachine = state_machine
        self._should_step_down: bool = False
        self._election_timeout_ms = None  # set below
        self._election_timeout_ms_min: int = election_timeout_ms_min
        self._election_timeout_ms_max: int = election_timeout_ms_max
        self._loop_interval_ms: int = loop_interval_ms

    def start(self, host: str, port: int):
        LOG.debug("Node start host:%s port:%d", host, port)
        self.reset_election_timeout()
        with self._lock:
            handlers: Dict[bytes, Callable] = {
                b'vote': self.handle_request_vote,
                b'append': self.handle_append_entries,
                b'db': self.handle_database_request,
            }
            self._server = RpcServer(host, port, handlers)
            self._server.start()

        self.loop_forever()

    def stop(self):
        LOG.debug("Node stop")
        with self._lock:
            self._server.stop()

    def loop_forever(self):
        LOG.debug("Node looping forever")
        while True:
            self.do_regular()
            self.do_follower()
            self.do_candidate()
            self.do_leader()
            time.sleep(self._loop_interval_ms / 1000)
            self.decrease_election_timeout()

    def do_regular(self):
        with self._lock:
            curr_commit_idx = self._node_volatile_state.get_commit_idx()
            curr_last_applied = self._node_volatile_state.get_last_applied()
            LOG.debug("Node do_regular commit_idx:%d last_applied:%d", curr_commit_idx, curr_last_applied)
            if curr_commit_idx > curr_last_applied:
                curr_last_applied += 1
                self._state_machine.apply(self._node_persistent_state.get_logs()[curr_last_applied])
                self._node_volatile_state.set_last_applied(curr_last_applied)

            if self._should_step_down:
                LOG.debug("Node do_regular: stepping down")
                self._state = Node.STATE_FOLLOWER

    def do_follower(self):
        # TODO: implement me
        LOG.debug("Node do_follower")
        if not self.is_follower():
            LOG.debug("Node is not follower")
            return

        # if election timeout elapses without receiving AppendEntries RPC from current leader
        # or granting vote to candidate: convert to candidate.
        if self.get_election_timeout_ms() <= 0:
            self.become_candidate()

    def do_candidate(self):
        # TODO: implement me
        LOG.debug("Node do_candidate")
        if not self.is_candidate():
            LOG.debug("Node is not candidate")
            return

        with self._lock:
            if self._should_step_down:
                LOG.info("stepping down from candidate to follower")
                self._state = Node.STATE_FOLLOWER
                return

        # if election timeout elapses: start new election
        if self.get_election_timeout_ms() <= 0:
            self.become_candidate()


    def do_leader(self):
        # TODO: implement me
        LOG.debug("Node do_leader")
        if not self.is_leader():
            LOG.debug("Node is not leader")
            return

    def get_election_timeout_ms(self):
        with self._lock:
            return self._election_timeout_ms

    def decrease_election_timeout(self):
        with self._lock:
            self._election_timeout_ms = max(0, self._election_timeout_ms - self._loop_interval_ms)
            LOG.debug("election timeout: %d", self._election_timeout_ms)

    def reset_election_timeout(self):
        with self._lock:
            self._election_timeout_ms = random.randint(self._election_timeout_ms_min, self._election_timeout_ms_max)
            LOG.debug("election timeout reset: %d", self._election_timeout_ms)

    def handle_append_entries(self, bytes_: bytes) -> Tuple[int, bool]:
        LOG.debug("Node handle_append_entries bytes:%s", bytes_)
        with self._lock:
            msg: AppendEntriesMessage = AppendEntriesMessage.from_bytes(bytes_)
            current_term: int = self._node_persistent_state.get_term()
            # Reply false if term < currentTerm (§5.1)
            if msg.term < self._node_persistent_state.get_term():
                return current_term, False

            # Reply false if log doesn’t contain an entry at prevLogIndex whose term matches prevLogTerm (§5.3)
            existing_logs: List[Entry] = self._node_persistent_state.get_logs()
            try:
                existing_entry = existing_logs[msg.prev_log_idx]
            except KeyError:
                return current_term, False

            if existing_entry._term != msg.prev_log_term:
                # If an existing entry conflicts with a new one (same index but different terms), delete the existing entry
                # and all that follow it (§5.3)
                pruned_logs = existing_logs[:msg.prev_log_idx + 1]
                self._node_persistent_state.set_logs(pruned_logs)
                return current_term, False

            last_commit_idx = len(existing_logs) - 1
            if msg.entry not in existing_logs:
                last_commit_idx = self._node_persistent_state.append_log(msg.entry)

            curr_commit_idx = self._node_volatile_state.get_commit_idx()
            if msg.leader_commit_idx > curr_commit_idx:
                new_commit_idx = min(msg.leader_commit_idx, last_commit_idx)
                self._node_volatile_state.set_commit_idx(new_commit_idx)

            self._last_heartbeat = time.time()
            # If AppendEntries RPC received from new leader: convert to follower
            if self._state == Node.STATE_CANDIDATE:
                LOG.debug(
                    'handle_append_entries: node_id:%s got AppendEntries from new leader node_id:%s -- stepping down',
                    self._node_id,
                    msg.leader_id)
                self._state = Node.STATE_FOLLOWER
            return self._node_persistent_state.get_term(), True

    def handle_request_vote(self, bytes_: bytes):
        LOG.debug("Node handle_request_vote bytes:%s", bytes_)
        with self._lock:
            msg: VoteMessage = VoteMessage.from_bytes(bytes_)
            current_term: int = self._node_persistent_state.get_term()
            # Reply false if term < currentTerm (§5.1)
            if msg.term < current_term:
                LOG.debug("Node handle_request_vote: msg_term:%d behind current_term:%d ", current_term, msg.term)
                return current_term, False

            # If votedFor is null or candidateId, and candidate’s log is at
            # least as up-to-date as receiver’s log, grant vote (§5.2, §5.4)
            voted_for = self._node_persistent_state.get_voted_for()
            if voted_for is not None and voted_for != msg.candidate_id:
                LOG.debug("Node handle_request_vote: already voted for node_id:%d", voted_for)
                return current_term, False

            logs: List[Entry] = self._node_persistent_state.get_logs()
            our_last_log_idx = len(logs) - 1

            if our_last_log_idx > msg.last_log_idx:
                LOG.debug("Node handle_request_vote: candidate not up to date: node_id:%s")
                return current_term, False

            LOG.info("Node handle_request_vote: giving a vote to node_id:%d", msg.candidate_id)
            self._node_persistent_state.set_voted_for(msg.candidate_id)
            return current_term, True

    def handle_database_request(self, bytes_: bytes):
        LOG.debug("Node handle_database_request bytes:%s", bytes_)
        with self._lock:
            # Get some request for database from flask-client probably
            # TODO Should take room from flask and initiate append logs for room booking
            msg: DbEntriesMessage = DbEntriesMessage.from_bytes(bytes_)

        return msg, True

    def is_leader(self) -> bool:
        LOG.debug("Node is_leader")
        with self._lock:
            return self._state == Node.STATE_LEADER

    def become_leader(self) -> bool:
        LOG.debug("Node become_leader")
        with self._lock:
            if self._state == Node.STATE_LEADER:
                return False
            raise NotImplementedError

    def is_candidate(self) -> bool:
        LOG.debug("Node is_candidate")
        with self._lock:
            return self._state == Node.STATE_CANDIDATE

    def become_candidate(self) -> bool:
        LOG.debug("Node become_candidate")
        # On conversion to candidate, start election:
        with self._lock:
            self._state = Node.STATE_CANDIDATE
            # increment currentTerm
            self._node_persistent_state.increment_term()
            # vote for self
            self._node_persistent_state.set_voted_for(self._node_id)
            # reset election timer
            self._election_timeout_ms = random.randint(self._election_timeout_ms_min, self._election_timeout_ms_max)
            # send RequestVote RPC to all other servers
            current_term = self._node_persistent_state.get_term()
            logs = self._node_persistent_state.get_logs()
            last_log_idx = len(logs) - 1
            try:
                last_log_term = logs[-1]._term
            except IndexError:
                last_log_term = 0

            msg = VoteMessage(current_term, self._node_id, last_log_idx, last_log_term)
            num_votes = 0
            votes_needed = int(len(self._peers) / 2) + 1  # need a majority
            for peer in self._peers:
                # TODO: what to do with their term?
                _, got_vote = self._client.send(peer, msg)
                if got_vote is None:
                    LOG.error("become_candidate: could not get vote from %s", peer)
                elif got_vote:
                    LOG.debug("become_candidate: got vote from %s", peer)
                    num_votes += got_vote
                else:
                    LOG.debug("become_candidate: lost vote from %s", peer)

            LOG.debug("become_candidate: need %d/%d votes, got %d/%d", votes_needed, len(self._peers), num_votes,
                      len(self._peers))
            won_election = num_votes >= votes_needed

        if won_election:
            LOG.debug("become_candidate: node_id:%d yay I won!", self._node_id)
            self.become_leader()
        return True

    def is_follower(self) -> bool:
        LOG.debug("Node is_follower")
        with self._lock:
            return self._state == Node.STATE_FOLLOWER

    def become_follower(self) -> bool:
        LOG.debug("Node become_follower")
        with self._lock:
            self._state = Node.STATE_FOLLOWER
            return True
