#!/usr/bin/env python
import inspect
import logging
import random
import sqlite3
import threading
import time
from typing import List, Optional, Dict, Callable, Tuple

from raft_messages import AppendEntriesMessage, VoteMessage, DbEntriesMessage
from raft_state_machine import StateMachine, DummyStateMachine
from raft_peer import Peer
from raft_rpc_client import RpcClient
from raft_rpc_server import RpcServer
from raft_states import NodePersistentState, NodeVolatileState, LeaderVolatileState, Entry
import operation

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
                 dbconn: sqlite3.Connection,
                 election_timeout_ms_min: int = 3000, election_timeout_ms_max: int = 6000,
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
        self._lock: threading.Lock = threading.Lock()
        # self._lock: NoisyLock = NoisyLock()
        self._dbconn: sqlite3.Connection = dbconn
        self._should_step_down: bool = False
        self._election_timeout_ms = None  # set below
        self._election_timeout_ms_min: int = election_timeout_ms_min
        self._election_timeout_ms_max: int = election_timeout_ms_max
        self._loop_interval_ms: int = loop_interval_ms
        self._votes = 0

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
            if not self.is_leader():
                self.decrease_election_timeout()

    def do_regular(self):
        with self._lock:
            if self._should_step_down:
                LOG.debug("Node do_regular: stepping down")
                self._state = Node.STATE_FOLLOWER
                self._should_step_down = False

            curr_commit_idx = self._node_volatile_state.get_commit_idx()
            while True:
                curr_last_applied = self._node_volatile_state.get_last_applied()
                LOG.debug("Node do_regular commit_idx:%d last_applied:%d", curr_commit_idx, curr_last_applied)
                if curr_commit_idx >= curr_last_applied:
                    break
                curr_last_applied += 1
                entry: Entry = self._node_persistent_state.get_logs()[curr_last_applied]
                db_msg = DbEntriesMessage.from_bytes(entry._data)
                operation.insert(self._dbconn, "room", db_msg.room, 'occupied')
                self._node_volatile_state.set_last_applied(curr_last_applied)

    def do_follower(self):
        if not self.is_follower():
            return

        # if election timeout elapses without receiving AppendEntries RPC from current leader
        # or granting vote to candidate: convert to candidate.
        if self.get_election_timeout_ms() <= 0:
            self.become_candidate()

    def do_candidate(self):
        if not self.is_candidate():
            return

        with self._lock:
            if self._should_step_down:
                LOG.info("stepping down from candidate to follower")
                self._state = Node.STATE_FOLLOWER
                self._should_step_down = False
                return

        # if election timeout elapses: start new election
        if self.get_election_timeout_ms() <= 0:
            self.become_candidate()

    def do_leader(self):
        if not self.is_leader():
            return

        for peer in self._peers:
            threading.Thread(target=self.sync_peer, args=(peer,)).start()

    def sync_peer(self, peer):
        while True:
            start_ms: int = int(time.time() * 1000)
            with self._lock:
                if self._state != Node.STATE_LEADER:
                    LOG.info("node_id:%d sync_peer: no longer leader, stopping", self._node_id)
                    return
                # If last log index ≥ nextIndex for a follower: send
                # AppendEntries RPC with log entries starting at nextIndex
                all_logs: List[Entry] = self._node_persistent_state.get_logs()
                if len(all_logs) == 0:
                    return  # nothing to replicate

                current_term = self._node_persistent_state.get_term()
                commit_idx = self._node_volatile_state.get_commit_idx()
                peer_next_idx: int = self._leader_volatile_state.get_next_idx(peer)
                LOG.debug("sync_peer:%s current_term:%d commit_idx:%d peer_next_idx:%d",
                          peer, current_term, commit_idx, peer_next_idx)
                if len(all_logs) <= peer_next_idx:
                    return False  # peer is up to date as far as we can tell

                # if we get here, need to replicate logs from nextIndex onwards
                # for now, just doing one at a time
                next_log_to_replicate = all_logs[peer_next_idx - 1]
                prev_log_idx = peer_next_idx - 1
                prev_log_term = all_logs[prev_log_idx]._term
                msg: AppendEntriesMessage = AppendEntriesMessage(
                    current_term,
                    self._node_id,
                    prev_log_idx,
                    prev_log_term,
                    commit_idx,
                    next_log_to_replicate,
                )
                _, ok = self._client.send(peer, msg)
                if ok:
                    # If successful: update nextIndex and matchIndex for
                    # follower (§5.3)
                    self._leader_volatile_state.set_next_idx(peer, peer_next_idx + 1)
                    return
                else:
                    # If AppendEntries fails because of log inconsistency:
                    # decrement nextIndex and retry (§5.3)
                    self._leader_volatile_state.set_next_idx(peer, max(0, peer_next_idx - 1))
            elapsed_ms: int = start_ms - int(time.time() * 1000)
            delta = max(0, self._loop_interval_ms - elapsed_ms)
            time.sleep(delta / 1000)

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
            if self._state == Node.STATE_LEADER:
                LOG.warning("node_id:%s is leader but got AppendEntries, stepping down", self._node_id)
                self._state = Node.STATE_FOLLOWER

            # if we get an AppendEntries message, reset election timeout and remember who's the boss
            self._election_timeout_ms = random.randint(self._election_timeout_ms_min, self._election_timeout_ms_max)
            LOG.debug("got AppendEntries msg: election timeout reset: %d", self._election_timeout_ms)

            msg: AppendEntriesMessage = AppendEntriesMessage.from_bytes(bytes_)
            LOG.debug(
                "node_id:%s AppendEntriesMessage term:%d leader_id:%d prev_log_idx:%d prev_log_term:%d " +
                "leader_commit_idx:%d entry:%s",
                self._node_id, msg.term, msg.leader_id, msg.prev_log_idx, msg.prev_log_term, msg.leader_commit_idx,
                msg.entry)
            current_term: int = self._node_persistent_state.get_term()
            # Reply false if term < currentTerm (§5.1)
            if msg.term < self._node_persistent_state.get_term():
                return current_term, False

            # if we have no entry it is just a heartbeat
            if msg.entry is None:
                return current_term, True

            existing_logs: List[Entry] = self._node_persistent_state.get_logs()
            # Reply false if log doesn’t contain an entry at prevLogIndex whose term matches prevLogTerm (§5.3)
            if len(existing_logs) > 0:
                try:
                    existing_entry = existing_logs[msg.prev_log_idx - 1]
                except IndexError:
                    LOG.debug('handle_append_entries: node_id:%d idx:%d out of range', self._node_id,
                              msg.prev_log_idx)
                    return current_term, False

                if existing_entry._term != msg.prev_log_term:
                    # If an existing entry conflicts with a new one (same index but different terms),
                    # delete the existing entry and all that follow it (§5.3)
                    pruned_logs = existing_logs[:msg.prev_log_idx]
                    self._node_persistent_state.set_logs(pruned_logs)
                    LOG.debug('handle_append_entries: node_id:%d did not find existing entry with idx:%d',
                              self._node_id, msg.prev_log_idx)
                    return current_term, False

            last_commit_idx = self._node_persistent_state.append_log(msg.entry)
            self._node_volatile_state.set_commit_idx(min(msg.leader_commit_idx, last_commit_idx))

            return current_term, True

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

            our_last_log_idx, _ = self._node_persistent_state.get_last_log()

            if our_last_log_idx > msg.last_log_idx:
                LOG.debug(
                    "Node handle_request_vote: candidate not up to date: our_last_log_idx:%d log_idx:%s node_id:%s",
                    our_last_log_idx, msg.last_log_idx, msg.candidate_id)
                return current_term, False

            LOG.info("Node handle_request_vote: giving a vote to node_id:%d", msg.candidate_id)
            self._node_persistent_state.set_voted_for(msg.candidate_id)
            return current_term, True

    def handle_database_request(self, bytes_: bytes):
        LOG.debug("Node handle_database_request bytes:%s", bytes_)
        if not self.is_leader():
            # TODO: return the leader ID
            LOG.warning("handle_database_request: not leader")
            return -1, False

        with self._lock:
            # sanity check: we want it to be a valid message before we commit it
            msg: DbEntriesMessage = DbEntriesMessage.from_bytes(bytes_)
            current_term = self._node_persistent_state.get_term()
            new_entry = Entry(current_term, bytes(msg))
            log_idx = self._node_persistent_state.append_log(new_entry)

            append_msg = AppendEntriesMessage(
                self._node_persistent_state.get_term(),
                self._node_id,
                log_idx,
                current_term,
                self._node_volatile_state.get_commit_idx(),
                new_entry,
            )
            acks_required: int = int((len(self._peers) / 2) + 1)
            acks_received: int = 0
            for peer in self._peers:
                peer_term, ok = self._client.send(peer, append_msg)
                # TODO: check peer term to see if we need to step down
                if not ok:
                    LOG.warning("handle_database_request: peer:%s (term:%d) failed to ack AppendEntries msg:%s", peer,
                                peer_term, append_msg)
                else:
                    acks_received += 1

            if acks_required < acks_required:
                LOG.error("handle_database_request: insufficient acks for request %s: got %d, want %d", msg,
                          acks_received, acks_required)
                return 0, False

            return log_idx, True

    def is_leader(self) -> bool:
        with self._lock:
            return self._state == Node.STATE_LEADER

    def become_leader(self) -> bool:
        LOG.debug("node_id:%d becoming leader", self._node_id)
        with self._lock:
            if self._state == Node.STATE_LEADER:
                return False

            self._state = Node.STATE_LEADER
            self._votes = 0
            # reinitialize leader volatile state after an election
            last_log_idx, _ = self._node_persistent_state.get_last_log()
            self._leader_volatile_state = LeaderVolatileState(last_log_idx, self._peers)
            LOG.debug("init leader volatile state: %s", self._leader_volatile_state)

            for peer in self._peers:
                threading.Thread(target=self.heartbeat, args=(peer,)).start()

    def is_candidate(self) -> bool:
        with self._lock:
            return self._state == Node.STATE_CANDIDATE

    def become_candidate(self) -> bool:
        LOG.debug("node_id:%d becoming candidate", self._node_id)
        # On conversion to candidate, start election:
        with self._lock:
            self._state = Node.STATE_CANDIDATE
            # increment currentTerm
            current_term = self._node_persistent_state.increment_term()
            # vote for self
            self._node_persistent_state.set_voted_for(self._node_id)
            # reset election timer
            self._election_timeout_ms = random.randint(self._election_timeout_ms_min, self._election_timeout_ms_max)
            # send RequestVote RPC to all other servers
            logs = self._node_persistent_state.get_logs()
            last_log_idx = max(len(logs) - 1, 0)
            try:
                last_log_term = logs[-1]._term
            except IndexError:
                last_log_term = 0

            for peer in self._peers:
                threading.Thread(target=self.request_vote,
                                 args=(peer, current_term, last_log_idx, last_log_term)).start()
        return True

    def is_follower(self) -> bool:
        with self._lock:
            return self._state == Node.STATE_FOLLOWER

    def become_follower(self) -> bool:
        LOG.debug("node_id:%d becoming follower", self._node_id)
        with self._lock:
            self._state = Node.STATE_FOLLOWER
            return True

    def request_vote(self, peer: Peer, curr_term: int, last_log_idx: int, last_log_term: int):
        msg = VoteMessage(curr_term, self._node_id, last_log_idx, last_log_term)
        while True:
            with self._lock:
                if self._state != Node.STATE_CANDIDATE or self._node_persistent_state.get_term() != curr_term:
                    LOG.info("request_vote: node_id:%d no longer polling for votes in term:%d", self._node_id,
                             curr_term)
                    return
            start = time.time()
            try:
                their_term, got_vote = self._client.send(peer, msg)
                if got_vote is None:
                    # We did not get receive a vote for one of two reasons:
                    # 1) Our logs are out of date, or
                    # 2) Our term is older.
                    # In either case, update our term and become a follower
                    # But first, a sanity check:
                    with self._lock:
                        self._node_persistent_state.set_term(their_term)
                        self._state = Node.STATE_FOLLOWER
                        return

                # cool, we got a vote!
                # make sure we're still a candidate
                with self._lock:
                    if self._state == Node.STATE_CANDIDATE:
                        self._votes += 1
            except Exception as e:
                LOG.error("request_vote: exception requesting vote from peer:%s: %s", peer, e)
            finally:
                if self._votes > len(self._peers) / 2:
                    LOG.debug("node_id:%s won election term:%d", self._node_id, curr_term)
                    self.become_leader()

                elapsed_ms = int(time.time() - start)
                time.sleep((self._loop_interval_ms - elapsed_ms) / 1000)

    def heartbeat(self, peer):
        while True:
            if self._state != Node.STATE_LEADER:
                return

            start = time.time()
            with self._lock:
                current_term = self._node_persistent_state.get_term()
                commit_idx = self._node_volatile_state.get_commit_idx()
                peer_next_idx: int = self._leader_volatile_state.get_next_idx(peer)
                LOG.debug("heartbeat:%s current_term:%d commit_idx:%d peer_next_idx:%d", peer, current_term, commit_idx,
                          peer_next_idx)

            msg: AppendEntriesMessage = AppendEntriesMessage(
                current_term,
                self._node_id,
                peer_next_idx,
                current_term,
                commit_idx,
                None,
            )
            try:
                their_term, ok = self._client.send(peer, msg)
                # If their term is suddenly higher than ours, we may need to relinquish our throne
                if their_term > current_term:
                    LOG.info("peer:%s term (%d) is greater than ours (%d), stepping down as leader",
                             peer, their_term, current_term)
                    self._state = Node.STATE_FOLLOWER
                    self.reset_election_timeout()
            except Exception as e:
                LOG.warning("peer:%s heartbeat exception:%s", peer, e)
            finally:
                elapsed_ms = int(time.time() - start)
                time.sleep((self._loop_interval_ms - elapsed_ms) / 1000)
