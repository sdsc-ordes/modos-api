# Caddy gateway

Caddy acts as a single entrypoint and reverse proxy to the modos stack.

It is configured to route HTTP traffic to the other services in the stack.

## Configuration

Changes you may want to make to the default configuration include:

* Using HTTPS:

```diff
-http:// {
+https:// {
```

* Setting up an identity provider in forward_auth mode for use in production ([authentik example](https://docs.goauthentik.io/add-secure-apps/providers/proxy/server_caddy/)):

```
# Lets client/browser access the auth server
${auth_url} {
  reverse_proxy http://${auth_ip}:9000
}

${launch_url} {

  log
  encode
  route {
    request_body {
        max_size 5TB
    }

    # always forward outpost path to actual outpost
    reverse_proxy /outpost.goauthentik.io/* http://${auth_ip}:9000

    # forward authentication to outpost
    forward_auth http://${auth_ip}:9000 {
      uri /outpost.goauthentik.io/auth/caddy

      # capitalization of the headers is important, otherwise they will be empty
      copy_headers X-Authentik-Username X-Authentik-Groups X-Authentik-Entitlements X-Authentik-Email X-Authentik-Name X-Authentik-Uid X-Authentik-Jwt X-Authentik-Meta-Jwks X-Authentik-Meta-Outpost X-Authentik-Meta-Provider X-Authentik-Meta-App X-Authentik-Meta-Version

      # optional, in this config trust all private ranges, should probably be set to the outposts IP
      trusted_proxies private_ranges
    }
```
