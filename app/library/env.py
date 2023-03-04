# Faux user environment (filtered set of application environment)
# We could likely find a way to better do this, but likely the users won't have customized environments
user_env = {
    "SHELL": "/bin/bash",
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin",
    "XDG_RUNTIME_DIR": "/tmp/user/0",
    "DISPLAY": ":0",
    "COLORTERM": "truecolor",
    "SHLVL": "2",
    "DEBIAN_FRONTEND": "noninteractive",
    "MAKE_TERMERR": "/dev/pts/1",
    "LANG": "C.UTF-8",
    "TERM": "xterm-256color",
}
