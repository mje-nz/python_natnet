# coding: utf-8
"""In fake mode, the timeout is used as the delay between publishing packets.  This is convenient
for profiling.  In IPython, use this command to profile packet deserialisation:
    %run -p scripts/natnet-client-demo.py fake 0 True
"""

import attr

import natnet

@attr.s
class ClientApp(object):

    _client = attr.ib()
    _timeout = attr.ib()
    _quiet = attr.ib()

    @classmethod
    def connect(cls, server_name, timeout, quiet):
        if server_name == 'fake':
            client = natnet.fakes.FakeClient.fake_connect()
        else:
            client = natnet.Client.connect(server_name)
        return cls(client, timeout, quiet)

    def run(self):
        if self._quiet:
            self._client.set_callback(self.callback_quiet)
        else:
            self._client.set_callback(self.callback)
        self._client.spin(self._timeout)

    def callback(self, rigid_bodies, markers, timing):
        """

        :type rigid_bodies: list[RigidBody]
        :type markers: list[LabelledMarker]
        :type timing: TimestampAndLatency
        """
        print()
        print('{:.1f}s: Received mocap frame'.format(timing.timestamp))
        if rigid_bodies:
            print('Rigid bodies:')
            for b in rigid_bodies:
                print('\t Id {}: ({: 5.2f}, {: 5.2f}, {: 5.2f}), ({: 5.2f}, {: 5.2f}, {: 5.2f}, {: 5.2f})'.format(
                    b.id_, *(b.position + b.orientation)
                ))
        if markers:
            print('Markers')
            for m in markers:
                print('\t Model {} marker {}: size {:.4f}mm, pos ({: 5.2f}, {: 5.2f}, {: 5.2f}), '.format(
                    m.model_id, m.marker_id, 1000*m.size, *m.position
                ))
        print('\t Latency: {:.1f}ms (system {:.1f}ms, transit {:.1f}ms, processing {:.2f}ms)'.format(
            1000*timing.latency, 1000*timing.system_latency, 1000*timing.transit_latency,
            1000*timing.processing_latency
        ))

    def callback_quiet(self, *args):
        print('.')


def main(server_name, timeout=0.1, quiet=False):
    timeout = float(timeout)
    if timeout == 0:
        timeout = None
    app = ClientApp.connect(server_name, timeout, bool(quiet))
    app.run()


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
