#!/usr/bin/env python
import json
import logging
import threading
from typing import Optional, List

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class LeaderVolatileState(object):
    """
    Volatile state on leaders: (Reinitialized after election)
        nextIndex[]: for each server, index of the next log entry to send to that server (initialized to leader last log index + 1)
        matchIndex[]: for each server, index of highest log entry known to be replicated on server (initialized to 0, increases monotonically)
    """

    def __init__(self):
        self._next_idx = {}
        self._match_idx = {}
        self._lock = threading.Lock()

    def set_next_idx(self, k, v):
        with self._lock:
            self._next_idx[k] = v

    def get_next_idx(self, k):
        with self._lock:
            return self._next_idx[k]

    def set_match_idx(self, k, v):
        with self._lock:
            self._match_idx[k] = v

    def get_match_idx(self, k):
        with self._lock:
            return self._match_idx[k]


class NodeVolatileState(object):
    """
    Volatile state on all servers:
        commitIndex: index of highest log entry known to be committed (initialized to 0, increases monotonically)
    lastApplied: index of highest log entry applied to state machine (initialized to 0, increases monotonically)
    """

    def __init__(self):
        self._commit_idx = 0
        self._last_applied = 0
        self._lock = threading.Lock()

    def get_commit_idx(self):
        with self._lock:
            return self._commit_idx

    def get_last_applied(self):
        with self._lock:
            return self._last_applied

    def set_commit_idx(self, idx):
        with self._lock:
            self._commit_idx = idx

    def set_last_applied(self, idx):
        with self._lock:
            self._last_applied = idx


class NodePersistentState(object):
    """
    Persistent state on all servers: (Updated on stable storage before responding to RPCs)
        currentTerm:  latest term server has seen (initialized to 0 on first boot, increases monotonically)
        votedFor:  candidateId that received vote in current term (or null if none)
        log[]:  log entries; each entry contains command for state machine, and term when entry was received by leader (first index is 1)
    """

    @classmethod
    def load(cls, fpath):
        """
        load persistent state from a file
        :param fpath: path of state. Created if it does not already exist.
        """
        with open(fpath, 'r') as f:
            json_str = f.read()
            json_obj = json.loads(json_str)
            current_term = json_obj.get('current_term', 0)
            voted_for = json_obj.get('voted_for', None)
            logs = []
            for l in json_obj.get('logs', []):
                idx = l['idx']
                term = l['term']
                data = l['data']
                logs.append(Entry(idx, term, data))
            return NodePersistentState(fpath, current_term, voted_for, logs)

    def __init__(self, fpath, current_term, voted_for, logs):
        self._fpath = fpath
        self._current_term = current_term
        self._voted_for = voted_for
        self._logs = logs
        self._lock = threading.Lock()

    def __str__(self):
        with self._lock:
            obj = {
                'current_term': self._current_term,
                'voted_for': self._voted_for,
                'logs': self._logs,
            }
            return json.dumps(obj)

    def get_term(self) -> int:
        with self._lock:
            return self._current_term

    def increment_term(self):
        with self._lock:
            self._current_term += 1
            self._save()

    def get_voted_for(self) -> Optional[int]:
        with self._lock:
            return self._voted_for

    def set_voted_for(self, voted_for=None):
        with self._lock:
            self._voted_for = voted_for
            self._save()

    def get_logs(self) -> List['Entry']:
        with self._lock:
            return self._logs

    def append_log(self, log) -> int:
        with self._lock:
            self._logs.append(log)
            self._save()
            return self._logs.index(log)

    def set_logs(self, logs):
        with self._lock:
            self._logs = [l for l in logs]
            self._save()

    def _save(self):
        with self._lock:
            with open(self._fpath, 'w') as f:
                f.write(str(self))


class Entry(object):
    """
    Entry represents a single log entry.
    """

    def __init__(self, term, data):
        self._term = term
        self._data = data

    def __str__(self) -> str:
        d = {
            'term': self._term,
            'data': self._data,
        }
        return json.dumps(d)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Entry):
            return False
        return (self._term == o._term) and (self._data == o._data)
