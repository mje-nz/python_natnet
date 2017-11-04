# coding: utf-8

# TODO: Estimate skew

import time
import timeit

import natnet
from natnet.protocol import EchoRequestMessage, MessageId, deserialize, serialize


def main():
    client = natnet.Client.connect('192.168.0.106')

    last_server_time = None
    last_synced_at = None
    min_rtt = 1e-3
    echo_count = 0

    try:
        while True:
            sent_timestamp = timeit.default_timer()
            sent_timestamp_int = int(sent_timestamp*1e9)
            request = serialize(EchoRequestMessage(sent_timestamp_int))
            client._conn.send_packet(request)
            response_packet, received_timestamp = client._conn.wait_for_packet_with_id(MessageId.EchoResponse)
            response = deserialize(response_packet)
            assert response.request_timestamp == sent_timestamp_int
            rtt = received_timestamp - sent_timestamp
            server_received_request_timestamp = client._convert_server_timestamp(response.received_timestamp)
            if last_server_time is None:
                last_server_time = server_received_request_timestamp + rtt/2
                last_synced_at = received_timestamp
                print('First echo: RTT {:.2f}ms, server time {:.1f}'.format(1000*rtt, last_server_time))
            else:
                if (rtt - min_rtt) < 0.05e-3:
                    dt = received_timestamp - last_synced_at
                    old_server_time_when_received = last_server_time + dt*(1 - 0.02e-3)
                    last_server_time = server_received_request_timestamp + rtt/2
                    last_synced_at = received_timestamp
                    correction = last_server_time - old_server_time_when_received
                    drift = correction/dt
                    print('Echo {: 5d}: RTT {:.2f}ms (min {:.2f}ms), server time {:.1f}s, dt {: .3f}s, correction {: .3f}ms, drift {: .3f}ms/s'
                          .format(echo_count, 1000*rtt, 1000*min_rtt, last_server_time, dt, 1000*correction, 1000*drift))
                elif received_timestamp - last_synced_at > 10:
                    # Relax accuracy requirement a bit
                    #print('Relaxing min RTT')
                    min_rtt += 0.01e-3
                # else:
                #     server_time_when_received = last_server_time + received_timestamp - last_synced_at
                #     print('Echo {}: RTT {:.1f}ms too long (min {:.1f}ms), server time {:.1f}s'
                #           .format(echo_count, 1000*rtt, 1000*min_rtt, server_time_when_received))

            if rtt < min_rtt:
                min_rtt = rtt
            echo_count += 1
            time.sleep(0.01)
    except (KeyboardInterrupt, SystemExit):
        print('Exiting')


if __name__ == '__main__':
    main()
