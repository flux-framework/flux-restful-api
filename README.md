# Flux RESTFul API

<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-2-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

![img/flux-restful-eyes-small.png](img/flux-restful-eyes-small.png)

This is a small Flux Python API (using FastAPI) that can be containerized
alongside Flux, and provide an easy means to interact with Flux via the API.
With Flux RESTful we can:

1. provide simple endpoints to submit jobs, list jobs, or get job status
2. eventually support subscribing to events and a user interface job table
3. option to kill or stop the server (intended for Flux Operator)
4. allow for start with a user name and token (for basic auth)


This project is new and we look forward to [hearing your feedback](https://github.com/flux-framework/flux-restful-api).
See our ⭐️ [Documentation](https://flux-framework.github.io/flux-restful-api) ⭐️ to get started!

![img/flux-restful.png](img/flux-restful.png)


## 😁️ Contributors 😁️

We use the [all-contributors](https://github.com/all-contributors/all-contributors)
tool to generate a contributors graphic below.

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://vsoch.github.io"><img src="https://avatars.githubusercontent.com/u/814322?v=4?s=100" width="100px;" alt="Vanessasaurus"/><br /><sub><b>Vanessasaurus</b></sub></a><br /><a href="https://github.com/flux-framework/flux-restful-api/commits?author=vsoch" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://linkedin.com/in/tgamblin/"><img src="?s=100" width="100px;" alt="Todd Gamblin"/><br /><sub><b>Todd Gamblin</b></sub></a><br /><a href="https://github.com/flux-framework/flux-restful-api/commits?author=tgamblin" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->


## TODO

- Interface view with nice job table
- We can put additional assets for the server in [data](data), not sure what those are yet!

#### Release

SPDX-License-Identifier: LGPL-3.0

LLNL-CODE-764420
