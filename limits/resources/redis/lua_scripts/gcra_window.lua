local timestamp = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local expiry = tonumber(ARGV[3])
local burst = tonumber(ARGV[4])

local emission_interval = expiry / limit
local tolerance = (burst - 1) * emission_interval
local tat = tonumber(redis.call('get', KEYS[1])) or timestamp

if tat <= timestamp then
    return {tostring(timestamp), burst}
end

local used = math.min(burst, math.ceil((tat - timestamp) / emission_interval))
local remaining = math.max(0, burst - used)
local reset = timestamp
if remaining == 0 then
    reset = tat - tolerance
end

return {tostring(reset), remaining}
