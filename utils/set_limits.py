import logging

log = logging.getLogger("set_limits")


class LimitGroup:
    def __init__(self, config, group, names, hashes):
        self.group = group
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


def return_index_of_dict_in_list(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


class ShareLimiter:
    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient
        self.groups = list(config["shareLimits"])

    def assign_limit_groups(self):
        categories = [{"group": i, "names": [], "hashes": []} for i in self.groups]
        for torrent in self.qbitclient.torrents_info(status_filter="downloading"):
            if torrent.tags != "":
                continue
            if torrent.trackers[0]["msg"] == "This torrent is private":
                index = return_index_of_dict_in_list(categories, "group", "private")
            elif torrent.category in self.groups:
                index = return_index_of_dict_in_list(
                    categories, "group", torrent.category
                )
            else:
                index = return_index_of_dict_in_list(categories, "group", "default")
            categories[index]["hashes"].append(torrent.hash)
            categories[index]["names"].append(torrent.name)

        return [
            LimitGroup(self.config, **i) for i in categories if i["hashes"]
        ]  # The double splat converts dict to keyword arguments

    def set_limits(self):
        for limit_group in self.assign_limit_groups():
            self.qbitclient.torrents_set_share_limits(
                limit_group.ratio_limit,
                limit_group.seeding_time_limit,
                torrent_hashes=limit_group.hashes,
            )
            self.qbitclient.torrents_set_upload_limit(
                limit_group.upload_speed_limit, torrent_hashes=limit_group.hashes
            )
            self.qbitclient.torrents_add_tags(
                limit_group.tags, torrent_hashes=limit_group.hashes
            )
            log.info(f"Limit set to {limit_group.group} for {limit_group.names}")
            if limit_group.group != "private":
                continue
            self.qbitclient.torrents_top_priority(torrent_hashes=limit_group.hashes)
            log.info(f"Moved private torrent to top of queue: {limit_group.names}")
