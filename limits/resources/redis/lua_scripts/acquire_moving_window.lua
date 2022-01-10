local amount = tonumber(ARGV[4])
local entry = redis.call('lindex', KEYS[1], tonumber(ARGV[2]) - amount)
local timestamp = tonumber(ARGV[1])
local expiry = tonumber(ARGV[3])

if entry and tonumber(entry) >= timestamp - expiry then
    return false
end
local limit = tonumber(ARGV[2])
local entries= {}
for i=1, amount do
    entries[i] = timestamp
end
redis.call('lpush', KEYS[1], unpack(entries))
redis.call('ltrim', KEYS[1], 0, limit - amount)
redis.call('expire', KEYS[1], expiry)

return true
