#!/usr/bin/python3
import os
import sys
import toml
import time
import argparse
import threading
import logging
from logging.handlers import RotatingFileHandler
from utils.set_limits import set_limits
from utils.add_cat import AddCategory
from utils.add_rule import RSSRule
from utils.mover import move
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

config = toml.load('utils/config.toml')

# Logging
log_formatter = logging.Formatter(
    u'%(asctime)s - %(levelname)-10s - %(name)-20s - %(funcName)-30s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(config['log_level'])

# Set schedule logger to ERROR
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("qbittorrentapi").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("watchdog").setLevel(logging.WARNING)

# Set console logger
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# Set file logger
file_handler = RotatingFileHandler(
    'qbitmgr.log',
    maxBytes=1024 * 1024 * 5,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Set chosen logging level
root_logger.setLevel(logging.DEBUG)
log = root_logger.getChild('qbitmgr')

# Functions to execute on directory changes
def on_created(event):
    log.info('File/directory created')
    time.sleep(3)
    set_limits()


def on_deleted(event):
    log.info('File/directory deleted - moving files')
    time.sleep(10)
    move()


def run_observer():
    event_handler = FileSystemEventHandler()

    # Calling functions
    event_handler.on_created = on_created
    event_handler.on_deleted = on_deleted

    # Path to monitor
    path = config['incompleteDownloadsDir']
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)

    # Start watchdog observer
    observer.start()
    log.info('Directory watcher started')
    try:
        while observer.is_alive():
            observer.join()
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    observer_thread = threading.Thread(target=run_observer, args=())
    observer_thread.daemon = False

    genres = list(config['genres'])

    #   Parse arguments and run functions
    parser = argparse.ArgumentParser(description='Create qbittorrent download categories and RSS auto download rules')
    parser.add_argument('--name', required=False, default='', help="Person's name")
    parser.add_argument('--genre', required=False, default='', choices=genres, help='Type of download ' + str(genres))
    parser.add_argument('cmd', default='', choices=['add-rule', 'add-cat', 'set-limits', 'move', 'watch'], help='Command to run')

    args = parser.parse_args()
    name = args.name
    download_type = args.genre
    cmd = args.cmd

    # Determine which function to run based on arguments
    if cmd == 'set-limits':
        log.info('User call to: set limits')
        set_limits()
    elif cmd == 'watch':
        log.info('Starting directory watcher')
        observer_thread.start()
    elif cmd == 'add-rule':
        log.info('User call to: add new RSS auto downloading rule')
        category = AddCategory(name, download_type)
        category.add_category()
        rule = RSSRule(name, download_type)
        rule.add_rule()
    elif cmd == 'add-cat':
        log.info('User call to: add new category')
        category = AddCategory(name, download_type)
        category.add_category()
    elif cmd == 'move':
        log.info('User call to: move completed downloads')
        move()
    else:
        print(
            "Command not recognized or incorrect flags given. Choose 'set_limits,' 'move,' or 'watch' with no flags or "
            "'add_rule'/'add_cat' with --genre and --name")
