# Desktop ID Probe results

What breaks when an AppImage's `.desktop` file is installed under a different name.
Install modes:

- **A: original name**: `./dtprobe-integrate.sh install "$AI"`
- **B: renamed**: `./dtprobe-integrate.sh install "$AI" --as dtprobe-renamed`
- **C: renamed + StartupWMClass**: `./dtprobe-integrate.sh install "$AI" --as dtprobe-renamed --wmclass`
- **D: in a subdirectory**: `./dtprobe-integrate.sh install "$AI" --subdir appimages`

✅ works · 🟡 partly works · ❌ broken · ➖ not applicable · · not tested

## Overview

| Test | GNOME A | GNOME B | GNOME C | GNOME D | Noctalia A | Noctalia B | Noctalia C | Noctalia D |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 · Window ↔ launcher | ✅ | 🟡 | ✅ | 🟡 | ✅ | ✅ | ✅ | ✅ |
| 2 · Notification, this process | ✅ | 🟡 | ✅ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| 2 · Notification, child process | ❌ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |
| 2b · GNotification | ✅ | ❌ | ❌ | ❌ | 🟡 | 🟡 | 🟡 | 🟡 |
| 3 · Badge + progress | ✅ | ❌ | ❌ | ❌ | ➖ | ➖ | ➖ | ➖ |
| 4 · `dtprobe://` registered at runtime | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 4 · `dtprobe-static://` declared in file | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 5 · Portal `Registry.Register` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 6 · MPRIS media widget | ✅ | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 | 🟡 |

## GNOME

Distro: Ubuntu 26.04.1 · Desktop / shell: 50 · Session: Wayland

| Test | A: original name | B: renamed | C: renamed + StartupWMClass | D: in a subdirectory |
|---|---|---|---|---|
| 1 · Window ↔ launcher | ✅ | 🟡 generic icon, cannot be pinned | ✅ | 🟡 generic icon, cannot be pinned |
| 2 · Notification, this process | ✅ | 🟡 generic icon, ID instead of app name, raise on click | ✅ | 🟡 generic icon, ID instead of app name, raise on click |
| 2 · Notification, child process | ❌ Notification immediately disappears [^gnome1] | 🟡 generic icon, actual name, raise on click | 🟡 generic icon, ID instead of app name, does not raise on click | 🟡 generic icon, actual name, does not raise on click |
| 2b · GNotification | ✅ | ❌ No notification | ❌ No notification | ❌ No notification |
| 3 · Badge + progress | ✅ | ❌ | ❌ | ❌ |
| 4 · `dtprobe://` registered at runtime | ✅ | ❌ | ❌ | ❌ |
| 4 · `dtprobe-static://` declared in file | ✅ | ✅ | ✅ | ✅ |
| 5 · Portal `Registry.Register` | ✅ | ❌ | ❌ | ❌ |
| 6 · MPRIS media widget | ✅ | 🟡 generic icon, actual name, click sends a new notification which raises on click | 🟡 generic icon, actual name, click sends a new notification which raises on click | 🟡 generic icon, actual name, click sends a new notification which raises on click |

[^gnome1]: Probe artifact, not a GNOME bug. GNOME removes notifications from an identified app when the sender leaves the session bus, and the probe's helper process exited right after sending. Disappearing here shows GNOME did match the app. Fixed in the probe (the helper now stays until the notification closes); re-test pending.

## KDE Plasma

Not tested yet.

## Noctalia + niri

Distro: Ubuntu 26.04.1 · Session: Wayland

| Test | A: original name | B: renamed | C: renamed + StartupWMClass | D: in a subdirectory |
|---|---|---|---|---|
| 1 · Window ↔ launcher | ✅ | ✅ | ✅ | ✅ |
| 2 · Notification, this process | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable |
| 2 · Notification, child process | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable |
| 2b · GNotification | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable | 🟡 no icon, unclickable |
| 3 · Badge + progress | ➖ unsupported | ➖ unsupported | ➖ unsupported | ➖ unsupported |
| 4 · `dtprobe://` registered at runtime | ✅ | ❌ | ❌ | ❌ |
| 4 · `dtprobe-static://` declared in file | ✅ | ✅ | ✅ | ✅ |
| 5 · Portal `Registry.Register` | ✅ | ❌ | ❌ | ❌ |
| 6 · MPRIS media widget | 🟡 no icon, no option to raise, receives events | 🟡 no icon, no option to raise, receives events | 🟡 no icon, no option to raise, receives events | 🟡 no icon, no option to raise, receives events |

<sub>Results saved 2026-10-15.</sub>
