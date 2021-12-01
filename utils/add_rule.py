import qbittorrentapi
import logging
import toml

log = logging.getLogger('add_rule')
config = toml.load('utils/config.toml')


class RSSRule:

    def __init__(self, name, download_type):
        self.name = f"{download_type.upper()} - {name}"
        self.download_type = download_type
        self.specification = {
            'enabled': config['genres'][self.download_type]['rssRules']['enabled'],
            'mustContain': name + " " + config['genres'][self.download_type]['rssRules']['mustContain'],
            'mustNotContain': config['genres'][self.download_type]['rssRules']['mustNotContain'],
            'useRegex': config['genres'][self.download_type]['rssRules']['useRegex'],
            'episodeFilter': config['genres'][self.download_type]['rssRules']['episodeFilter'],
            'smartFilter': config['genres'][self.download_type]['rssRules']['smartFilter'],
            'previouslyMatchedEpisodes': config['genres'][self.download_type]['rssRules']['previouslyMatchedEpisodes'],
            'affectedFeeds': config['genres'][self.download_type]['rssRules']['affectedFeeds'],
            'ignoreDays': config['genres'][self.download_type]['rssRules']['ignoreDays'],
            'lastMatch': config['genres'][self.download_type]['rssRules']['lastMatch'],
            'addPaused': config['genres'][self.download_type]['rssRules']['addPaused'],
            'assignedCategory': name,
            'savePath': config['genres'][self.download_type]['rssRules']['savePath']}

    def add_rule(self):
        client = qbittorrentapi.Client(host=config['host'], username=config['username'], password=config['password'])
        rules = client.rss_rules()
        # Create rule if does not already exist
        if self.name not in rules:
            client.rss.set_rule(rule_name=self.name, rule_def=self.specification)
            log.info(f'Rule created: {self.name}')
        else:
            log.info(f'Rule already exists: {self.name}')

