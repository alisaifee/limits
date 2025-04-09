local timestamp = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local expiry = tonumber(ARGV[3])
local amount = tonumber(ARGV[4])

if amount > limit then
    return false
end

local entry = redis.call('lindex', KEYS[1], limit - amount)

if entry and tonumber(entry) >= timestamp - expiry then
    return false
end
local entries = {}
for i = 1, amount do
    entries[i] = timestamp
end

for i=1,#entries,5000 do
    redis.call('lpush', KEYS[1], unpack(entries, i, math.min(i+4999, #entries)))
end
redis.call('ltrim', KEYS[1], 0, limit - 1)
redis.call('expire', KEYS[1], expiry)

return true
