#!/bin/sh
# Install the probe's embedded .desktop file the way an integration script would,
# under its original name or a renamed one, so the two can be compared.
#
#   dtprobe-integrate.sh install APPIMAGE [--as NAME] [--subdir DIR] [--wmclass] [--hidden] [--rename-icon]
#   dtprobe-integrate.sh uninstall
#
#   --as NAME       install as NAME.desktop instead of the original name
#   --subdir DIR    install into applications/DIR/ (desktop file ID becomes DIR-NAME.desktop)
#   --wmclass       add StartupWMClass=<built-in ID>
#   --hidden        add NoDisplay=true (for the "hidden alias" experiment)
#   --rename-icon   install the icon as NAME too and point Icon= at it
#
# Run "install" more than once to have several entries side by side.
# "uninstall" removes everything this script installed and the
# dtprobe:// defaults the app may have registered.
set -eu

ORIG_ID=org.example.DesktopIdProbe
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APPS="$DATA/applications"
ICONS="$DATA/icons/hicolor/scalable/apps"
MANIFEST="$DATA/dtprobe-integrate.manifest"
MIMEAPPS="${XDG_CONFIG_HOME:-$HOME/.config}/mimeapps.list"

refresh() {
    update-desktop-database "$APPS" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$DATA/icons/hicolor" 2>/dev/null || true
}

usage() { sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

[ $# -ge 1 ] || usage
cmd=$1; shift

case "$cmd" in
install)
    [ $# -ge 1 ] || usage
    appimage=$(readlink -f "$1"); shift
    name=$ORIG_ID subdir= wmclass=no hidden=no rename_icon=no
    while [ $# -gt 0 ]; do
        case "$1" in
            --as) name=${2%.desktop}; shift 2 ;;
            --subdir) subdir=${2%/}; shift 2 ;;
            --wmclass) wmclass=yes; shift ;;
            --hidden) hidden=yes; shift ;;
            --rename-icon) rename_icon=yes; shift ;;
            *) usage ;;
        esac
    done

    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    (cd "$tmp" && "$appimage" --appimage-extract >/dev/null)
    src="$tmp/squashfs-root"
    mkdir -p "$APPS" "$ICONS"

    icon=$ORIG_ID
    [ "$rename_icon" = yes ] && icon=$name
    cp "$src/usr/share/icons/hicolor/scalable/apps/$ORIG_ID.svg" "$ICONS/$icon.svg"
    echo "$ICONS/$icon.svg" >> "$MANIFEST"

    dir="$APPS${subdir:+/$subdir}"
    mkdir -p "$dir"
    dest="$dir/$name.desktop"
    sed -e "s|^Exec=[^ ]*|Exec=\"$appimage\"|" -e "s|^Icon=.*|Icon=$icon|" \
        "$src/$ORIG_ID.desktop" > "$dest"
    [ "$wmclass" = yes ] && echo "StartupWMClass=$ORIG_ID" >> "$dest"
    [ "$hidden" = yes ] && echo "NoDisplay=true" >> "$dest"
    echo "$dest" >> "$MANIFEST"
    chmod +x "$dest"

    refresh
    echo "Installed $dest"
    echo "Desktop file ID: $(echo "${subdir:+$subdir/}$name.desktop" | tr / -)"
    sed 's/^/    /' "$dest"
    ;;
uninstall)
    if [ -f "$MANIFEST" ]; then
        sort -u "$MANIFEST" | while IFS= read -r f; do
            rm -f "$f" && echo "Removed $f"
            # drop subdirectories of applications/ that are now empty
            d=$(dirname "$f")
            while [ "${d#"$APPS"/}" != "$d" ] && rmdir "$d" 2>/dev/null; do d=$(dirname "$d"); done
        done
        rm -f "$MANIFEST"
    fi
    if [ -f "$MIMEAPPS" ]; then
        sed -i '/^x-scheme-handler\/dtprobe\(-static\)\{0,1\}=/d' "$MIMEAPPS"
    fi
    refresh
    ;;
*) usage ;;
esac
