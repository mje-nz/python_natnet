These applications are intended largely as examples.
`natnet-client-demo.py` connects to an instance of Motive and prints out
the rigid bodies and markers in each frame.  `natnet-client-demo-ros.py`
is a poorly-packaged equivalent ROS node.  The Dockerfile describes a
ROS Kinetic environment sufficient for testing the ROS node.

Both applications take one command-line argument: either the IP of the
Motive instance to connect to, or "fake" to use test data instead.
