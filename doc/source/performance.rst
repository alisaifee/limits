Performance
===========

The performance of each rate-limiting strategy and storage backend
differs in both throughput and storage cost characteristics.

Performance by storage and strategy
-----------------------------------
Below you will find benchmarks for each strategy and storage when using
a rate limit of ``500/minute``. (For details about the benchmarking environment
please refer to :ref:`performance:benchmark run details`).


.. tab:: Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=hit,percentage_full=0.5
       :sort: storage_type,strategy
       :filters: storage_type=,async=false

.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=test,percentage_full=0.5
       :sort: storage_type,strategy
       :filters: storage_type=,async=false


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=get-window-stats,percentage_full=0.5
       :sort: storage_type,strategy
       :filters: storage_type=,async=false



Performance implication of limit sizes
--------------------------------------

Though for :ref:`strategies:fixed window` and :ref:`strategies:sliding window counter` both the
storage cost and performance of operations remains constant when the limit window and size varies,
this is not true for :ref:`strategies:moving window` which maintains a complete log of successful
requests within the window.

The following benchmarks demonstrate the implications when using various limits.

Fixed Window
~~~~~~~~~~~~

.. tab::  Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=hit,strategy=fixed-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false

.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=test,strategy=fixed-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=get-window-stats,strategy=fixed-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false

Moving Window
~~~~~~~~~~~~~

.. tab:: Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=hit,strategy=moving-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false



.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=test,strategy=moving-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=get-window-stats,strategy=moving-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false


Sliding Window
~~~~~~~~~~~~~~

.. tab:: Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=hit,strategy=sliding-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=true

.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=test,strategy=sliding-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false

.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: group=get-window-stats,strategy=sliding-window
       :sort: storage_type,limit
       :filters: percentage_full=0.5,storage_type=,async=false

Benchmark run details
---------------------
.. benchmark-details::
   :source: benchmark-summary