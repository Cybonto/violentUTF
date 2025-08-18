--
-- APISIX Gateway Authentication Plugin
-- Generates HMAC signatures for FastAPI authentication
--
local ngx = ngx
local ngx_var = ngx.var
local ngx_time = ngx.time
local hmac = require("resty.hmac")
local core = require("apisix.core")

local plugin_name = "apisix-gateway-auth"

local schema = {
    type = "object",
    properties = {
        gateway_secret = {
            type = "string",
            minLength = 1,
            description = "Shared secret for HMAC signature generation"
        }
    },
    required = {"gateway_secret"}
}

local _M = {
    version = 0.1,
    priority = 2000,
    name = plugin_name,
    schema = schema
}

function _M.check_schema(conf)
    return core.schema.check(schema, conf)
end

function _M.rewrite(conf, ctx)
    -- Get current timestamp
    local timestamp = tostring(ngx_time())

    -- Get request details
    local method = ngx_var.request_method
    local path = ngx_var.uri

    -- Create signature payload: METHOD:PATH:TIMESTAMP
    local signature_payload = method .. ":" .. path .. ":" .. timestamp

    -- Generate HMAC-SHA256 signature
    local hmac_sha256 = hmac:new(conf.gateway_secret, hmac.ALGOS.SHA256)
    hmac_sha256:update(signature_payload)
    local signature = hmac_sha256:final()

    -- Convert to hex string
    local signature_hex = ""
    for i = 1, #signature do
        signature_hex = signature_hex .. string.format("%02x", signature:byte(i))
    end

    -- Add required headers for FastAPI authentication
    ngx.req.set_header("X-API-Gateway", "APISIX")
    ngx.req.set_header("X-APISIX-Signature", signature_hex)
    ngx.req.set_header("X-APISIX-Timestamp", timestamp)

    core.log.info("Added APISIX gateway authentication headers for ", method, " ", path)
end

return _M
