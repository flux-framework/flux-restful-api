# CHANGELOG

This is a manually generated log to track changes to the repository for each release.
Each section should include general headers such as **Implemented enhancements**
and **Merged pull requests**. Critical items to know are:

 - renamed commands
 - deprecated / removed commands
 - changed defaults
 - backward incompatible changes (recipe file format? image file format?)
 - migration guidance (how to convert images?)
 - changed behaviour (recipe sections work differently)

The versions coincide with releases on pip. Only major versions will be released as tags on Github.

## [0.0.x](https://github.com/flux-framework/flux-restful-api/tree/main) (0.0.x)
 - Requests no longer block on running jobs: output is read as a snapshot, Flux calls run off the event loop with per-thread handles; bad job ids are 400, missing jobs 404 (unreleased)
 - Jobs and launchers get an allowlist of the server environment instead of all of it (unreleased)
   - server settings and secrets no longer reach jobs; add variables with FLUX_JOB_ENV_PASSTHROUGH (names or patterns)
   - web UI: messages and job table cells are escaped, forms carry a CSRF token, cancel is a POST
 - Pluggable authentication backends via FLUX_AUTH_BACKEND: none, database, shared-secret, pam, oidc (unreleased)
   - access tokens are signed with a server-only FLUX_TOKEN_SIGNING_KEY (required; entrypoint generates one), never the client shared secret
   - a failed login at a token endpoint is 400, not 401, so clients do not loop re-requesting a token
   - FLUX_ADMIN_USERS grants superuser with any backend; GET /v1/auth describes how to log in
   - FLUX_REQUIRE_AUTH=false now disables auth (previously any value enabled it)
 - Multi-user mode becomes the user directly (no sudo); jobs are owned by their user, others get 403 (unreleased)
 - Pin dependencies; hash passwords with bcrypt directly; fix views and job listing on current FastAPI/Flux (unreleased)
 - Ensure we update flux environment for user (0.1.13)
 - Add better multi-user mode - running jobs on behalf of user (0.1.12)
 - Restore original rpc to get job info (has more information) (0.1.11)
 - Refactor of FLux Restful to use a database and OAauth2 (0.1.0)
 - Support for basic PAM authentication (0.0.11)
 - Fixing bug with launcher always being specified (0.0.1)
  - catching any errors on creation of fluxjob
  - Add support uvicorn workers (>1 needed to run >1 process with Flux)
 - Project (faux) skeleton release (0.0.0)
