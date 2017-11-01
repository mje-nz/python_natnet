# coding: utf-8

from __future__ import print_function

import rospy
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion

import natnet


def main(server_name):
    rospy.init_node('mocap')
    pub = rospy.Publisher('~/pose', PoseStamped, queue_size=10)

    def callback(rigid_bodies, markers, timing):
        """

        :type rigid_bodies: list[RigidBody]
        :type markers: list[LabelledMarker]
        :type timing: TimestampAndLatency
        """
        print()
        print('{:.1f}s: Received mocap frame'.format(timing.timestamp))
        if len(rigid_bodies) > 0:
            body = rigid_bodies[0]
            message = PoseStamped()
            message.header.frame_id = 'mocap'
            message.header.stamp = rospy.Time(timing.timestamp)
            message.pose.position = Point(*body.position)
            message.pose.orientation = Quaternion(*body.orientation)
            print('Publishing', message)
            pub.publish(message)

    if server_name == 'fake':
        client = natnet.fakes.FakeClient.fake_connect()
    else:
        client = natnet.Client.connect(server_name)
    client.set_callback(callback)
    client.spin()


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
