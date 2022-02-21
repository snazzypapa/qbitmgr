import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class PlexScanner:
    """
    determines if plex should scan its libraries after a new download is completed
    and issues plex scan command
    """

    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient

    def get_completed_downloads(self):
        """get the completed downloads unyet processed"""
        completed_list = self.qbitclient.torrents_info(status_filter="completed")
        return [
            i
            for i in completed_list
            if "Processed" not in i.tags and self.get_genre(i.save_path)
        ]

    def get_genre(self, save_path):
        """gets genre of torrent
        Args:
            save_path: torrent save_path
        Returns:
            genre from config or False
        """
        genre_path = Path(save_path).parent
        for key, val in self.config["genres"].items():
            if Path(val["moveToDir"]) == genre_path:
                return key
        return False

    def plex_scan(self):
        """runs plex scan command as subprocess"""
        s_out = (
            subprocess.check_output(self.config["plexScanCommand"])
            .strip()
            .decode("UTF-8")
        )
        if "Got nothing for: It's All Connected" in s_out:
            log.debug(f"Plex scan success, stdout: '{s_out}'")
        else:
            log.debug(f"Plex scan failed, stdout: '{s_out}'")

    def scan_if_needed(self):
        """determines if scanning plex is required and runs command if needed"""
        completed_downloads = self.qbitclient.torrents_info(status_filter="completed")
        requires_scan = [
            i.hash
            for i in completed_downloads
            if self.get_genre(i.save_path)
            and self.config["genres"][self.get_genre(i.save_path)]["scanPlex"]
            and "Scanned" not in i.tags
        ]
        if requires_scan:
            log.debug("Running plex scan")
            self.plex_scan()
            self.qbitclient.torrents_add_tags(
                tags="Scanned", torrent_hashes=requires_scan
            )
        else:
            log.debug("No plex scan needed")
