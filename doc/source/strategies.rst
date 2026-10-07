========================
Rate Limiting Strategies
========================

TL;DR: How to choose a strategy
===============================

- **Fixed Window:**
  Use when low memory usage and high performance are critical, and occasional bursts
  are acceptable or can be mitigated by additional fine-grained limits.

- **Moving Window:**
  Use when exactly accurate rate limiting is required and extra memory overhead is acceptable.

- **Sliding Window Counter:**
  Use when a balance between memory efficiency and accuracy is needed. This strategy
  smooths transitions between time periods with less overhead than a full moving window,
  though it may trade off some precision near bucket boundaries.

- **Token Bucket:**
  Use when you want to allow short bursts up to a fixed capacity while enforcing a
  steady average rate. Tokens replenish continuously rather than resetting on window
  boundaries, which avoids the edge-of-window bursts of the fixed window.

Fixed Window
============

This strategy is the most memory‑efficient because it uses a single counter per resource and
rate limit. When the first request arrives, a window is started for a fixed duration
(e.g., for a rate limit of 10 requests per minute the window expires in 60 seconds from the first request).
All requests in that window increment the counter and when the window expires, the counter resets.

Burst traffic that bypasses the rate limit may occur at window boundaries.

For example, with a rate limit of 10 requests per minute:

- At **00:00:45**, the first request arrives, starting a window from **00:00:45** to **00:01:45**.
- All requests between **00:00:45** and **00:01:45** count toward the limit.
- If 10 requests occur at any time in that window, any further request before **00:01:45** is rejected.
- At **00:01:45**, the counter resets and a new window starts which would allow 10 requests
  until **00:02:45**.

.. tip::
   To mitigate burstiness (e.g., many requests at window edges), combine limits
   with large windows with finer-granularity ones
   (e.g., combine a 2 requests per second limit with a 10 requests per minute limit).


Moving Window
=============

This strategy adds each request’s timestamp to a log if the ``nth`` oldest entry (where ``n``
is the limit) is either not present or is older than the duration of the window (for example with a rate limit of
``10 requests per minute`` if there are either less than 10 entries or the 10th oldest entry is at least
60 seconds old). Upon adding a new entry to the log "expired" entries are truncated.

For example, with a rate limit of 10 requests per minute:

- At **00:00:10**, a client sends 1 requests which are allowed.
- At **00:00:20**, a client sends 2 requests which are allowed.
- At **00:00:30**, the client sends 4 requests which are allowed.
- At **00:00:50**, the client sends 3 requests which are allowed (total = 10).
- At **00:01:11**, the client sends 1 request. The strategy checks the timestamp of the
  10th oldest entry (**00:00:10**) which is now 61 seconds old and thus expired. The request
  is allowed.
- At **00:01:12**, the client sends 1 request. The 10th oldest entry's timestamp is **00:00:20**
  which is only 52 seconds old. The request is rejected.

Sliding Window Counter
=======================
.. versionadded:: 4.1

This strategy approximates the moving window while using less memory by maintaining
two counters:

- **Current bucket:** counts requests in the ongoing period.
- **Previous bucket:** counts requests in the immediately preceding period.

A weighted sum of these counters is computed based on the elapsed time in the current
bucket. The weighted count is defined as:

.. math::

    C_{\text{weighted}} = \left\lfloor C_{\text{current}} +
    \left(C_{\text{prev}} \times w\right) \right\rfloor

and the weight factor :math:`w` is calculated as:

.. math::

    w = \frac{T_{\text{exp}} - T_{\text{elapsed}}}{T_{\text{exp}}}

Where:

- :math:`T_{\text{exp}}` is the bucket duration.
- :math:`T_{\text{elapsed}}` is the time elapsed since the bucket shifted.
- :math:`C_{\text{prev}}` is the previous bucket's count.
- :math:`C_{\text{current}}` is the current bucket's count.


For example, with a rate limit of ``100 requests per minute``

Suppose:

- Current bucket has 80 hits (:math:`C_{\text{current}}`)
- Previous bucket has 40 hits (:math:`C_{\text{prev}}`)

- If the bucket shifted 30 seconds ago (:math:`T_{\text{elapsed}} = 30`).

  .. math::

    w = \frac{60 - 30}{60} = 0.5

  .. math::

    C_{\text{weighted}} = \left\lfloor 80 + (0.5 \times 40) \right\rfloor = 100

  Since the effective count equals the limit, a new request is rejected.

- If the bucket shifted 40 seconds ago (:math:`T_{\text{elapsed}} = 40`).

  .. math::

    w = \frac{60 - 40}{60} \approx 0.33

  .. math::

    C_{\text{weighted}} = \left\lfloor 80 + (0.33 \times 40) \right\rfloor = 93

  Since the effective count is below the limit, a new request is allowed.

.. note::
   Some storage implementations use fixed bucket boundaries (e.g., aligning buckets with
   clock intervals), while others adjust buckets dynamically based on the first hit.
   This difference can allow an attacker to bypass limits during the initial sampling
   period. The affected implementations are ``memcached`` and ``in-memory``.


Token Bucket
============
.. versionadded:: 5.9

This strategy models each resource as a bucket that holds up to ``limit`` tokens and
refills continuously at ``limit / expiry`` tokens per second. Each request removes
``cost`` tokens; if fewer than ``cost`` tokens are available the request is rejected and
no tokens are removed. Because tokens accrue continuously rather than resetting on a
fixed boundary, the bucket permits bursts up to its capacity while holding the long-run
average to the configured rate.

A bucket starts full, so the first ``limit`` requests are allowed immediately. After the
bucket empties it refills gradually: with a rate limit of ``10 requests per minute`` a
token becomes available roughly every 6 seconds.

For example, with a rate limit of ``10 requests per minute`` (capacity 10, refill
≈ 0.167 tokens/second):

- At **00:00:00**, a burst of 10 requests drains the full bucket. All are allowed.
- At **00:00:01**, an 11th request arrives. Only ~0.167 tokens have refilled, so it is
  rejected without consuming anything.
- At **00:00:30**, ~5 tokens have refilled, so up to 5 requests are allowed before the
  bucket is empty again.
- At **00:01:00**, the bucket has refilled to its capacity of 10 (never more).

.. note::
   The token bucket requires a storage backend that can atomically refill and consume
   the bucket (:class:`~limits.storage.base.TokenBucketSupport`). It is supported by the
   in-memory, redis (including redis cluster, sentinel and valkey) and mongodb storages.
   ``memcached`` does not support it, and instantiating
   :class:`~limits.strategies.TokenBucketRateLimiter` with an unsupported storage raises
   :exc:`NotImplementedError`.



