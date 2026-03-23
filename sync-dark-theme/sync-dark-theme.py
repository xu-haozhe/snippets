#!/usr/bin/env python3
import subprocess
import re
from gi.repository import Gio, GLib#type:ignore

THEME_MAP = {
    'Adwaita': 'Adwaita-dark',
    'Yaru': 'Yaru-dark',
    'Arc': 'Arc-Dark',
    'Nordic': 'Nordic-darker',
}

def get_base_theme(theme):
    return re.sub(r'-(dark|Dark|darker|Darker)$', '', theme)

def update_theme(settings, key):
    scheme = settings.get_string('color-scheme')
    current_theme = settings.get_string('gtk-theme')
    base_theme = get_base_theme(current_theme)
    
    if scheme == 'prefer-dark':
        new_theme = THEME_MAP.get(base_theme, f"{base_theme}-dark")
    else:
        new_theme = base_theme
    
    if current_theme != new_theme:
        print(f"切换主题: {current_theme} → {new_theme}")
        settings.set_string('gtk-theme', new_theme)

def main():
    settings = Gio.Settings.new('org.gnome.desktop.interface')
    update_theme(settings, None)
    settings.connect('changed::color-scheme', update_theme)
    loop = GLib.MainLoop()
    loop.run()

if __name__ == '__main__':
    main()