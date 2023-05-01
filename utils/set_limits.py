import logging

log = logging.getLogger(__name__)


class LimitGroup:
    """group of torrents that share limits specified in config. Sets share limits and order in qbittorrent queue."""

    def __init__(self, config, qbitclient, group, names, hashes):
        self.group = group
        self.qbitclient = qbitclient
        self.names = names
        self.hashes = hashes
        self.ratio_limit = config["shareLimits"][self.group]["ratio_limit"]
        self.seeding_time_limit = config["shareLimits"][self.group][
            "seeding_time_limit"
        ]
        self.upload_speed_limit = config["shareLimits"][self.group][
            "upload_speed_limit"
        ]
        self.tags = config["shareLimits"][group]["tags"]
        self.priority_in_queue = config["shareLimits"][group]["priorityInQueue"]

    def set_group_limits(self):
        """sets share limits for group with qbitclient"""
        self.qbitclient.torrents_set_share_limits(
            self.ratio_limit,
            self.seeding_time_limit,
            torrent_hashes=self.hashes,
        )
        self.qbitclient.torrents_set_upload_limit(
            self.upload_speed_limit, torrent_hashes=self.hashes
        )
        self.qbitclient.torrents_add_tags(self.tags, torrent_hashes=self.hashes)
        log.info(f"Limit set to {self.group} for {self.names}")
        if self.priority_in_queue:
            self.qbitclient.torrents_top_priority(torrent_hashes=self.hashes)
            log.info(f"Moved priority torrents to top of queue: {self.names}")


class ShareLimiter:
    """matches downloading torrents to limit groups in config and creates LimitGroup objects"""

    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient

    @staticmethod
    def check_if_string_contains_any_match_term(match_terms, string_):
        """returns true if any of list of match_terms are present in a string
        Args:
            match_terms: list of terms that a string could contain
            string_: string within which to find match_terms

        Returns: bool
        """
        return any(term.lower() in string_.lower() for term in match_terms)

    def match_torrent_trackers(self, torrent):
        """matches torrent tracker to trackers in config
        Args:
            torrent: qbittorrentapi torrent obj
        Returns:
            key of shareLimit group or False
        """
        urls = [i.url for i in torrent.trackers]
        for key, val in self.config["shareLimits"].items():
            if self.check_if_string_contains_any_match_term(
                val["trackers"], " ".join(urls)
            ):
                return key
        return False

    def match_torrent_category(self, torrent):
        """matches torrent category to categories in config
        Args:
            torrent: qbittorrentapi torrent obj
        Returns:
            key of shareLimit group or False
        """
        for key, val in self.config["shareLimits"].items():
            if torrent.category in val["categories"]:
                return key
        return False

    def assign_torrents(self):
        """assigns torrents to share limits
        Args: None
        Returns:
            list of dicts representing each torrent
        """
        assigned_torrents = []
        downloading_torrents = self.qbitclient.torrents_info(
            status_filter="downloading"
        )
        for torrent in downloading_torrents:
            if torrent.tags != "":
                continue
            tracker_match = self.match_torrent_trackers(torrent)
            category_match = self.match_torrent_category(torrent)
            if tracker_match:
                assigned_torrents.append(
                    {"group": tracker_match, "name": torrent.name, "hash": torrent.hash}
                )
            elif category_match:
                assigned_torrents.append(
                    {
                        "group": category_match,
                        "name": torrent.name,
                        "hash": torrent.hash,
                    }
                )
            else:
                assigned_torrents.append(
                    {"group": "default", "name": torrent.name, "hash": torrent.hash}
                )
        return assigned_torrents

    def assign_limit_groups(self):
        """consolidates torrents from assign_torrents into groups
        Args: None
        Returns:
            list of LimitGroup objects
        """
        assigned_torrents = self.assign_torrents()
        groups = {i["group"] for i in assigned_torrents}
        group_list = [
            {
                "group": group,
                "hashes": [i["hash"] for i in assigned_torrents if i["group"] == group],
                "names": [i["name"] for i in assigned_torrents if i["group"] == group],
            }
            for group in groups
        ]
        return [LimitGroup(self.config, self.qbitclient, **i) for i in group_list]

    def set_limits(self):
        """creates LimitGroup objects and sets limits
        Args: None
        Returns: None
        """
        limit_groups = self.assign_limit_groups()
        if not limit_groups:
            log.debug("No downloads to set limits")
            return
        for limit_group in limit_groups:
            limit_group.set_group_limits()
