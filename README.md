# Desktop Filename Tester

A small testing setup to check what breaks when you rename an app's `*.desktop` file. Different desktop environments and shells seem to behave differently.

## Results so far

See [test results](https://syntactic-spice.github.io/desktop-filename-tester/) ([text version](RESULTS.md)) for GNOME and Noctalia + niri; KDE Plasma is not tested yet.\
Here's an [empty template](https://syntactic-spice.github.io/desktop-filename-tester/template.html) to record your own.

## The problem
On Linux, apps use a `*.desktop` file to tell the launcher/dock/desktop environment about themselves. These are usually stored in `~/.local/share/applications` (or `/usr/share/applications` system-wide).

AppImages usually include an embdded desktop file, which is then extracted to the user's applications directory. However, existing programs that manage AppImages ([Gear Lever](https://github.com/mijorus/gearlever), [AppImageLauncher](https://github.com/TheAssassin/AppImageLauncher), etc.) all seem to rename the file in some way, which subtly breaks things. Reading the [XDG spec](https://specifications.freedesktop.org/desktop-entry/latest/file-naming.html) on the naming convention, it seems entirely expected this would be the case.

Different desktop shells seem to use different heuristics as workarounds, and so behave differently.

## The test
Download a release or follow instructions from the Rebuild section.

This repository builds a minimal AppImage and provides a script to install the icon and desktop file in various ways. The app has buttons that perform various actions, like creating notifications in different ways, updating progress badge, etc., whose results can be manually observed and entered recorded. See the HTML template to check what to look for.

It runs on the host's Python, so it needs `python3` with PyGObject and GTK 3:
  Debian/Ubuntu `python3-gi gir1.2-gtk-3.0`, Fedora `python3-gobject gtk3`,
  Arch `python-gobject gtk3`.

The installed desktop file's `Exec=` points at that path, so don't move the
AppImage afterwards.

```sh
cd desktop-filename-tester
chmod +x dist/Desktop_ID_Probe-x86_64.AppImage dtprobe-integrate.sh
AppimagePath=$PWD/dist/Desktop_ID_Probe-x86_64.AppImage   # use the aarch64 one on ARM

./dtprobe-integrate.sh uninstall                                                 # Uninstall if exists
./dtprobe-integrate.sh install "$AppimagePath"                                   # A: original name
# Manual testing...
./dtprobe-integrate.sh uninstall                                                 # Uninstall if exists
./dtprobe-integrate.sh install "$AppimagePath" --as dtprobe-renamed              # B: renamed
# Manual testing...
./dtprobe-integrate.sh uninstall                                                 # Uninstall if exists
./dtprobe-integrate.sh install "$AppimagePath" --as dtprobe-renamed --wmclass    # C: renamed + StartupWMClass
# Manual testing...
./dtprobe-integrate.sh uninstall                                                 # Uninstall if exists
./dtprobe-integrate.sh install "$AppimagePath" --subdir appimages                # D: original name, in applications/appimages/
# Manual testing...
./dtprobe-integrate.sh uninstall

# Repeat above for each desktop shell
```

Quit the probe before switching: it's single-instance, so relaunching only re-focuses the old process.

For each run:

1. Launch it from the app grid or menu, not a terminal.
2. Pin it to the dock and check the pinned icon and the running window.
3. Click through the buttons. The log at the bottom says what was sent.

<img width="759" height="822" alt="image" src="https://github.com/user-attachments/assets/de7bcb5d-4410-4bee-ace0-06a936fccd8d" />


The identity panel shows whether a desktop file with the built-in ID exists,
which desktop file launched the app (`GIO_LAUNCHED_DESKTOP_FILE`), the systemd
unit, and the app ID xdg-desktop-portal would derive from that unit.

## Extra experiments

- **Hidden alias:** install C, then `install "$AppimagePath" --hidden`, which adds the
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
