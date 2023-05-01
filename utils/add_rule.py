import logging

log = logging.getLogger(__name__)


class RSSRule:
    """creates new RSS auto downloading rule based on config"""

    def __init__(self, config, qbitclient, name: str, genre: str):
        self.qbitclient = qbitclient
        self.name = name
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
            "assignedCategory": f"{genre.upper()} - {name}",
            "savePath": config["genres"][genre]["rssRules"]["savePath"],
        }
        self.replace_separators = config["genres"][genre]["regexReplaceSeparators"]
        self.genre = genre

    def add_rule(self):
        """adds rule to qbittorrent if it does not already exist"""
        existing_rules = self.qbitclient.rss_rules()
        pre_existing = False
        rule_name = f"{self.genre.upper()} - {self.name}"
        if self.name in existing_rules:
            pre_existing = True
        if self.replace_separators:
            new_name = (
                self.replace_separators.join(self.name.split())
                + self.replace_separators
            )
            self.specification["mustContain"] = rf"\b{new_name}"
        self.qbitclient.rss.set_rule(rule_name=rule_name, rule_def=self.specification)
        if pre_existing:
            log.info(f"Updated rule: {rule_name}")
        else:
            log.info(f"Rule created: {rule_name}")
