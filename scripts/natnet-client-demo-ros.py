# coding: utf-8
"""Natnet client ROS node.

Note that this node does not convert Motive's poses from y-up to z-up. You can do so with:
    rosrun tf static_transform_publisher 0 0 0 0 0 1.57079632679 mocap mocap_motive 100
"""

from __future__ import print_function

import rospy
from geometry_msgs.msg import Point, PointStamped, Pose, PoseStamped, Quaternion, Vector3
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker

import natnet
import natnet.protocol.MocapFrameMessage


MOCAP_FRAME = 'mocap_motive'


def main(server_name):
    rospy.init_node('mocap')
    rigid_body_pubs = []
    marker_vis_pub = [rospy.Publisher('~/markers/vis', Marker, queue_size=10)]
    marker_pubs = {}

    def callback(rigid_bodies, markers, timing):
        """

        :type rigid_bodies: list[RigidBody]
        :type markers: list[LabelledMarker]
        :type timing: TimestampAndLatency
        """
        print()
        print('{:.1f}s: Received mocap frame'.format(timing.timestamp))

        if rigid_bodies:
            # Publish ~/rigid_bodies/i/pose topics
            for i, b in enumerate(rigid_bodies):
                if i >= len(rigid_body_pubs):
                    pub = rospy.Publisher('~/rigid_bodies/{}/pose'.format(i), PoseStamped, queue_size=10)
                    rigid_body_pubs.append(pub)
                message = PoseStamped()
                message.header.frame_id = MOCAP_FRAME
                message.header.stamp = rospy.Time(timing.timestamp)
                message.pose.position = Point(*b.position)
                message.pose.orientation = Quaternion(*b.orientation)
                rigid_body_pubs[i].publish(message)
        if markers:
            # Publish ~/markers/vis topic
            message = Marker()
            message.header.frame_id = MOCAP_FRAME
            message.header.stamp = rospy.Time(timing.timestamp)
            message.ns = 'python-natnet'
            message.id = 0
            message.type = Marker.SPHERE_LIST
            positions = [Point(*m.position) for m in markers]
            message.points = positions
            sizes = [m.size for m in markers]
            mean_size = sum(sizes)/len(sizes)
            message.scale = Vector3(mean_size, mean_size, mean_size)
            message.color = ColorRGBA(1, 1, 1, 1)
            marker_vis_pub[0].publish(message)
            for m in markers:
                if m.model_id == 0:
                    # For markers which are not part of a rigid body, publish ~/markers/i topic
                    try:
                        pub = marker_pubs[m.marker_id]
                    except KeyError:
                        pub = rospy.Publisher('~/markers/{}'.format(m.marker_id), PointStamped, queue_size=10)
                        marker_pubs[m.marker_id] = pub
                    message = PointStamped()
                    message.header.frame_id = MOCAP_FRAME
                    message.header.stamp = rospy.Time(timing.timestamp)
                    message.point = Point(*m.position)
                    pub.publish(message)

    if server_name == 'fake':
        client = natnet.fakes.FakeClient.fake_connect()
    else:
        client = natnet.Client.connect(server_name)
    client.set_callback(callback)
    client.spin()
    # TODO: Handle ROS shutdown properly


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
