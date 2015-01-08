.. _ratelimit-string:

Rate limit string notation
--------------------------

Rate limits are specified as strings following the format:

    [count] [per|/] [n (optional)] [second|minute|hour|day|month|year]

You can combine multiple rate limits by separating them with a delimiter of your
choice.

Examples
========

* 10 per hour
* 10/hour
* 10/hour;100/day;2000 per year
* 100/day, 500/7days
