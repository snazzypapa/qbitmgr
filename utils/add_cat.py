import qbittorrentapi
import logging
import toml
import os

log = logging.getLogger('add_cat')
config = toml.load('utils/config.toml')


class AddCategory:

    def __init__(self, name, download_type):
        self.name = name
        self.download_type = download_type
        self.save_path = os.path.join(config['completeDownloadsDir'], self.download_type, self.name)

    def add_category(self):
        client = qbittorrentapi.Client(host=config['host'], username=config['username'], password=config['password'])
        categories = client.torrents_categories()
        if self.name not in categories:
            client.torrent_categories.create_category(self.name, self.save_path)
            log.info(f'Category created: {self.name}')
        else:
            log.info(f'Category already exists: {self.name}')
