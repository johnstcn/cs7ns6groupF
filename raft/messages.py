#!/usr/bin/env python
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


class VoteMessage(object):
    """
    Invoked by candidates to gather votes (§5.2).
    :param term: candidate's term
    :param candidate_id: candidate requesting vote
    :param last_log_idx: index of candidate's last log entry
    :param last_log_term: term of candidate's last log entry
    :return: (current_term, vote_granted): current term for candidate to update itself
            and whether the candidate was granted a vote or not
    """

    def __init__(self, term, candidate_id, last_log_idx, last_log_term):
        self.term = term
        self.candidate_id = candidate_id
        self.last_log_idx = last_log_idx
        self.last_log_term = last_log_term

    def __bytes__(self):
        return b'vote %s %s %s %s' % (self.term, self.candidate_id, self.last_log_idx, self.last_log_term)

    @classmethod
    def from_bytes(cls, bytes_: bytes):
        bytes_ = bytes_.lstrip(b'vote ')
        parts = bytes_.split(b' ')
        assert len(parts) == 4, 'VoteMessage.from_bytes expected 4 parts after stripping leading vote but got %d' % len(
            parts)
        term = int(parts.pop(0))
        candidate_id = int(parts.pop(0))
        last_log_idx = int(parts.pop(0))
        last_log_term = int(parts.pop(0))
        return VoteMessage(term, candidate_id, last_log_idx, last_log_term)


class AppendEntriesMessage(object):
    """
    Invoked by leader to replicate log entries (§5.3); also used as heartbeat (§5.2).
    :param term: leader's term
    :param leader_id: so follower can redirect clients
    :param prev_log_idx: index of log entry immediately preceding new ones
    :param prev_log_term: term of prev_log_idx entry
    :param leader_commit_idx: leader commit index
    :param entry: log entry to store. May be None for heartbeat. TODO: support multiple entries at once.
    :return: term, success: current term, for leader to update itself, success true if follower contained entry
            matching prev_log_idx and prev_log_term
    """

    def __init__(self, term: int, leader_id: int, prev_log_idx: int, prev_log_term: int, leader_commit_idx: int,
                 entry):
        self.term = term
        self.leader_id = leader_id
        self.prev_log_idx = prev_log_idx
        self.prev_log_term = prev_log_term
        self.leader_commit_idx = leader_commit_idx
        self.entry = entry

    def __bytes__(self):
        return b'append %s %s %s %s %s %s' % (
            self.term, self.leader_id, self.prev_log_idx, self.prev_log_term, self.leader_commit_idx, self.entry)

    @classmethod
    def from_bytes(cls, bytes_: bytes):
        bytes_ = bytes_.lstrip(b'append ')
        parts = bytes_.split(b' ', maxsplit=6)  # entry may contain spaces
        assert len(parts) in [5,
                              6], 'AppendEntriesMessage.from_bytes expected either 5 or 6 parts after stripping leading' \
                                  '"vote" but got %d' % len(parts)
        term = int(parts.pop(0))
        leader_id = int(parts.pop(0))
        prev_log_idx = int(parts.pop(0))
        prev_log_term = int(parts.pop(0))
        leader_commit_idx = int(parts.pop(0))
        try:
            entry = parts.pop(0)
        except IndexError:
            entry = b''
        return AppendEntriesMessage(term, leader_id, prev_log_idx, prev_log_term, leader_commit_idx, entry)