local timestamp = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local expiry = tonumber(ARGV[3])
local amount = tonumber(ARGV[4])
local burst = tonumber(ARGV[5])

if amount > burst then
    return false
end

local emission_interval = expiry / limit
local tolerance = burst * emission_interval
local tat = tonumber(redis.call('get', KEYS[1])) or timestamp

if tat < timestamp then
    tat = timestamp
end

local new_tat = tat + amount * emission_interval
if new_tat - tolerance > timestamp then
    return false
end

redis.call('set', KEYS[1], tostring(new_tat))
redis.call('expire', KEYS[1], math.max(1, math.ceil(new_tat - timestamp)))

return true
