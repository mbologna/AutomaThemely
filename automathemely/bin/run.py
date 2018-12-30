#!/usr/bin/env python3
import json
import pickle as pkl
import shutil
import sys
from datetime import datetime
import os
from pathlib import Path

import pytz
import tzlocal
import collections

import automathemely
from automathemely import __version__ as version
from automathemely.autoth_tools.utils import get_resource, get_local

import logging
logger = logging.getLogger(__name__)


def check_root():  # Prevent from being run as root for security and compatibility reasons
    if os.getuid() == 0:
        logger.critical('This shouldn\'t be run as root unless told otherwise!')
        sys.exit()


def update_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.Mapping):
            d[k] = update_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def main():

    check_root()

    #   Set workspace as the directory of the script, and import tools package
    workspace = Path(os.path.dirname(os.path.realpath(__file__)))
    os.chdir(str(workspace))
    sys.path.append('..')
    from automathemely import autoth_tools

    #   Test for settings file and if it doesn't exist copy it from defaults
    if not Path(get_local('user_settings.json')).is_file():
        shutil.copy2(get_resource('default_user_settings.json'), get_local('user_settings.json'))
        # By default notifications are enabled
        from automathemely import notifier_handler
        logging.getLogger().addHandler(notifier_handler)
        logger.info('No valid config file found, creating one...')
        automathemely.first_time_run = True

    try:
        with open(get_local('user_settings.json'), 'r') as f:
            user_settings = json.load(f)
    except json.decoder.JSONDecodeError:
        user_settings = dict()

    #   If settings files versions don't match (in case of an update for instance), overwrite values of
    #   default_settings with user_settings and use that instead
    if 'version' not in user_settings or user_settings['version'] != version:
        with open(get_resource('default_user_settings.json'), 'r') as f:
            default_settings = json.load(f)

        # Hardcoded attempt to try to import old structure to new structure...
        if user_settings['version'] <= 1.2:
            user_settings['themes']['gnome'] = dict()
            user_settings['themes']['gnome']['light'], user_settings['themes']['gnome']['dark'] = dict(), dict()
            user_settings['themes']['gnome']['light']['gtk'] = user_settings['themes'].pop('light', '')
            user_settings['themes']['gnome']['dark']['gtk'] = user_settings['themes'].pop('dark', '')

        user_settings = update_dict(default_settings, user_settings)
        user_settings['version'] = version

    if user_settings['misc']['notifications']:
        # Add the notification handler to the root logger
        from automathemely import notifier_handler
        logging.getLogger().addHandler(notifier_handler)

    #   If any argument is given, pass it/them to the arg manager module
    if len(sys.argv) > 1:
        autoth_tools.argmanager.main(user_settings)
        sys.exit()

    if not Path(get_local('sun_times')).is_file():
        logger.info('No valid times file found, creating one...')
        output = autoth_tools.updsuntimes.main(user_settings)
        if output:
            with open(get_local('sun_times'), 'wb') as file:
                pkl.dump(output, file, protocol=pkl.HIGHEST_PROTOCOL)

    local_tz = tzlocal.get_localzone()

    with open(get_local('sun_times'), 'rb') as file:
        sunrise, sunset = pkl.load(file)

    #   Convert to local timezone and ignore date
    now = datetime.now(pytz.utc).astimezone(local_tz).time()
    sunrise, sunset = sunrise.astimezone(local_tz).time(), sunset.astimezone(local_tz).time()

    if sunrise < now < sunset:
        theme_type = 'light'
    else:
        theme_type = 'dark'

    logger.debug('Not implemented yet!')

    # from gi.repository import Gio
    # g_settings = Gio.Settings.new('org.gnome.desktop.interface')
    #
    # change_theme = user_settings['themes'][theme_type]
    # current_theme = g_settings['gtk-theme']
    #
    # #   Check if there is a theme set to change to
    # if not change_theme:
    #     notify_print_exit('ERROR: No {} theme set'.format(theme_type), enabled=n_enabled, is_error=True)
    #
    # #   Check if theme is different before trying to do anything
    # if change_theme != current_theme:
    #     notify_print_exit('Switching to {} theme...'.format(theme_type), enabled=n_enabled, exit_after=False)
    #
    #     g_settings['gtk-theme'] = change_theme
    #
    #     #   Change extra themes
    #     for k, v in user_settings['extras'].items():
    #         if v['enabled']:
    #             is_error = autoth_tools.extratools.set_extra_theme(user_settings, k, theme_type)
    #             if is_error:
    #                 notify_print_exit('ERROR: {} {} is enabled but cannot be found/set'.format(v, theme_type),
    #                                   enabled=n_enabled, is_error=True, exit_after=False)


if __name__ == '__main__':
    main()
