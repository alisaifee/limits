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
    storage backend.

This strategy is the most effective for preventing bursts from by-passing the
rate limit as the window for each limit is not fixed at the start and end of each time unit
(i.e. N/second for a moving window means N in the last 1000 milliseconds). There is
however a higher memory cost associated with this strategy as it requires ``N`` items to
be maintained in memory per resource and rate limit.

Token Bucket
=============

The token bucket strategy allows bursts of traffic up to a fixed capacity,
while refilling the bucket at a steady rate over time.

For example, with a rate limit of 10 tokens with 1 token per second refill:

- Allow 10 requests at once if the bucket is full
- Refill the bucket with 1 token every second
- If the bucket is empty, further requests will be rejected until more tokens are available