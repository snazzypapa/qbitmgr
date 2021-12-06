import logging

log = logging.getLogger("add_cat")


class AddCategory:
    def __init__(self, config, qbitclient, name, genre):
        self.config = config
        self.qbitclient = qbitclient
        self.name = name
        self.genre = genre
        self.save_path = config["genres"][genre]["moveToDir"]

    def add_category(self):
        categories = self.qbitclient.torrents_categories()
        if self.name not in categories:
            self.qbitclient.torrent_categories.create_category(
                self.name, self.save_path
            )
            log.info(f"Category created: {self.name}")
        else:
            log.info(f"Category already exists: {self.name}")
