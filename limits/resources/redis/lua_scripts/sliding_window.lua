local expiry = tonumber(ARGV[1]) * 1000
local previous_count = redis.call('get', KEYS[1])
local previous_ttl = redis.call('pttl', KEYS[1])
local current_count = redis.call('get', KEYS[2])
local current_ttl = redis.call('pttl', KEYS[2])

if current_ttl > 0 and current_ttl < expiry then
    -- Current window expired, shift it to the previous window
    redis.call('rename', KEYS[2], KEYS[1])
    redis.call('set', KEYS[2], 0, 'PX', current_ttl + expiry)
    previous_count = redis.call('get', KEYS[1])
    previous_ttl = redis.call('pttl', KEYS[1])
    current_count = redis.call('get', KEYS[2])
    current_ttl = redis.call('pttl', KEYS[2])
end

return {previous_count, previous_ttl, current_count, current_ttl}
