#!/usr/bin/python3
import os
import sys
import toml
import time
import argparse
import threading
import logging
import qbittorrentapi
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.set_limits import ShareLimiter
from utils.add_cat import AddCategory
from utils.add_rule import RSSRule
from utils.cleaner import Cleaner
from utils.scheduler import Periodic
from utils.copier import Copier

config = toml.load(os.path.join(os.path.dirname(__file__), "config.toml"))

############################################################
# LOGGING
############################################################
log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)-10s - %(name)-15s - %(funcName)-20s - %(message)s"
)
root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)

# Set module logging to WARNING
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
    "qbitmgr.log", maxBytes=1024 * 1024 * 5, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Set chosen logging level
root_logger.setLevel(config["logLevel"])
log = root_logger.getChild("qbitmgr")

############################################################
# WATCHDOG OBSERVER
############################################################
def on_created(event):
    log.info("New incomplete download - setting limits")
    share_limiter = ShareLimiter(config, qbitclient)
    share_limiter.set_limits()


def on_deleted(event):
    time.sleep(10)
    log.info("Download completed - copying files")
    copier = Copier()
    copier.copy_completes()

    time.sleep(3)
    log.info("Checking downloads directory for completed seeds")
    cleaner = Cleaner()
    cleaner.clean_seeds(0)


def run_observer():
    event_handler = FileSystemEventHandler()

    # Calling functions
    event_handler.on_created = on_created
    event_handler.on_deleted = on_deleted

    # Path to monitor
    path = config["incompleteDownloadsDir"]
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)

    # Start watchdog observer
    observer.start()
    log.info("Directory watcher started")
    try:
        while observer.is_alive():
            observer.join()
    finally:
        observer.stop()
        observer.join()


############################################################
# Completed Seed Cleaner
############################################################
def run_cleaner(ignore_age):
    cleaner = Cleaner()
    return cleaner.clean_seeds(ignore_age)


############################################################
# Argument Parsing
############################################################
def get_args():
    genres = list(config["genres"])
    parser = argparse.ArgumentParser(
        description="Create qbittorrent download categories and RSS auto download rules"
    )
    parser.add_argument("--name", required=False, default="", help="Person's name")
    parser.add_argument(
        "--genre",
        required=False,
        default="",
        choices=genres,
        help="Type of download " + str(genres),
    )
    parser.add_argument(
        "cmd",
        default="",
        choices=["run", "add-rule", "add-cat", "copy", "clean", "set-limits"],
        help="Command to run",
    )

    return parser.parse_args()


############################################################
# Main
############################################################
if __name__ == "__main__":

    # Run chosen mode
    try:
        args = get_args()
        qbitclient = qbittorrentapi.Client(
            host=config["host"],
            username=config["username"],
            password=config["password"],
        )
        if args.cmd == "run":
            observer_thread = threading.Thread(target=run_observer, args=())
            observer_thread.daemon = False
            log.debug("Starting directory watcher")
            observer_thread.start()
            log.info(
                f"Scheduling cleaner to run every: {config['cleanerInterval']} minutes"
            )
            scheduled_cleaner = Periodic(
                config["cleanerInterval"] * 60, run_cleaner, 120
            )
        elif args.cmd == "add-rule":
            log.info("User call to: add new RSS auto downloading rule")
            category = AddCategory(config, qbitclient, args.name, args.genre)
            category.add_category()
            rule = RSSRule(config, qbitclient, args.name, args.genre)
            rule.add_rule()
        elif args.cmd == "add-cat":
            log.info("User call to: add new category")
            category = AddCategory(config, qbitclient, args.name, args.genre)
            category.add_category()
        elif args.cmd == "copy":
            log.info("User call to: copy files")
            copier = Copier(config, qbitclient)
            copier.copy_completes()
        elif args.cmd == "clean":
            log.info("User call to: clean seeds")
            cleaner = Cleaner(config, qbitclient)
            cleaner.clean_seeds(120)
        elif args.cmd == "set-limits":
            log.info("User call to: set limits")
            share_limiter = ShareLimiter(config, qbitclient)
            share_limiter.set_limits()
        else:
            print(
                "Command not recognized or incorrect flags given. Choose 'run,' 'copy,' or 'set-limits' with no flags or "
                "'add-rule'/'add-cat' with --genre and --name"
            )
    except KeyboardInterrupt:
        scheduled_cleaner.stop()
        log.info("Qbitmgr was interrupted by Ctrl + C")
    except Exception:
        log.exception("Unexpected fatal exception occurred: ")
