local rate_limit_key = KEYS[1]
local burst          = ARGV[1]
local rate           = ARGV[2]
local period         = ARGV[3]
local cost           = ARGV[4]

local emission_interval = period / rate
local increment         = emission_interval * cost
local burst_offset      = emission_interval * burst

local tat = redis.call("GET", rate_limit_key)

local time = redis.call("TIME")
local now = tonumber(time[1]) + tonumber(time[2])/1000000.0

if not tat then
  tat = now
else
  tat = tonumber(tat)
end

tat = math.max(tat, now)

local new_tat = tat + increment
local allow_at = new_tat - burst_offset
local diff = now - allow_at

local consumed = 0
local retry_in = 0
local reset_in

local remaining = math.floor(diff / emission_interval) -- poor man's round
if remaining < 0 then
  consumed = 0
  remaining = math.floor((now - (tat - burst_offset)) / emission_interval)
  reset_in = math.ceil(tat - now)
  retry_in = math.ceil(diff * -1)
elseif remaining == 0 and increment <= 0 then
  consumed = 1
  remaining = 0
  reset_in = math.ceil(tat - now)
else
  consumed = 1
  reset_in = math.ceil(new_tat - now)
  if increment > 0 then
    redis.call("SET", rate_limit_key, new_tat, "PX", reset_in)
  end
end

return {consumed, remaining, retry_in, reset_in}