========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - tests
      - | |travis| |appveyor| |codecov|

.. |travis| image:: https://travis-ci.org/mje-nz/python-natnet.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/mje-nz/python-natnet

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/mje-nz/python-natnet?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/mje-nz/python-natnet

.. |codecov| image:: https://codecov.io/github/mje-nz/python-natnet/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/mje-nz/python-natnet

.. end-badges

NatNet 3 client

* Free software: BSD 3-Clause License


Installation
============

For now, use::

    python setup.py install

to build and install the package, or::

    python setup.py develop

to install in "development mode" i.e. to install symlinks.


Development
===========
Install Python 2.7 and 3.6, git, and pip3 install tox.  On Windows you'll have to manually git to your PATH,
and it's probably best to add at least one Python (tox will use the "py" launcher to find your installed Pythons, but if
you want to be able to run "python27", "pip3" etc on the command line you'll have to set that up yourself).  On Windows,
Gow makes the command line a bit less painful.

To run the checks and tests run::

    tox

To run the most important checks and tests automatically before you commit, run::

    ln -s $(pwd)/pre-commit-hook .git/hooks/pre-commit

