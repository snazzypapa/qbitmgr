import os
import glob
import toml
import time
import shutil
import logging
import qbittorrentapi

config = toml.load('utils/config.toml')
log = logging.getLogger('cleaner')
client = qbittorrentapi.Client(host=config['host'], username=config['username'], password=config['password'])


class CompletedSeed:

    def __init__(self, name, hash, content_path, save_path, completion_on):
        self.name = name
        self.hash = hash
        self.content_path = content_path # path to download
        self.save_path = os.path.normpath(save_path) # path to category, if in a category
        self.time_complete = self.elapsed_time(completion_on)
        self.genre = os.path.basename(os.path.dirname(self.save_path)) # returns one directory up from given directory
        self.delete_from_client = config['genres'][self.genre]['deleteFromClientWhenDone']

    @staticmethod
    def elapsed_time(unix_epoch_time):
        return time.mktime(time.gmtime()) - int(unix_epoch_time)

    @staticmethod
    def delete_path(path):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        if os.path.isfile(path):
            os.remove(path)
        log.debug(f'Deleted {path}')

    @staticmethod
    def delete_empty_dirs_recursively(path):
        for item in glob.glob(os.path.join(path, '**'), recursive=True):
            if not os.path.exists(item) or not os.path.isdir(item) or os.listdir(item):
                continue
            os.removedirs(item)
            log.debug(f'Deleted {item}')

    def delete_content(self):
        if self.delete_from_client:
            client.torrents_delete(delete_files=True, torrent_hashes=self.hash)
            log.debug(f'Deleted from client: {self.name}')
        else:
            self.delete_path(self.content_path)
            client.torrents_add_tags(tags='Deleted', torrent_hashes=self.hash)
            log.debug(f"Added 'Deleted' tag for {self.name}")


class Cleaner:

    def __init__(self):
        self.completed_list = client.torrents_info(status_filter='completed')
        self.seeding_list = client.torrents_info(status_filter='seeding')
        self.done_seeding_list = [i for i in self.completed_list if i not in self.seeding_list and 'Copied' in i.tags and 'Deleted' not in i.tags]

    def clean_seeds(self, ignore_age=120):
        if not self.done_seeding_list:
            log.info('No completed seeds to clean')
        else:
            for i in [CompletedSeed(i.name, i.hash, i.content_path, i.save_path, i.completion_on) for i in self.done_seeding_list]:
                if i.time_complete < ignore_age or i.genre not in list(config['genres']) or not config['genres'][i.genre]['moveToDir']:
                    continue
                i.delete_content()
                log.info(f'Deleted files for completed seed: {i.name}')
                i.delete_empty_dirs_recursively(i.save_path)
                log.debug(f'Deleted empty directories recursively upstream: {i.save_path}')
