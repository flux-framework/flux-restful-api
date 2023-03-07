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
 - Expose host to environment and bug fix for logs (0.1.14)
 - Ensure we update flux environment for user (0.1.13)
 - Add better multi-user mode - running jobs on behalf of user (0.1.12)
 - Restore original rpc to get job info (has more information) (0.1.11)
 - refactor to require secret key, oauth2 flow (0.1.0)
 - add simple retry to requests (0.0.16)
 - support for adding option flags to submit (0.0.15)
 - support for `is_launcher` parameter to indicate a launcher should be used instead (0.0.14)
 - support for streaming job output (0.0.13)
 - ensure logs end with one newline! (0.0.12)
 - support for job info and logs (0.0.11)
 - Parse envars from the command line, add descriptions for submit (0.0.1)
 - Project skeleton release (0.0.0)
