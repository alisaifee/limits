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
       :query: limit=500 per 1 minute,group=hit,async=false
       :sort: storage_type,strategy


.. tab:: Hit (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=hit,async=true
       :sort: storage_type,strategy



.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=test,async=false
       :sort: storage_type,strategy


.. tab:: Test (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=test,async=true
       :sort: storage_type,strategy



.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=get-window-stats,async=false
       :sort: storage_type,strategy


.. tab:: Get Window Stats (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: limit=500 per 1 minute,group=get-window-stats,async=true
       :sort: storage_type,strategy


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
       :query: async=false,group=hit,strategy=fixed-window
       :sort: storage_type,limit


.. tab::  Hit (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=hit,strategy=fixed-window
       :sort: storage_type,limit


.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=test,strategy=fixed-window
       :sort: storage_type,limit


.. tab:: Test (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=test,strategy=fixed-window
       :sort: storage_type,limit


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=get-window-stats,strategy=fixed-window
       :sort: storage_type,limit

.. tab:: Get Window Stats (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=get-window-stats,strategy=fixed-window
       :sort: storage_type,limit

Moving Window
~~~~~~~~~~~~~

.. tab:: Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=hit,strategy=moving-window
       :sort: storage_type,limit

.. tab:: Hit (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=hit,strategy=moving-window
       :sort: storage_type,limit


.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=test,strategy=moving-window
       :sort: storage_type,limit

.. tab:: Test (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=test,strategy=moving-window
       :sort: storage_type,limit


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=get-window-stats,strategy=moving-window
       :sort: storage_type,limit

.. tab:: Get Window Stats (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=get-window-stats,strategy=moving-window
       :sort: storage_type,limit


Sliding Window
~~~~~~~~~~~~~~

.. tab:: Hit

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=hit,strategy=sliding-window
       :sort: storage_type,limit

.. tab:: Hit (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=hit,strategy=sliding-window
       :sort: storage_type,limit

.. tab:: Test

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=test,strategy=sliding-window
       :sort: storage_type,limit

.. tab:: Test (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=test,strategy=sliding-window
       :sort: storage_type,limit


.. tab:: Get Window Stats

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=false,group=get-window-stats,strategy=sliding-window
       :sort: storage_type,limit

.. tab:: Get Window (Async)

    .. benchmark-chart::
       :source: benchmark-summary
       :query: async=true,group=get-window-stats,strategy=sliding-window
       :sort: storage_type,limit


Benchmark run details
---------------------
.. benchmark-details::
   :source: benchmark-summary