local now = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local rate = tonumber(ARGV[3])
local expiry = tonumber(ARGV[4])
local amount = tonumber(ARGV[5])

if amount > capacity then
    return 0
end

local state = redis.call('hmget', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(state[1])
local ts = tonumber(state[2])

if tokens == nil or ts == nil then
    tokens = capacity
    ts = now
end

local elapsed = now - ts
if elapsed < 0 then
    elapsed = 0
end
tokens = math.min(capacity, tokens + elapsed * rate)

local allowed = 0
if tokens >= amount then
    tokens = tokens - amount
    allowed = 1
end

-- store the token count as a string so the fractional part is never lost to
-- Lua's integer coercion, and refresh the safety expiry.
redis.call('hset', KEYS[1], 'tokens', tostring(tokens), 'ts', tostring(now))
redis.call('expire', KEYS[1], expiry)

return allowed
