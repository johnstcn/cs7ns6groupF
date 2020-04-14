#!/usr/bin/env python
import datetime
import json
import logging
from typing import Optional, List, Dict

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class LeaderVolatileState(object):
    """
    Volatile state on leaders: (Reinitialized after election)
        nextIndex[]: for each server, index of the next log entry to send to that server (initialized to leader last log index + 1)
        matchIndex[]: for each server, index of highest log entry known to be replicated on server (initialized to 0, increases monotonically)
    """

    def __init__(self):
        self._next_idx: Dict[int, int] = {}
        self._match_idx: Dict[int, int] = {}

    def set_next_idx(self, k: int, v: int):
        self._next_idx[k] = v

    def get_next_idx(self, k: int) -> int:
        return self._next_idx[k]

    def set_match_idx(self, k: int, v: int):
        self._match_idx[k] = v

    def get_match_idx(self, k: int) -> int:
        return self._match_idx[k]


class NodeVolatileState(object):
    """
    Volatile state on all servers:
        commitIndex: index of highest log entry known to be committed (initialized to 0, increases monotonically)
    lastApplied: index of highest log entry applied to state machine (initialized to 0, increases monotonically)
    """

    def __init__(self):
        self._commit_idx: int = 0
        self._last_applied: int = 0

    def get_commit_idx(self) -> int:
        return self._commit_idx

    def get_last_applied(self) -> int:
        return self._last_applied

    def set_commit_idx(self, idx: int):
        self._commit_idx = idx

    def set_last_applied(self, idx: int):
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
                term = l['term']
                data = l['data']
                logs.append(Entry(term, data))
            return NodePersistentState(fpath, current_term, voted_for, logs)

    def __init__(self, fpath: str, current_term: int, voted_for: int, logs: List['Entry']):
        self._fpath: str = fpath
        self._current_term: int = current_term
        self._voted_for: int = voted_for
        self._logs: List['Entry'] = logs

    def __str__(self) -> str:
        obj = {
            'current_term': self._current_term,
            'voted_for': self._voted_for,
            'logs': self._logs,
        }
        return json.dumps(obj)

    def get_term(self) -> int:
        return self._current_term

    def increment_term(self):
        self._current_term += 1
        self._save()

    def get_voted_for(self) -> Optional[int]:
        return self._voted_for

    def set_voted_for(self, voted_for=None):
        self._voted_for = voted_for
        self._save()

    def get_logs(self) -> List['Entry']:
        return self._logs

    def append_log(self, log) -> int:
        self._logs.append(log)
        self._save()
        return self._logs.index(log)

    def set_logs(self, logs):
        self._logs = [l for l in logs]
        self._save()

    def _save(self):
        with open(self._fpath, 'w') as f:
            f.write(str(self))


class BookingData(object):
    """
    BookingData represents a room booking to be stored in the Raft log.
    """

    def __init__(self, room_id: int, booking_time: datetime.datetime):
        self._room_id: int = room_id
        self._booking_time: datetime.datetime = booking_time

    def get_room_id(self) -> int:
        return self._room_id

    def get_booking_time(self) -> datetime.datetime:
        return self._booking_time

    @classmethod
    def from_bytes(cls, bytes: bytes):
        room_id_bytes, booking_time_bytes = bytes.split(b' ', maxsplit=2)
        room_id = int(room_id_bytes)
        booking_time = datetime.datetime.utcfromtimestamp(int(booking_time_bytes))
        return BookingData(room_id, booking_time)

    def __str__(self):
        return '%d %d' % (self._room_id, int(self._booking_time.strftime('%s')))


class Entry(object):
    """
    Entry represents a single log entry.
    """

    def __init__(self, term: int, data: BookingData):
        self._term: int = term
        self._data: BookingData = data

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
