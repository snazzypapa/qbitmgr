import sys
import toml
import time
import argparse
import threading
import logging
import qbittorrentapi
from pathlib import Path
from logging.handlers import RotatingFileHandler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.set_limits import ShareLimiter
from utils.add_cat import AddCategory
from utils.add_rule import RSSRule
from utils.cleaner import Cleaner
from utils.scheduler import Periodic
from utils.plex_scanner import PlexScanner

config = toml.load(Path(Path(__file__).parent, "config.toml"))
qbitclient = qbittorrentapi.Client(
    host=config["host"],
    username=config["username"],
    password=config["password"],
)

############################################################
# LOGGING
############################################################
def get_logger(name):
    """returns logger object
    Args:
        name: name of primary module
    Returns:
        child logger of given name
    """
    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)-10s - %(name)-15s - %(funcName)-20s - %(message)s"
    )
    root_logger = logging.getLogger()

    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("qbittorrentapi").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        f"{name}.log", maxBytes=1024 * 1024 * 5, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    root_logger.setLevel(config["logLevel"])
    return root_logger.getChild(name)


log = get_logger("qbitmgr")

############################################################
# WATCHDOG OBSERVER
############################################################
def on_created(event):
    """funcation to perfom when a new file/directory
    is created in the incomplete downloads directory
    presumably when a download starts
    """
    log.info("New incomplete download - setting limits")
    share_limiter = ShareLimiter(config, qbitclient)
    share_limiter.set_limits()


def on_deleted(event):
    """funcation to perfom when file/directory
    is deleted in the incomplete downloads directory
    presumably when a download finishes
    """
    time.sleep(20)
    log.info("Checking for completed seeds to process")
    cleaner = Cleaner(config, qbitclient)
    cleaner.clean_seeds(0)

    time.sleep(5)
    log.info("Download completed - initiating plex library scan, if needed")
    scanner = PlexScanner(config, qbitclient)
    scanner.scan_if_needed()


def run_observer():
    """function to run the directory observer
    to monitor for filesystem changes
    """
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
    """function to clean seeds"""
    cleaner = Cleaner(config, qbitclient)
    return cleaner.clean_seeds(ignore_age)


############################################################
# Argument Parsing
############################################################
def get_args():
    """parse cli arguments
    Returns: args object
    """
    genres = list(config["genres"])
    parser = argparse.ArgumentParser(
        description="Create qbittorrent download categories and RSS auto download rules"
    )
    parser.add_argument(
        "cmd",
        default="",
        choices=["run", "add-cat", "add-rule", "clean", "set-limits"],
        help="Command to run",
    )
    parser.add_argument("--name", required=False, default="", help="Person's name")
    parser.add_argument(
        "--genre",
        required=False,
        default="",
        choices=genres,
        help="Type of download " + str(genres),
    )

    return parser.parse_args()


############################################################
# Main
############################################################
def main():
    try:
        args = get_args()
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
            log.debug("User call to: add new RSS auto downloading rule")
            category = AddCategory(config, qbitclient, args.name, args.genre)
            category.add_category()
            rule = RSSRule(config, qbitclient, args.name, args.genre)
            rule.add_rule()
        elif args.cmd == "add-cat":
            log.debug("User call to: add new category")
            category = AddCategory(config, qbitclient, args.name, args.genre)
            category.add_category()
        elif args.cmd == "clean":
            log.debug("User call to: clean seeds")
            cleaner = Cleaner(config, qbitclient)
            cleaner.clean_seeds(120)
        elif args.cmd == "set-limits":
            log.debug("User call to: set limits")
            share_limiter = ShareLimiter(config, qbitclient)
            share_limiter.set_limits()
        else:
            print(
                "Command not recognized or incorrect flags given. Choose 'run,' 'clean,' or 'set-limits' with no flags or "
                "'add-rule'/'add-cat' with --genre and --name"
            )
    except KeyboardInterrupt:
        log.info("Qbitmgr was interrupted by Ctrl + C")
    except Exception as e:
        log.exception(f"Unexpected fatal exception occurred: {e}")


if __name__ == "__main__":
    main()
