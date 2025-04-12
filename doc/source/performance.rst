Performance
===========

The performance of each rate-limiting strategy and storage backend
differs in both throughput and storage cost characteristics.

Performance by storage and strategy
-----------------------------------
Below you will find benchmarks for each strategy and storage giving
a high level overview of the performance.


.. dropdown:: Benchmark parameters

   - 100 unique virtual users (i.e. unique rate limit keys)
   - A rate limit of ``500/minute``
   - Each virtual user's limit was pre-seeded to be 50% full.

   See :ref:`performance:benchmark run details` for information on the benchmarking
   environment.

.. tab-set::

    .. tab-item:: Hit

       Performance of :meth:`~limits.strategies.RateLimiter.hit`
       by storage & strategy.

       .. benchmark-chart::
          :source: benchmark-summary
          :query: limit=500 per 1 minute,group=hit,percentage_full=50
          :sort: storage_type,strategy
          :filters: storage_type=,strategy=,async=false


    .. tab-item:: Test

       Performance of :meth:`~limits.strategies.RateLimiter.test`
       by storage & strategy.

       .. benchmark-chart::
          :source: benchmark-summary
          :query: limit=500 per 1 minute,group=test,percentage_full=50
          :sort: storage_type,strategy
          :filters: storage_type=,strategy=,async=false

    .. tab-item:: Get Window Stats

       Performance of :meth:`~limits.strategies.RateLimiter.get_window_stats`
       by storage & strategy.

       .. benchmark-chart::
          :source: benchmark-summary
          :query: limit=500 per 1 minute,group=get-window-stats,percentage_full=50
          :sort: storage_type,strategy
          :filters: storage_type=,strategy=,async=false


Performance implication of limit sizes
--------------------------------------

Though for :ref:`strategies:fixed window` and :ref:`strategies:sliding window counter` both the
storage cost and performance of operations remains constant when the limit window and size varies,
this is not true for :ref:`strategies:moving window` which maintains a complete log of successful
requests within the window.

The following benchmarks demonstrate the implications when using various limits.

.. dropdown:: Benchmark parameters

  - 100 unique virtual users
  - Rate limits of

    - ``500/minute``
    - ``10000/day``
    - ``100000/day``
  - Each virtual user's limit was pre-seeded to be:

    - 5% full.
    - 50% full.
    - 90% full.

  See :ref:`performance:benchmark run details` for information on the benchmarking
  environment.

.. tab-set::

   .. tab-item::  Hit

      Performance of :meth:`~limits.strategies.RateLimiter.hit`
      with various rate limits

      .. benchmark-chart::
         :source: benchmark-summary
         :query: group=hit
         :sort: storage_type,limit
         :filters: strategy=,percentage_full=50,storage_type=,async=false

   .. tab-item:: Test

      Performance of :meth:`~limits.strategies.RateLimiter.test`
      with various rate limits

      .. benchmark-chart::
         :source: benchmark-summary
         :query: group=test
         :sort: storage_type,limit
         :filters: strategy=,percentage_full=50,storage_type=,async=false


   .. tab-item:: Get Window Stats

      Performance of :meth:`~limits.strategies.RateLimiter.get_window_stats`
      with various rate limits

      .. benchmark-chart::
         :source: benchmark-summary
         :query: group=get-window-stats
         :sort: storage_type,limit
         :filters: strategy=,percentage_full=50,storage_type=,async=false


Benchmark run details
---------------------
.. benchmark-details::
   :source: benchmark-summary