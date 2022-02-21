import logging
from pathlib import Path

log = logging.getLogger(__name__)


class AddCategory:
    """creates new category with save path based on config
    category names include the genre
    """

    def __init__(self, config, qbitclient, name, genre):
        self.qbitclient = qbitclient
        self.name = f"{genre.upper()} - {name}"
        self.save_path = Path(config["genres"][genre]["moveToDir"], name)

    def add_category(self):
        """adds download category"""
        categories = self.qbitclient.torrents_categories()
        if self.name not in categories:
            self.qbitclient.torrent_categories.create_category(
                self.name, self.save_path
            )
            log.info(f"Category created: {self.name}")
        else:
            log.info(f"Category already exists: {self.name}")
