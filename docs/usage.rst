=====
Usage
=====

To use natnet in a project::

	import natnet
	client = natnet.Client.connect("192.168.0.106")
	client.set_callback(
	    lambda rigid_bodies, markers, timing: print(rigid_bodies))
	client.spin()

see ``scripts\natnet-client-demo.py`` for a full example.
