import os
import logging
import subprocess

log = logging.getLogger("plex_scanner")


class PlexScanner:
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
        """ """
        genre_path = os.path.dirname(save_path)
        for key, val in self.config["genres"].items():
            if val["moveToDir"] == genre_path:
                return key
        return False

    def plex_scan(self):
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