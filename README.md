# Desktop ID Probe

A ~1 MB AppImage with its desktop file ID baked in, the way real apps have it,
and one button per feature that looks the app up by that ID. Install its
`.desktop` file under the original name, then renamed, and compare.

- Built-in ID: `org.example.DesktopIdProbe`. This is the Wayland app_id, the
  X11 `WM_CLASS` (`org.example.DesktopIdProbe`, `Org.example.DesktopIdProbe`),
  the GApplication ID, the notification `desktop-entry` hint, the badge URI and
  the MPRIS `DesktopEntry`.
- Embedded desktop file: `org.example.DesktopIdProbe.desktop`. It declares
  `MimeType=x-scheme-handler/dtprobe-static`. The `dtprobe://` scheme is only
  ever registered at runtime, the way Electron does it.
- The window sets no icon of its own, so the only icon source is the desktop
  file the shell matches the window to.
- It runs on the host's Python, so it needs `python3` with PyGObject and GTK 3:
  Debian/Ubuntu `python3-gi gir1.2-gtk-3.0`, Fedora `python3-gobject gtk3`,
  Arch `python-gobject gtk3`.

## Results so far

See [RESULTS.md](RESULTS.md) for GNOME and Noctalia + niri; KDE Plasma is not tested yet.

## Setup

`$AI` below is just a shell variable holding the absolute path to the AppImage.
The installed desktop file's `Exec=` points at that path, so don't move the
AppImage afterwards.

```sh
cd desktop-id-probe
chmod +x dist/Desktop_ID_Probe-x86_64.AppImage dtprobe-integrate.sh
AI=$PWD/dist/Desktop_ID_Probe-x86_64.AppImage   # use the aarch64 one on ARM

./dtprobe-integrate.sh install "$AI"                                   # A: original name
./dtprobe-integrate.sh install "$AI" --as dtprobe-renamed              # B: renamed
./dtprobe-integrate.sh install "$AI" --as dtprobe-renamed --wmclass    # C: renamed + StartupWMClass
./dtprobe-integrate.sh install "$AI" --subdir appimages                # D: original name, in applications/appimages/
./dtprobe-integrate.sh uninstall                                       # between runs
```

You can use your own install script instead. It only has to extract
`org.example.DesktopIdProbe.desktop` and the icon. Do one configuration at a
time and run `uninstall` in between. Quit the probe before switching: it's
single-instance, so relaunching only re-focuses the old process.

For each run:

1. Launch it from the app grid or menu, not a terminal. That's how real users
   launch apps, and it gives you a launcher-named systemd scope.
2. Pin it to the dock and check the pinned icon and the running window.
3. Click through the buttons. The log at the bottom says what was sent.
4. Repeat test 1 launched from a terminal, which removes the
   startup-notification rescue.

The identity panel shows whether a desktop file with the built-in ID exists,
which desktop file launched the app (`GIO_LAUNCHED_DESKTOP_FILE`), the systemd
unit, and the app ID xdg-desktop-portal would derive from that unit.

## What to expect

These are predictions from reading the GNOME Shell, Plasma, GLib and
xdg-desktop-portal source. That's what you're testing.

| # | Test | A: original | B: renamed | C: renamed + `--wmclass` | D: `--subdir appimages` |
|---|---|---|---|---|---|
| 1 | Window ↔ pinned launcher, window icon (Alt-Tab, Wayland titlebar) | One dock entry, real icon | GNOME: generic icon, second dock entry. KDE: icon from `$APPDIR` fallback, may not merge with the pin | Same as A | GNOME: same as B. KDE: same as A (it matches the bare file name) |
| 2 | fdo notification (this process) | Icon + app name | GNOME: generic | Same as A on GNOME (matched by the window's PID) | GNOME: same as B |
| 2 | fdo notification (child, no PID match) | Icon + app name | Generic | Generic | GNOME: generic |
| 2b | GNotification | Shows | **GNOME: never appears.** Other desktops: falls back to fdo, like row 2 | Same as B | Same as B |
| 2c | Notification with a click action (sends `default`; the probe raises itself with the server's activation token) | Clicking raises the probe | Same | Same | Same |
| 3 | Badge + progress | Count/progress on the dock icon | Nothing | Nothing | Dash to Dock: nothing. Plasma: untested |
| 4 | Register `dtprobe://` at runtime → "Am I default?" → Open | Registered / YES / "Received URI" | FAIL / NO / no handler | Same as B | Same as B |
| 4 | Open `dtprobe-static://` (declared in the file) | Works | Works | Works | Works |
| 5 | Portal `Registry.Register` | Accepted | Refused: `App info not found` | Same as B | Same as B |
| 6 | MPRIS player: media widget icon/name, Raise | Icon + name, Raise focuses | Generic or missing icon | Same as B | GNOME: same as B. Plasma: untested |

Where you'll see each one:

- **Test 3** needs a dock that implements `com.canonical.Unity.LauncherEntry`:
  Ubuntu Dock / Dash to Dock, Dash to Panel, or the Plasma task manager. Stock
  GNOME Shell shows nothing even in case A.
- **Test 5** needs xdg-desktop-portal 1.19.1 or newer; older versions report
  that the Registry interface doesn't exist. The identity panel also shows the
  launcher path: started from the app grid, the scope is named after the
  *installed* file, so the portal's derived ID is consistent even when renamed.
- **Test 6** shows up in the GNOME media controls (in the clock/calendar menu)
  and Plasma's Media Player widget.

### Why D is mostly a rename

The desktop entry spec makes the path below `applications/` part of the ID,
with `/` turned into `-`. So `applications/appimages/org.example.DesktopIdProbe.desktop`
has the ID `appimages-org.example.DesktopIdProbe.desktop`. GLib, GNOME Shell and
the portal look the app up by its exact ID, so it's not found. The identity
panel shows the launching file's ID next to the built-in one.

There are two exceptions:

- **KDE window matching** compares the app_id with the bare file name
  (`KService::desktopEntryName`), ignoring the directory, so row 1 should
  still work on Plasma.
- **GNOME window matching** also retries the ID with the vendor prefixes
  `gnome-`, `fedora-`, `mozilla-` and `debian-`. With `--subdir gnome`, row 1
  should work on GNOME but the other rows should still fail. That's a useful
  control.

## Extra experiments

- **Hidden alias:** install C, then `install "$AI" --hidden`, which adds the
  original name with `NoDisplay=true`. Rows 2b, 4, 5 and 6 should pass. Badges
  should still not reach the pinned launcher.
- **`--rename-icon`:** installs the icon under the new name as well, like
  libappimage does. On KDE, case B then loses the `$APPDIR` fallback icon.
- **`$DESKTOPINTEGRATION`:** shown in the identity panel. AppImageLauncher sets
  it to stop self-integrating apps from writing their own entry.

## Rebuild

`./build.sh` downloads appimagetool and the type2 runtimes into `.cache/`, then
builds `dist/` for x86_64 and aarch64. The app itself is
`AppDir/usr/share/dtprobe/dtprobe.py`.

## Recording results

`results/results.json` holds the recorded results. After editing it, regenerate
the tables with `python3 tools/render_results.py`. Each cell is
`{"s": "works" | "partial" | "broken" | "na" | "", "n": "notes"}`, keyed
`<test>|<install mode>` (for example `fdochild|A`).
