# coding: utf-8

import natnet


def main(server_name):
    def callback(rigid_bodies, markers, timing):
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
                print('\t Model {} marker {}: ({: 5.2f}, {: 5.2f}, {: 5.2f})'.format(
                    m.model_id, m.marker_id, *m.position
                ))
        print('\t Latency: {:.1f}ms (system {:.1f}ms, transit {:.1f}ms, processing {:.2f}ms)'.format(
            1000*timing.latency, 1000*timing.system_latency, 1000*timing.transit_latency,
            1000*timing.processing_latency
        ))

    if server_name == 'fake':
        client = natnet.fakes.FakeClient.fake_connect()
    else:
        client = natnet.Client.connect(server_name)
    client.set_callback(callback)
    client.spin()


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
