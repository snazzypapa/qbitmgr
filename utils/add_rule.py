import logging

log = logging.getLogger("add_rule")


class RSSRule:
    def __init__(self, config, qbitclient, name, download_type):
        self.config = config
        self.qbitclient = qbitclient
        self.name = f"{download_type.upper()} - {name}"
        self.download_type = download_type
        self.specification = {
            "enabled": self.config["genres"][self.download_type]["rssRules"]["enabled"],
            "mustContain": f"{name} {self.config['genres'][self.download_type]['rssRules']['mustContain']}",
            "mustNotContain": self.config["genres"][self.download_type]["rssRules"][
                "mustNotContain"
            ],
            "useRegex": self.config["genres"][self.download_type]["rssRules"][
                "useRegex"
            ],
            "episodeFilter": self.config["genres"][self.download_type]["rssRules"][
                "episodeFilter"
            ],
            "smartFilter": self.config["genres"][self.download_type]["rssRules"][
                "smartFilter"
            ],
            "previouslyMatchedEpisodes": self.config["genres"][self.download_type][
                "rssRules"
            ]["previouslyMatchedEpisodes"],
            "affectedFeeds": self.config["genres"][self.download_type]["rssRules"][
                "affectedFeeds"
            ],
            "ignoreDays": self.config["genres"][self.download_type]["rssRules"][
                "ignoreDays"
            ],
            "lastMatch": self.config["genres"][self.download_type]["rssRules"][
                "lastMatch"
            ],
            "addPaused": self.config["genres"][self.download_type]["rssRules"][
                "addPaused"
            ],
            "assignedCategory": name,
            "savePath": self.config["genres"][self.download_type]["rssRules"][
                "savePath"
            ],
        }

    def add_rule(self):
        existing_rules = self.qbitclient.rss_rules()
        if self.name not in existing_rules:
            self.qbitclient.rss.set_rule(
                rule_name=self.name, rule_def=self.specification
            )
            log.info(f"Rule created: {self.name}")
        else:
            log.info(f"Rule already exists: {self.name}")
