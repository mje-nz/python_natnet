# coding: utf-8
"""Integration tests for comms module using Server class."""


import multiprocessing
import time

import pytest

import natnet


class MPServer(natnet.Server):

    def __init__(self, exit_event, *args, **kwargs):
        super(MPServer, self).__init__(*args, **kwargs)
        self.exit_event = exit_event  # type: multiprocessing.Event

    def should_exit(self):
        return self.exit_event.is_set()
    should_exit = property(should_exit, lambda self, e: None)


@pytest.fixture()
def server():
    exit_event = multiprocessing.Event()
    process = multiprocessing.Process(target=lambda: MPServer(exit_event).run(rate=1000))
    process.start()
    time.sleep(0.1)  # Give the server a head start
    yield
    exit_event.set()
    process.join(timeout=1)
    process.terminate()


@pytest.mark.timeout(5)
def test_autodiscovery(server):
    c = natnet.Client.connect(timeout=0.1)
    c.run_once()
