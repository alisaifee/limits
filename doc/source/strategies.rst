========================
Rate limiting strategies
========================


Fixed Window
============

This is the most memory efficient strategy to use as it maintains one counter
per resource and rate limit. It does however have its drawbacks as it allows
bursts within each window - thus allowing an 'attacker' to by-pass the limits.
The effects of these bursts can be partially circumvented by enforcing multiple
granularities of windows per resource.

For example, if you specify a ``100/minute`` rate limit on a route, this strategy will
allow 100 hits in the last second of one window and a 100 more in the first
second of the next window. To ensure that such bursts are managed, you could add a second rate limit
of ``2/second`` on the same route.


Fixed Window with Elastic Expiry
================================
.. deprecated:: 4.1

This strategy works almost identically to the Fixed Window strategy with the exception
that each hit results in the extension of the window. This strategy works well for
creating large penalties for breaching a rate limit.

For example, if you specify a ``100/minute`` rate limit on a route and it is being
attacked at the rate of 5 hits per second for 2 minutes - the attacker will be locked
out of the resource for an extra 60 seconds after the last hit. This strategy helps
circumvent bursts.


Moving Window
=============

.. warning:: The moving window strategy is not implemented for the ``memcached``
    and ``etcd`` storage backends.

This strategy is the most effective for preventing bursts from by-passing the
rate limit as the window for each limit is not fixed at the start and end of each time unit
(i.e. N/second for a moving window means N in the last 1000 milliseconds). There is
however a higher memory cost associated with this strategy as it requires ``N`` items to
be maintained in memory per resource and rate limit.


Sliding Window Counter
======================
.. versionadded:: 4.1

.. warning:: The sliding window strategy is not implemented for the
   ``etcd`` storage backend.

This strategy approximates the moving window strategy, with less memory use.
It approximates the behavior of a moving window by maintaining counters for two adjacent
fixed windows: the current and the previous windows.

The current window counter increases at the first hit, and the sampling period begins. Then,
at the end of the sampling period, the window counter and expiration are moved to the
previous window, and new requests will still increase the current window counter.

**To determine if a request should be allowed, we assume the requests in the previous window
were distributed evenly over its duration (eg: if it received 5 requests in 10 seconds,
we consider it has received one request every two seconds).**

Depending on how much time has elapsed since the current window was moved, a weight is applied:

.. math::

    \begin{aligned}
        C_{\text{weighted}} &= \frac{C_{\text{prev}} \times (T_{\text{exp}} - T_{\text{elapsed}})}{T_{\text{exp}}} + C_{\text{current}} \\[10pt]
        \text{where} \quad
        C_{\text{weighted}} &\quad \text{is the weighted count}, \\
        C_{\text{prev}} &\quad \text{is the previous count}, \\
        C_{\text{current}} &\quad \text{is the current count}, \\
        T_{\text{exp}} &\quad \text{is the expiration period}, \\
        T_{\text{elapsed}} &\quad \text{is the time elapsed since shift}.
    \end{aligned}


For example, for a sampling period of 10 seconds and if the window has shifted 2 seconds ago,
the weighted count will be computed as follows:

.. math::

   C_{\text{weighted}} &= \frac{C_{\text{prev}} \times (10 - 2)}{10} + C_{\text{current}} \\[10pt]

Contrary to the moving window strategy, at most two counters per rate limiter are needed,
which dramatically reduces memory usage.

.. warning::

   With some storage implementations, the sampling period doesn't start at the first hit,
   but at a fixed interval like the fixed window, thus allowing an 'attacker' to bypass the limits,
   especially if the counter is very low. This burst is observed only at the first sampling period.
   Eg: with "1 / day", the attacker can send one request at 23:59:59 and another at 00:00:00.
   However, the subsequent requests will be rate-limited once a day, since the previous window is full.

   The following storage implementations are affected: ``memcached`` and ``in-memory``.