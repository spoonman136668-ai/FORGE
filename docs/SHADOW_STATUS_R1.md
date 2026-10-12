# INACTIVE shadow observer HTTP status boundary

The shadow observer exposes a **loopback-only** GET /status endpoint. Before a complete verified snapshot it returns HTTP 503; no mutation/worker/lease/reservation/authority endpoints exist. This is visibility only, not an active FORGE Scientific Authority.

For private evidence safety, use a protected host: no remote access, public ingress, shared workstation, or proxy forwarding. A deployed service still requires operator-approved provisioning, authentication appropriate to the environment, independent durable journal and witnessing, and exact legacy custody reconciliation. Tests assert wildcard and non-literal loopback binding is rejected.

The API does not claim any real scientific cycles completed.
