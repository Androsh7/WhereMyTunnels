# WhereMyTunnels

![example_1](/docs/example_1.png)

**WhereMyTunnels** is a cross-platform tool for viewing SSH connections and tunnels.

## Usage

```
usage: wheremytunnels [options]

Tool for viewing SSH connections

options:
  -h, --help            show this help message and exit
  --version, -v         show program's version number and exit
  --about, -a           Show information about WhereMyTunnels
  --interval, -i INTERVAL
                        Refresh interval in seconds (default: 2)
  --no-color            Disable colored output
  --show-connections    Displays attached connections I.E: "LISTEN 127.0.0.1:8081", "ESTABLISHED 15.1.2.5:12385 -> 8.5.1.4:80"
  --show-arguments      Shows SSH arguments I.E: "ssh test.com -L 8080:localhost:80"
```


## Why does this exist?

During a CTF in late 2024, I found myself five SSH tunnels deep while pivoting between hosts trying to find a flag when I suddenly got disconnected from my ssh jump box.

When I finally got back in, all my notes were gone, and I was left with one question: **Where My Tunnels?**

## How does this work?

1. Enumerates active ssh processes using [psutil](https://github.com/giampaolo/psutil)
2. Parses ssh processes into:
    - Master sockets (-MS) and attached socket forwards/sessions (-S)
    - Traditional tunnels (-L, -R, -D)
    - Traditional SSH sessions
3. Find associations between processes, forwards, and connections
4. Detect errors in forwards and connections I.E: a local forward that doesn't have an attached listening connection
5. Render everything in a tree structure using [rich](https://github.com/Textualize/rich)


## Linux Install

Download the wheremytunnels binary from the release page, see (Which linux binary do I pick?) for help

Then run:
```
chmod 755 wheremytunnels_latest_linux.bin
mv wheremytunnels_latest_linux.bin /usr/bin/wheremytunnels
```
### Which linux binary do I pick?
#### glibc vs musl

Nearly all linux systems use glibc or the GNU C Library, including:
- Ubuntu
- Debian
- Fedora
- CentOS / RHEL
- Kali
- Arch Linux

However some more "unique" operating systems rely on musl, notably Alpine linux

#### Architecture

Most systems run on the `x86_64` cpu architecture, however some devices use `ARM`  (`aarch64`)

The simplest way to tell is by running `uname -m`, you could also determine this by looking at your cpu specifications

## Windows Install

There is currently only an x86_64 install for windows, sorry ARM users

After downloading the windows binary run:
```
Move-Item -Path "wheremytunnels_latest_windows.exe" -Destination "~/AppData/Local/Microsoft/WindowsApps/wheremytunnels.exe"
```

# Examples

`wheremytunnels.exe`

![example_1](/docs/example_1.png)

`wheremytunnels.exe --show-arguments --show-connections`

![example_2](/docs/example_2.png)