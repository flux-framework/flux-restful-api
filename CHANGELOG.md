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
 - Add better multi-user mode - running jobs on behalf of user (0.1.12)
 - Restore original rpc to get job info (has more information) (0.1.11)
 - Refactor of FLux Restful to use a database and OAauth2 (0.1.0)
 - Support for basic PAM authentication (0.0.11)
 - Fixing bug with launcher always being specified (0.0.1)
  - catching any errors on creation of fluxjob
  - Add support uvicorn workers (>1 needed to run >1 process with Flux)
 - Project (faux) skeleton release (0.0.0)
