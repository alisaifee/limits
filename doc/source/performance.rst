===========
Performance
===========

The performance of each rate-limiting strategy and storage backend
differs in both throughput and storage cost characteristics.

Performance by storage and strategy
===================================
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
======================================

For :ref:`strategies:fixed window` and :ref:`strategies:sliding window counter` both the
storage cost and performance of operations remains mostly constant when the limit window and size
varies. This is not always true for :ref:`strategies:moving window` which maintains a complete log of successful
requests within the rate limit window.  This has both a cost and computation implication depending
on the limit size and load.

.. dropdown:: Benchmark parameters

  - 100 unique virtual users
  - Rate limits of

    - ``500/minute``
    - ``10000/day``
    - ``100000/day``
  - Each virtual user's limit was pre-seeded to be:

    - 5% full.
    - 50% full.
    - 95% full.

  See :ref:`performance:benchmark run details` for information on the benchmarking
  environment.

.. tab:: Fixed Window

       .. tab::  Hit

          Performance of :meth:`limits.strategies.FixedWindowRateLimiter.hit`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Fixed Window (hit)
             :source: benchmark-summary
             :query: group=hit,strategy=fixed-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false

       .. tab:: Test

          Performance of :meth:`limits.strategies.FixedWindowRateLimiter.test`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.


          .. benchmark-chart::
             :title: Fixed Window (test)
             :source: benchmark-summary
             :query: group=test,strategy=fixed-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false


       .. tab:: Get Window Stats

          Performance of :meth:`limits.strategies.FixedWindowRateLimiter.get_window_stats`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Fixed Window (test)
             :source: benchmark-summary
             :query: group=get-window-stats,strategy=fixed-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false

.. tab:: Sliding Window Counter

       .. tab::  Hit

          Performance of :meth:`limits.strategies.SlidingWindowCounterRateLimiter.hit`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Sliding Window Counter (hit)
             :source: benchmark-summary
             :query: group=hit,strategy=sliding-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false

       .. tab:: Test

          Performance of :meth:`limits.strategies.SlidingWindowCounterRateLimiter.test`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.


          .. benchmark-chart::
             :title: Sliding Window Counter (test)
             :source: benchmark-summary
             :query: group=test,strategy=sliding-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false


       .. tab:: Get Window Stats

          Performance of :meth:`limits.strategies.SlidingWindowCounterRateLimiter.get_window_stats`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Sliding Window Counter (get_window_stats)
             :source: benchmark-summary
             :query: group=get-window-stats,strategy=sliding-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false

.. tab:: Moving Window

       .. tab::  Hit

          Performance of :meth:`limits.strategies.MovingWindowRateLimiter.hit`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Moving Window (hit)
             :source: benchmark-summary
             :query: group=hit,strategy=moving-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false

       .. tab:: Test

          Performance of :meth:`limits.strategies.MovingWindowRateLimiter.test`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.


          .. benchmark-chart::
             :title: Moving Window (test)
             :source: benchmark-summary
             :query: group=test,strategy=moving-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false


       .. tab:: Get Window Stats

          Performance of :meth:`limits.strategies.MovingWindowRateLimiter.get_window_stats`
          with different rate limits and storages and with each rate limit
          pre-seeded to different percentages to show the implications of limit size.

          .. benchmark-chart::
             :title: Moving Window (get_window_stats)
             :source: benchmark-summary
             :query: group=get-window-stats,strategy=moving-window
             :sort: strategy,storage_type,limit
             :filters: percentage_full=95,storage_type=,limit=,async=false


Benchmark run details
=====================
.. benchmark-details::
   :source: benchmark-summary