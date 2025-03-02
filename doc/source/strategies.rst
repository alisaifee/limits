========================
Rate Limiting Strategies
========================

Fixed Window
============

This strategy is memory‑efficient because it uses a single counter per resource and
rate limit. When the first request arrives, a window is started for a fixed duration
(e.g., 100 requests per minute). All requests within that window increment the same
counter; when the window expires, the counter resets.

.. admonition:: Pros
   :class: important

   - Memory‑efficient.
   - Simple to implement.

.. admonition:: Cons
   :class: caution

   - Susceptible to burst traffic at window boundaries (see example below).

Example
-------

With a rate limit of `100 request per minute`

- At 12:00:45, the first request arrives, starting a window from 12:00:45 to
  12:01:45.
- All requests in this window increment the counter.
- Only 99 more requests will be allowed until 12:01:45
- At 12:01:45, the counter resets and a new window starts.

.. tip::
   To mitigate burstiness (e.g., many requests at window edges), combine this
   strategy with a finer‑granularity limit (e.g., 2 requests per second).



Fixed Window with Elastic Expiry
==================================
.. deprecated:: 4.1

This variant extends the window’s expiry with each hit by resetting the timer on
every request. Although designed to impose larger penalties for breaches, it is now
deprecated and should not be used.



Moving Window
=============

In the moving window strategy, each request’s timestamp is recorded. When a new
request arrives, the system counts only those timestamps within a fixed duration
(e.g., the previous 60 seconds). This creates a continuously sliding window that
enforces limits based on recent activity.

.. admonition:: Pros
   :class: important

   - Provides accurate, time-based rate limiting by counting only recent requests.
   - Continuously removes expired timestamps to prevent bursts.

.. admonition:: Cons
   :class: caution

   - Requires storing every timestamp, increasing memory usage.
   - Incurs extra computation to evaluate the rolling window.
   - Some backends do not support this natively.

Example
-------

With a rate limit of `100 request per minute`

- A client sends 100 requests between 12:00:10 and 12:00:50.
- At 12:01:00, the system counts only requests after 12:00:00 (i.e., within the last 60
  seconds).
- If the earliest request (e.g., at 12:00:10) has expired, fewer than 100 requests
  remain and the new request is allowed.



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

.. admonition:: Pros
   :class: important

   - Utilizes only two counters per limit
   - Smooths transitions between buckets to reduce burst effects.

.. admonition:: Cons
   :class: caution

   - May be less precise near bucket boundaries.

Example
-------

With a rate limit of `100 request per minute`

Suppose:

- Current bucket (:math:`C_{\text{current}}`) has 80 hits.
- Previous bucket (:math:`C_{\text{prev}}`) has 40 hits.

Scenario 1
~~~~~~~~~~

The bucket shifted 30 seconds ago (:math:`T_{\text{elapsed}} = 30`).

- Weight factor:

  .. math::

      w = \frac{60 - 30}{60} = 0.5

- Weighted count:

  .. math::

      C_{\text{weighted}} = \left\lfloor 80 + (0.5 \times 40) \right\rfloor = 100

Since the effective count equals the limit, a new request is rejected.

Scenario 2
~~~~~~~~~~

The bucket shifted 40 seconds ago (:math:`T_{\text{elapsed}} = 40`).

- Weight factor:

  .. math::

      w = \frac{60 - 40}{60} \approx 0.33

- Weighted count:

  .. math::

      C_{\text{weighted}} = \left\lfloor 80 + (0.33 \times 40) \right\rfloor = 93

Since the effective count is below the limit, a new request is allowed.

.. note::
   Some storage implementations use fixed bucket boundaries (e.g., aligning buckets with
   clock intervals), while others adjust buckets dynamically based on the first hit.
   This difference can allow an attacker to bypass limits during the initial sampling
   period. Affected implementations include ``memcached`` and ``in-memory``.



How to choose a strategy
========================

- **Fixed Window:**
  Use when low memory usage and high performance are critical, and occasional bursts
  are acceptable or can be mitigated by additional fine-grained limits.

- **Moving Window:**
  Use when exactly accurate rate limiting is required and extra memory overhead is acceptable.

- **Sliding Window Counter:**
  Use when a balance between memory efficiency and accuracy is needed. This strategy
  smooths transitions between time periods with less overhead than a full moving window,
  though it may trade off some precision near bucket boundaries.
