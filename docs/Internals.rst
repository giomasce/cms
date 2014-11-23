Internals
*********

This section contains some details about some CMS internals. They are
mostly meant for developers, not for users. However, if you are curious
about what's under the hood, you will find something interesting here
(though without any pretension of completeness). Moreover, these are
not meant to be full specifications, but only useful notes for the
future.

Oh, I was nearly forgetting: if you are curious about what happens
inside CMS, you may actually be interested in helping us writing
it. We can assure you it is a very rewarding task. After all, if you
are hanging around here, you must have some interest in coding! In
case, feel free `to get in touch with us
<http://cms-dev.github.io/>`_.

RPC protocol
============

Different CMS processes communicate between them by mean of TCP
sockets. Once a service has established a socket with another, it can
write messages on the stream; each message is a JSON-encoded object,
terminated by a ``\r\n`` string (this, of course, means that ``\r\n``
cannot be used in the JSON encoding: this is not a problem, since new
lines inside string represented in the JSON have to be escaped
anyway).

An RPC request must be of the form (it is pretty printed here, but it
is sent in compact form inside CMS)::

  {
    "__method": <name of the requested method>,
    "__data": {
                <name of first arg>: <value of first arg>,
                ...
              },
    "__id": <random ID string>
  }

The arguments in ``__data`` are (of course) not ordered: they have to
be matched according to their names. In particular, this means that
our protocol enables us to use a ``kwargs``-like interface, but not a
``args``-like one. That's not so terrible, anyway.

The ``__id`` is a random string that will be returned in the response,
and it is useful (actually, it's the only way) to match requests with
responses.

The response is of the form::

  {
    "__data": <return value or null>,
    "__error": <null or error string>,
    "__id": <random ID string>
  }

The value of ``__id`` must of course be the same as in the request.
If ``__error`` is not null, then ``__data`` is expected to be null.

Historical notes
----------------

In the past the RPC protocol used to be a bit more powerful, having
the ability of complement the JSON message with a blob of binary
data. This feature has been removed now, both because it was unused
and because its implementation actually has a subtle bug that caused
messages of a specific length to mess around with the ``\r\n``
terminator.

Backdoor
========

Setting the ``backdoor`` configuration key to true causes services to
serve a Python console (accessible with netcat), running in the same
interpreter instance as the service, allowing to inspect and modify its
data, live. It will be bound to a local UNIX domain socket, usually at
:file:`/var/local/run/cms/{service}_{shard}`. Access is granted only to
users belonging to the cmsuser group.
Although there's no authentication mechanism to prevent unauthorized
access, the restrictions on the file should make it safe to run the
backdoor everywhere, even on workers that are used as contestants'
machines.
You can use ``rlwrap`` to add basic readline support. For example, the
following is a complete working connection command:

.. sourcecode:: bash

    rlwrap netcat -U /var/local/run/cms/EvaluationService_0

Substitute ``netcat`` with your implementation (``nc``, ``ncat``, etc.)
if needed.

Test suite
==========

There are a lot of different systems to test that CMS behaves
correctly and new revisions do not introduce
regressions. Unfortunetely the test suite has grown in a rather untidy
manner and is, at the moment, insufficient to handle the complexity of
CMS. So many things are rather experimental and may not work as
intended. Everyone is welcome to fix them!

Many of the tests below are routinely tested against all revisions of
CMS. You can see the results on the `CMS Jenkins instance`_.

.. _CMS Jenkins instance: http://cms.di.unipi.it/jenkins/

Unit tests
----------

Unit tests are meant to test single pieces of CMS (one single service,
one single functionality, ...). They do so by implementing mock
instances of the other components of CMS and making them interacting
with the component that is undergoing testing, checking that it
behaves as expected.

In order to run all the available unit tests, you can execute
``cmstestsuite/RunUnitTests.py``. You can pass command line arguments
to specify which tests you want to run, or to run all the tests that
failed in the previous execution (see the documentation that comes
with ``--help``). The list of failed tests is saved in the file
``.unittestfailers``.

In order to implement a new test, you have to create a new file in
``cmstestsuite/unit_tests`` (or one of its subdirectories). Format it
according to the suggestion in the `documentation of Python unittest
package`_ (you can also use the tests that already exist as models).

.. _documentation of Python unittest package: https://docs.python.org/2/library/unittest.html

Functional tests
----------------

Functional tests are meant to test that CMS works as a whole. That is,
they launch all the services that are meant to intervene in an
ordinary CMS setting and check that everthing is working properly:
they submit programs, wait for the result and check that the grading
was correct. Other kind of tests may be implemented in the future.

In order to run all the available functional tests, you can execute
``cmstestsuite/RunFunctionalTests.py``. As before, you can see
additional options using ``--help``.

At the moment, all the tests are in the form of submissions to certain
tasks, together with definitions of the check that have to be
performed on the scored submission. Single tests are defined in
``cmstestsuite/Tests.py``. Each test is an instance of the class
``Test`` (defined in ``cmstestsuite/Test.py``), characterized by a
name, a task, a filename, a tuple of languages and a list of checks.

The task is chosen between the modules that reside in
``cmstestsuite/tasks``. Have a look at the modules already there in
order to see how to implement a new one. The filename is taken in the
directory ``cmstestsuite/code``; the substring ``%l`` is substituted
with the extension associated to the language that is going to be
tested.

Some checks are already defined in ``cmstestsuite/Test.py`` and are
probably more than enough for all but very unusual situations.

Coverage
--------

When running unit tests of functional tests it is often useful to
check how much of the codebase is actually involved in the tests being
performed. This can be measured with the ``coverage`` Python utility.

Coverage data are gathered when executing tests. In order to produce a
report, you can go through the following steps.

First you should erase past coverage data, which could poison the
report.

.. sourcecode:: bash

    python-converage erase

Then you run either unit or functional tests (new run overwrite
previous coverage data). Then you can generate a text report with

.. sourcecode:: bash

    python-converage report

Or an HTML report with

.. sourcecode:: bash

    python-converage html --include="cms/*" -d coverage_output_dir

Sometimes ``coverage`` complains about missing source code for some
(nonexistent) files. The exact source of this problem has not been
investigated at the moment, but it appears that you can ask
``coverage`` to ignore this error by passing it the ``-i`` option.

Stress testing
--------------

In order to evaluate the performance of CMS in a real environment, it
may be useful to have a tool that simulates many users trying to
submit solutions and accessing random pages of the Contest Web
Server. There are scripts to make something of this kind.

In order to do stress testing, first you have to properly deploy CMS
as usual. Then you run:

.. sourcecode:: bash

    cmstestsuite/StressTest.py -c contest_id -n actor_num -u server_url

This will emulate ``actor_num`` users that start browsing on the
Contest Web Server, logging in and randomly going over the available
pages and downloading task statements. The random behavior of the
users is described by laws and constants that are hardcoded in the
script itself. See for example the variable ``DEFAULT_METRICS`` and
the method ``RandomActor.act()``.

If you do not provide the ``server_url`` argument, the script will try
to guess it on its own (checking the configuration). If you specify
``server_url``, it `must` end with a slash.

The contest ID provided on the command line must coincide with the one
that is served by CWS. It is only used at the beginning to retrieve
the passwords of the users. If the machine (or the machines) you want
to run the stress testing on have no access to the database, you can
previously save of copy of the relevant data in a file using:

.. sourcecode:: bash

    cmstestsuite/StressTest.py -c contest_id -p prepared_info

Then you can copy the file ``prepared_info`` wherever you need it
(beware: there are clear passwords inside!) and use ``-r
prepared_info`` instead of ``-c contest_id`` in the first
``StressTest.py`` command above.

You can also make the stress tester submit some programs. In order to
do that you have to prepare a directory which has a directory for each
task (name after that task). In each of the task directories you have
to put some solutions for that task (at least one for each task). Then
you have to specify the path of the main directory with the option
``-S``. It is not possible to send submissions with more than one file
at the moment.

You can terminate the stress testing with Ctrl-C. A concise summary of
the number of successful and unsuccessful requests and the time to
perform them will be produced to the output. Moreover, additional
details on all the queries will be written in the directory
``test_logs``. For each user and each request performed by that user,
a file will be written with a lot of details, including the whole
content of the request. For each user a symbolic link will point to
last request of each type performed by that user.

Contest replaying
-----------------

TODO

Other utilities
---------------

TestCleanCheckout.py
RunTests.py
