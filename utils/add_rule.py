import logging

log = logging.getLogger("add_rule")


class RSSRule:
    def __init__(self, config, qbitclient, name, genre):
        self.qbitclient = qbitclient
        self.name = f"{genre.upper()} - {name}"
        self.specification = {
            "enabled": config["genres"][genre]["rssRules"]["enabled"],
            "mustContain": f"{name} {config['genres'][genre]['rssRules']['mustContain']}",
            "mustNotContain": config["genres"][genre]["rssRules"]["mustNotContain"],
            "useRegex": config["genres"][genre]["rssRules"]["useRegex"],
            "episodeFilter": config["genres"][genre]["rssRules"]["episodeFilter"],
            "smartFilter": config["genres"][genre]["rssRules"]["smartFilter"],
            "previouslyMatchedEpisodes": config["genres"][genre]["rssRules"][
                "previouslyMatchedEpisodes"
            ],
            "affectedFeeds": config["genres"][genre]["rssRules"]["affectedFeeds"],
            "ignoreDays": config["genres"][genre]["rssRules"]["ignoreDays"],
            "lastMatch": config["genres"][genre]["rssRules"]["lastMatch"],
            "addPaused": config["genres"][genre]["rssRules"]["addPaused"],
            "assignedCategory": self.name,
            "savePath": config["genres"][genre]["rssRules"]["savePath"],
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
