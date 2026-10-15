#!/usr/bin/env python3
"""Desktop ID Probe.

A tiny GTK app that, like most real apps, has its desktop file ID baked in.
Each button exercises one desktop integration feature that looks the app up
by that ID, so you can compare behaviour with the .desktop file installed
under its original name versus a renamed one.
"""

import os
import re
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

# The built-in identity. Real apps hard-code this (Electron: package.json
# "desktopName"; GTK: application_id; Qt: QGuiApplication::desktopFileName).
# DTPROBE_APP_ID exists only so you can experiment; leave it unset for tests.
APP_ID = os.environ.get("DTPROBE_APP_ID", "org.example.DesktopIdProbe")
DESKTOP_ID = APP_ID + ".desktop"
NAME = "Desktop ID Probe"
RUNTIME_SCHEME = "dtprobe"  # registered at runtime, the way Electron does it
STATIC_SCHEME = "dtprobe-static"  # declared in the .desktop file's MimeType=

NOTIFY_BUS = "org.freedesktop.Notifications"
NOTIFY_PATH = "/org/freedesktop/Notifications"
LAUNCHER_ENTRY_IFACE = "com.canonical.Unity.LauncherEntry"
LAUNCHER_ENTRY_PATH = "/com/canonical/unity/launcherentry/dtprobe"
MPRIS_BUS = "org.mpris.MediaPlayer2.dtprobe"
MPRIS_PATH = "/org/mpris/MediaPlayer2"

MPRIS_XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek"><arg direction="in" name="Offset" type="x"/></method>
    <method name="SetPosition">
      <arg direction="in" name="TrackId" type="o"/>
      <arg direction="in" name="Position" type="x"/>
    </method>
    <method name="OpenUri"><arg direction="in" name="Uri" type="s"/></method>
    <signal name="Seeked"><arg name="Position" type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""

# Same patterns xdg-desktop-portal uses to derive a host app's ID from its
# systemd unit (shared/xdp-app-info-host.c).
SCOPE_RE = re.compile(r"^app-(?:[A-Za-z0-9]+-)?(.+?)(?:-[A-Za-z0-9]*)(?:\.scope|\.slice)$")
SERVICE_RE = re.compile(r"^app-(?:[A-Za-z0-9]+-)?(.+?)(?:@[A-Za-z0-9]*|-autostart)?\.service$")


def lookup_app_info(desktop_id):
    try:
        return Gio.DesktopAppInfo.new(desktop_id)
    except TypeError:  # PyGObject raises when the constructor returns NULL
        return None


def find_desktop_file(desktop_id):
    info = lookup_app_info(desktop_id)
    return info.get_filename() if info else None


def desktop_id_for_path(path):
    """Desktop file ID per the spec: path below applications/, '/' -> '-'."""
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    data_dirs = (os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    for d in [data_home] + data_dirs:
        apps = os.path.join(d, "applications") + os.sep
        if path.startswith(apps):
            return path[len(apps):].replace(os.sep, "-")
    return None


def systemd_unit():
    try:
        with open("/proc/self/cgroup") as f:
            for line in f:
                path = line.rstrip("\n").split(":", 2)[-1]
                return path.rsplit("/", 1)[-1]
    except OSError:
        pass
    return None


def portal_app_id_from_unit(unit):
    if not unit or not unit.startswith("app-"):
        return None
    m = SCOPE_RE.match(unit) or SERVICE_RE.match(unit)
    if not m:
        return None
    return re.sub(r"\\x([0-9a-fA-F]{2})", lambda h: chr(int(h.group(1), 16)), m.group(1))


def identity_report():
    own = find_desktop_file(DESKTOP_ID)
    launched = os.environ.get("GIO_LAUNCHED_DESKTOP_FILE")
    unit = systemd_unit()
    portal_id = portal_app_id_from_unit(unit)
    lines = [
        f"Built-in ID (Wayland app_id, X11 WM_CLASS instance): {APP_ID}",
        f"Session: {os.environ.get('XDG_SESSION_TYPE', '?')} / "
        f"{os.environ.get('XDG_CURRENT_DESKTOP', '?')}",
        f"Desktop file for built-in ID ({DESKTOP_ID}): "
        + (own if own else "MISSING -> rows 2b, 3, 4, 5 and 6 should fail"),
        f"Launched from (GIO_LAUNCHED_DESKTOP_FILE): {launched or '(not set)'}",
    ]
    if launched:
        launched_id = desktop_id_for_path(launched)
        lines.append(
            f"  its desktop file ID: {launched_id or '(outside applications/ dirs)'}"
            + ("" if launched_id == DESKTOP_ID else f"  (differs from {DESKTOP_ID})")
        )
    lines += [
        f"systemd unit: {unit or '(unknown)'}",
    ]
    if portal_id:
        found = find_desktop_file(portal_id + ".desktop")
        lines.append(
            f"  portal would derive app ID {portal_id!r}: "
            + ("desktop file found" if found else "NO desktop file -> empty app ID")
        )
    else:
        lines.append("  not an app-*.scope/.service unit -> portal has no app ID unless Register is called")
    for var in ("APPIMAGE", "APPDIR", "DESKTOPINTEGRATION"):
        lines.append(f"${var}: {os.environ.get(var, '(not set)')}")
    return lines


def send_fdo_notification(summary, body, with_hint=True, actions=()):
    """Plain org.freedesktop.Notifications call, as libnotify/Electron make it.

    No app_icon on purpose: the icon should come from the desktop file the
    server matches, which is what's being tested.
    """
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    hints = {"desktop-entry": GLib.Variant("s", APP_ID)} if with_hint else {}
    reply = bus.call_sync(
        NOTIFY_BUS, NOTIFY_PATH, NOTIFY_BUS, "Notify",
        GLib.Variant("(susssasa{sv}i)", (NAME, 0, "", summary, body, list(actions), hints, -1)),
        GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, -1, None,
    )
    return reply.unpack()[0]


def notify_child_main():
    """Runs in a separate, windowless process so GNOME can't match it by PID.

    It stays on the bus until the notification closes: GNOME removes an
    identified app's notifications as soon as their sender disconnects.
    """
    try:
        nid = send_fdo_notification(
            "fdo notification (child process)",
            f"desktop-entry={APP_ID}. No window owns this PID, so only the hint "
            "can identify the app. Check the icon and app name.",
        )
    except GLib.Error as e:
        print(f"Notify failed: {e.message}", flush=True)
        return 1
    print(f"sent notification #{nid}", flush=True)
    loop = GLib.MainLoop()

    def on_closed(_conn, _sender, _path, _iface, _signal, params):
        closed_id, reason = params.unpack()
        if closed_id == nid:
            print(f"notification #{nid} closed (reason {reason})", flush=True)
            loop.quit()

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.signal_subscribe(None, NOTIFY_BUS, "NotificationClosed", NOTIFY_PATH, None,
                         Gio.DBusSignalFlags.NONE, on_closed)
    GLib.timeout_add_seconds(120, loop.quit)
    loop.run()
    return 0


class Probe(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.window = None
        self.log_buffer = None
        self.badge_count = 0
        self.portal_conn = None
        self.mpris_owner_id = 0
        self.mpris_reg_ids = []
        self.mpris_playing = True
        self.click_ids = {}  # notification id -> activation token (None until sent)
        self.notify_sub = 0

    # ---- lifecycle -------------------------------------------------------

    def do_activate(self):
        self.ensure_window()
        self.window.present()

    def do_open(self, files, *_n_files_and_hint):
        self.ensure_window()
        for f in files:
            self.log(f"Received URI via launcher: {f.get_uri()}")
        self.window.present()

    def do_shutdown(self):
        self.stop_mpris()
        Gtk.Application.do_shutdown(self)

    # ---- UI --------------------------------------------------------------

    def ensure_window(self):
        if self.window:
            return
        # No window icon is set on purpose: like most AppImages, the only
        # source of the icon is the .desktop file the shell matches us to.
        win = Gtk.ApplicationWindow(application=self, title=NAME)
        win.set_default_size(760, 680)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=10)
        win.add(outer)

        self.identity_label = Gtk.Label(xalign=0, selectable=True)
        self.identity_label.get_style_context().add_class("monospace")
        self.identity_label.set_line_wrap(True)
        frame = Gtk.Frame(label="Identity")
        frame.add(self.identity_label)
        outer.pack_start(frame, False, False, 0)

        grid = Gtk.Grid(row_spacing=6, column_spacing=6, column_homogeneous=True)
        buttons = [
            ("1  Refresh identity", self.on_identity),
            ("2  fdo notification (this process)", self.on_fdo_notify),
            ("2  fdo notification (child, no PID match)", self.on_fdo_notify_child),
            ("2b GNotification (GApplication)", self.on_gnotification),
            ("2c Notification with click action", self.on_click_notify),
            ("3  Badge +1 / progress", self.on_badge),
            ("3  Clear badge", self.on_badge_clear),
            (f"4  Register {RUNTIME_SCHEME}:// at runtime", self.on_register_scheme),
            (f"4  Am I default for {RUNTIME_SCHEME}://?", self.on_check_scheme),
            (f"4  Open {RUNTIME_SCHEME}://hello", self.on_open_runtime_uri),
            (f"4  Open {STATIC_SCHEME}://hello", self.on_open_static_uri),
            ("5  Portal Registry.Register", self.on_portal_register),
            ("6  Toggle MPRIS player", self.on_mpris_toggle),
        ]
        for i, (label, handler) in enumerate(buttons):
            b = Gtk.Button(label=label)
            b.get_child().set_xalign(0)
            b.connect("clicked", lambda _b, h=handler: self.safely(h))
            grid.attach(b, i % 2, i // 2, 1, 1)
        outer.pack_start(grid, False, False, 0)

        view = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.log_buffer = view.get_buffer()
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.add(view)
        self.log_view = view
        outer.pack_start(scroller, True, True, 0)

        win.show_all()
        self.window = win
        self.on_identity()

    def log(self, msg):
        line = f"{time.strftime('%H:%M:%S')}  {msg}"
        print(line, flush=True)
        if self.log_buffer:
            self.log_buffer.insert(self.log_buffer.get_end_iter(), line + "\n")
            self.log_view.scroll_to_iter(self.log_buffer.get_end_iter(), 0, False, 0, 0)

    def safely(self, handler):
        try:
            handler()
        except GLib.Error as e:
            self.log(f"ERROR: {e.message}")
        except Exception as e:  # keep the probe alive whatever happens
            self.log(f"ERROR: {type(e).__name__}: {e}")

    # ---- 1: identity -----------------------------------------------------

    def on_identity(self):
        lines = identity_report()
        self.identity_label.set_text("\n".join(lines))
        print("\n".join(lines), flush=True)
        self.log("Identity: desktop file for built-in ID is "
                 + ("present" if find_desktop_file(DESKTOP_ID) else "MISSING"))

    # ---- 2: notifications ------------------------------------------------

    def on_fdo_notify(self):
        nid = send_fdo_notification(
            "fdo notification (this process)",
            f"desktop-entry={APP_ID}. GNOME may still identify us via our window's PID.",
        )
        self.log(f"Sent fdo notification #{nid} with desktop-entry={APP_ID}")

    def on_fdo_notify_child(self):
        proc = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--notify-child"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        self.log(f"Child process {proc.pid} sent the notification; it stays until "
                 "the notification closes (at most 2 minutes)")
        GLib.child_watch_add(
            GLib.PRIORITY_DEFAULT, proc.pid,
            lambda _pid, _status: self.log("Child process: " + " / ".join(proc.stdout.read().split("\n")).strip(" /")),
        )

    def on_click_notify(self):
        # Most real apps send a "default" action; servers such as Noctalia
        # only make a notification clickable when it has one. On click the
        # server emits ActivationToken, then ActionInvoked, and the app raises
        # itself with that token.
        if not self.notify_sub:
            self.notify_sub = self.get_dbus_connection().signal_subscribe(
                None, NOTIFY_BUS, None, NOTIFY_PATH, None,
                Gio.DBusSignalFlags.NONE, self.on_notify_signal)
        nid = send_fdo_notification(
            "Notification with a click action",
            "Cover or minimize the probe window, then click this notification.",
            actions=["default", "Raise probe"],
        )
        self.click_ids[nid] = None
        self.log(f"Sent notification #{nid} with a default action; click it to raise the probe")

    def on_notify_signal(self, _conn, _sender, _path, _iface, signal, params):
        args = params.unpack()
        if not args or args[0] not in self.click_ids:
            return
        nid = args[0]
        if signal == "ActivationToken":
            self.click_ids[nid] = args[1]
        elif signal == "ActionInvoked":
            token = self.click_ids.get(nid)
            self.log(f"Notification #{nid} clicked (action {args[1]!r}, activation token: "
                     + ("yes" if token else "none") + "); raising the window")
            if token:
                self.window.set_startup_id(token)
            self.window.present()
        elif signal == "NotificationClosed":
            self.click_ids.pop(nid, None)

    def on_gnotification(self):
        n = Gio.Notification.new("GNotification")
        n.set_body(f"Sent with application ID {APP_ID}. On GNOME this is dropped "
                   "if no desktop file has that ID.")
        self.send_notification("probe", n)
        self.log("Sent GNotification (GNOME drops it silently if the ID has no desktop file)")

    # ---- 3: badges -------------------------------------------------------

    def emit_launcher_entry(self, props):
        uri = f"application://{DESKTOP_ID}"
        self.get_dbus_connection().emit_signal(
            None, LAUNCHER_ENTRY_PATH, LAUNCHER_ENTRY_IFACE, "Update",
            GLib.Variant("(sa{sv})", (uri, props)),
        )
        return uri

    def on_badge(self):
        self.badge_count += 1
        progress = (self.badge_count % 10) / 10 or 1.0
        uri = self.emit_launcher_entry({
            "count": GLib.Variant("x", self.badge_count),
            "count-visible": GLib.Variant("b", True),
            "progress": GLib.Variant("d", progress),
            "progress-visible": GLib.Variant("b", True),
        })
        self.log(f"LauncherEntry Update for {uri}: count={self.badge_count}, progress={progress:.1f}")

    def on_badge_clear(self):
        self.badge_count = 0
        uri = self.emit_launcher_entry({
            "count-visible": GLib.Variant("b", False),
            "progress-visible": GLib.Variant("b", False),
        })
        self.log(f"LauncherEntry cleared for {uri}")

    # ---- 4: URL schemes --------------------------------------------------

    def on_register_scheme(self):
        # Mirrors Electron's SetDefaultWebClient (shell/browser/browser_linux.cc).
        info = lookup_app_info(DESKTOP_ID)
        if not info:
            self.log(f"FAIL: no desktop file named {DESKTOP_ID}; "
                     "Electron's setAsDefaultProtocolClient returns false here")
            return
        info.set_as_default_for_type(f"x-scheme-handler/{RUNTIME_SCHEME}")
        self.log(f"Registered {info.get_filename()} as default for {RUNTIME_SCHEME}://")

    def on_check_scheme(self):
        # Mirrors Electron's IsDefaultProtocolClient: compare IDs.
        default = Gio.AppInfo.get_default_for_uri_scheme(RUNTIME_SCHEME)
        default_id = default.get_id() if default else None
        verdict = "YES" if default_id == DESKTOP_ID else "NO"
        self.log(f"Default for {RUNTIME_SCHEME}:// is {default_id!r}; "
                 f"equals {DESKTOP_ID}? {verdict}")

    def open_uri(self, scheme):
        uri = f"{scheme}://hello?sent={time.strftime('%H:%M:%S')}"
        handler = Gio.AppInfo.get_default_for_uri_scheme(scheme)
        if not handler:
            self.log(f"No handler for {scheme}:// - nothing would open")
            return
        Gio.AppInfo.launch_default_for_uri(uri, None)
        self.log(f"Asked {handler.get_id()} to open {uri}; expect 'Received URI' below")

    def on_open_runtime_uri(self):
        self.open_uri(RUNTIME_SCHEME)

    def on_open_static_uri(self):
        self.open_uri(STATIC_SCHEME)

    # ---- 5: portal -------------------------------------------------------

    def on_portal_register(self):
        # Register must be the first portal call on a connection, so use a
        # fresh private one rather than GTK's shared session connection.
        if self.portal_conn:
            self.portal_conn.close_sync(None)
        address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
        self.portal_conn = Gio.DBusConnection.new_for_address_sync(
            address,
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
            | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
            None, None,
        )
        try:
            self.portal_conn.call_sync(
                "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                "org.freedesktop.host.portal.Registry", "Register",
                GLib.Variant("(sa{sv})", (APP_ID, {})),
                None, Gio.DBusCallFlags.NONE, -1, None,
            )
            self.log(f"Portal accepted Register({APP_ID!r})")
        except GLib.Error as e:
            hint = ""
            if "UnknownInterface" in e.message or "UnknownMethod" in e.message:
                hint = " (xdg-desktop-portal is older than 1.19.1; no Registry)"
            self.log(f"Portal refused Register({APP_ID!r}): {e.message}{hint}")

    # ---- 6: MPRIS --------------------------------------------------------

    def on_mpris_toggle(self):
        if self.mpris_owner_id:
            self.stop_mpris()
            self.log("MPRIS player removed")
            return
        conn = self.get_dbus_connection()
        node = Gio.DBusNodeInfo.new_for_xml(MPRIS_XML)
        for iface in node.interfaces:
            # No property callbacks: GDBus then routes Properties.* to method_call.
            self.mpris_reg_ids.append(
                conn.register_object(MPRIS_PATH, iface, self.mpris_method, None, None))
        self.mpris_owner_id = Gio.bus_own_name_on_connection(
            conn, MPRIS_BUS, Gio.BusNameOwnerFlags.NONE, None, None)
        self.log(f"MPRIS player published as {MPRIS_BUS} with DesktopEntry={APP_ID}; "
                 "check the media widget's icon/name and its Raise action")

    def stop_mpris(self):
        conn = self.get_dbus_connection()
        for reg_id in self.mpris_reg_ids:
            conn.unregister_object(reg_id)
        self.mpris_reg_ids = []
        if self.mpris_owner_id:
            Gio.bus_unown_name(self.mpris_owner_id)
            self.mpris_owner_id = 0

    def mpris_props(self, iface):
        if iface == "org.mpris.MediaPlayer2":
            return {
                "CanQuit": GLib.Variant("b", False),
                "CanRaise": GLib.Variant("b", True),
                "HasTrackList": GLib.Variant("b", False),
                "Identity": GLib.Variant("s", NAME),
                "DesktopEntry": GLib.Variant("s", APP_ID),
                "SupportedUriSchemes": GLib.Variant("as", []),
                "SupportedMimeTypes": GLib.Variant("as", []),
            }
        return {
            "PlaybackStatus": GLib.Variant("s", "Playing" if self.mpris_playing else "Paused"),
            "Rate": GLib.Variant("d", 1.0),
            "Metadata": GLib.Variant("a{sv}", {
                "mpris:trackid": GLib.Variant("o", "/org/example/dtprobe/track/1"),
                "xesam:title": GLib.Variant("s", "Desktop ID Probe"),
                "xesam:artist": GLib.Variant("as", [f"DesktopEntry={APP_ID}"]),
            }),
            "Volume": GLib.Variant("d", 1.0),
            "Position": GLib.Variant("x", 0),
            "MinimumRate": GLib.Variant("d", 1.0),
            "MaximumRate": GLib.Variant("d", 1.0),
            "CanGoNext": GLib.Variant("b", False),
            "CanGoPrevious": GLib.Variant("b", False),
            "CanPlay": GLib.Variant("b", True),
            "CanPause": GLib.Variant("b", True),
            "CanSeek": GLib.Variant("b", False),
            "CanControl": GLib.Variant("b", True),
        }

    def mpris_method(self, conn, sender, path, iface, method, params, invocation):
        if iface == "org.freedesktop.DBus.Properties":
            if method == "Get":
                target, prop = params.unpack()
                value = self.mpris_props(target).get(prop)
                if value is None:
                    invocation.return_dbus_error(
                        "org.freedesktop.DBus.Error.UnknownProperty", prop)
                else:
                    invocation.return_value(GLib.Variant("(v)", (value,)))
            elif method == "GetAll":
                (target,) = params.unpack()
                invocation.return_value(GLib.Variant("(a{sv})", (self.mpris_props(target),)))
            else:
                invocation.return_value(None)  # ignore Set
            return
        if method == "Raise":
            self.log(f"MPRIS Raise from {sender}")
            self.window.present()
        elif method in ("PlayPause", "Play", "Pause"):
            self.mpris_playing = {"Play": True, "Pause": False}.get(method, not self.mpris_playing)
            conn.emit_signal(
                None, MPRIS_PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                GLib.Variant("(sa{sv}as)", (
                    "org.mpris.MediaPlayer2.Player",
                    {"PlaybackStatus": self.mpris_props("player")["PlaybackStatus"]},
                    [],
                )),
            )
            self.log(f"MPRIS {method} from {sender}")
        else:
            self.log(f"MPRIS {method} from {sender} (ignored)")
        invocation.return_value(None)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--notify-child"]:
        return notify_child_main()
    if args[:1] == ["--identity"]:
        print("\n".join(identity_report()))
        return 0
    # Sets the X11 WM_CLASS instance; GTK uses application_id for Wayland app_id.
    GLib.set_prgname(APP_ID)
    GLib.set_application_name(NAME)
    return Probe().run([sys.argv[0]] + args)


if __name__ == "__main__":
    sys.exit(main())
