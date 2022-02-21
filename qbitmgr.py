import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import qbittorrentapi
import toml

from utils.add_cat import AddCategory
from utils.add_rule import RSSRule
from utils.cleaner import Cleaner
from utils.plex_scanner import PlexScanner
from utils.scheduler import Periodic
from utils.set_limits import ShareLimiter


def get_logger(name, log_level):
    log_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)-10s - %(name)-15s - %(funcName)-20s - %(message)s"
    )
    root_logger = logging.getLogger()
    logging.getLogger("requests").setLevel(logging.ERROR)
    logging.getLogger("qbittorrentapi").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.ERROR)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    logs_dir = Path(Path(__file__).parent, "logs")
    if not logs_dir.exists():
        logs_dir.mkdir()
    file_handler = TimedRotatingFileHandler(
        Path(logs_dir, f"{name}.log"),
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(log_level)
    return root_logger.getChild(name)


def get_args(genres):
    """parse cli arguments
    Returns: args object
    """
    parser = argparse.ArgumentParser(
        description="Create qbittorrent download categories and RSS auto download rules"
    )
    parser.add_argument(
        "cmd",
        default="",
        choices=["run", "add-cat", "add-rule", "clean", "set-limits"],
        help="Command to run",
    )
    parser.add_argument("-name", required=False, default="", help="Person's name")
    parser.add_argument(
        "-genre",
        required=False,
        default="",
        choices=genres,
        help="Type of download " + str(genres),
    )

    return parser.parse_args()


def periodic_tasks(
    share_limiter: ShareLimiter,
    cleaner: Cleaner,
    plex_scanner: PlexScanner,
    ignore_age: int,
):
    share_limiter.set_limits()
    cleaner.clean_seeds(ignore_age)
    plex_scanner.scan_if_needed()


def main():
    config = toml.load(Path(Path(__file__).parent, "config.toml"))
    args = get_args(list(config["genres"]))
    log = get_logger("qbitmgr", config["logLevel"])
    qbitclient = qbittorrentapi.Client(
        host=config["host"],
        username=config["username"],
        password=config["password"],
    )
    try:
        if args.cmd == "run":
            log.info(
                f"Scheduling tasks to run every: {config['checkInterval']} minutes"
            )
            share_limiter = ShareLimiter(config, qbitclient)
            cleaner = Cleaner(config, qbitclient)
            plex_scanner = PlexScanner(config, qbitclient)
            Periodic(
                config["checkInterval"] * 60,
                periodic_tasks,
                share_limiter,
                cleaner,
                plex_scanner,
                20,
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
            cleaner.clean_seeds(10)
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
