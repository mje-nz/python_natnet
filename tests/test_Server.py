# coding: utf-8
"""Integration tests for comms module using Server class."""


import time

# Use multiprocess instead of multiprocessing to skip hassles around pickling functions
import multiprocess
import pytest

import natnet


class MPServer(natnet.Server):

    def __init__(self, started_event, exit_event, *args, **kwargs):
        super(MPServer, self).__init__(*args, **kwargs)
        self.started_event = started_event  # type: multiprocess.Event
        self.exit_event = exit_event  # type: multiprocess.Event

    def _run(self, *args, **kwargs):
        self.started_event.set()
        super(MPServer, self)._run(*args, **kwargs)

    def should_exit(self):
        return self.exit_event.is_set()
    should_exit = property(should_exit, lambda self, e: None)


@pytest.fixture()
def server():
    started_event = multiprocess.Event()
    exit_event = multiprocess.Event()
    process = multiprocess.Process(target=lambda: MPServer(started_event, exit_event).run(rate=1000))
    process.start()
    started_event.wait()  # Starting processes is really slow on Windows
    time.sleep(0.1)  # Give the server a head start at stdout
    yield
    exit_event.set()
    process.join(timeout=1)
    process.terminate()


@pytest.mark.timeout(5)
def test_autodiscovery(server):
    c = natnet.Client.connect(timeout=1)
    c.run_once()
