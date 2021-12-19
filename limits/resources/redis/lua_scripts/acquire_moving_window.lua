local entry = redis.call('lindex', KEYS[1], tonumber(ARGV[2]) - 1)
local timestamp = tonumber(ARGV[1])
local expiry = tonumber(ARGV[3])

if entry and tonumber(entry) >= timestamp - expiry then
    return false
end
local limit = tonumber(ARGV[2])

redis.call('lpush', KEYS[1], timestamp)
redis.call('ltrim', KEYS[1], 0, limit - 1)
redis.call('expire', KEYS[1], expiry)

return true
