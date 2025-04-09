local len = tonumber(ARGV[2])
local expiry = tonumber(ARGV[1])

-- Binary search to find the oldest valid entry in the window
local function oldest_entry(high, target)
    local low = 0
    local result = nil

    while low <= high do
        local mid = math.floor((low + high) / 2)
        local val = tonumber(redis.call('lindex', KEYS[1], mid))

        if val and val >= target then
            result = mid
            low = mid + 1
        else
            high = mid - 1
        end
    end

    return result
end

local index = oldest_entry(len - 1, expiry)

if index then
    local count = index + 1
    local oldest = tonumber(redis.call('lindex', KEYS[1], index))
    return {tostring(oldest), count}
end
