import os
import glob
import toml
import time
import shutil
import logging
from .background_subprocess import BackgroundPopen

config = toml.load('utils/config.toml')
log = logging.getLogger('mover')


class Mover:

    def __init__(self, genre):
        self.genre = genre
        self.source_dir = os.path.join(config['completeDownloadsDir'], self.genre)
        self.destination_dir = config['genres'][self.genre]['moveToDir']
        self.keep_dir_structure = config['genres'][self.genre]['keepDirStructure']
        self.file_exts_to_keep = tuple(config['genres'][self.genre]['keepSpecificFileTypes'])
        self.scan_plex = config['genres'][self.genre]['scanPlex']
        self.plex_command = config['plexScanCommand']
        self.background_process = BackgroundPopen

    def is_dir_empty(self, path):
        if not os.path.isdir(path):
            return 'DNE or not directory'
        return not os.listdir(path)

    def delete_non_filetype(self, path, extensions: tuple):
        contents = glob.glob(os.path.join(path, '**'), recursive=True)
        for item in contents:
            if os.path.isfile(item) and not item.endswith(extensions):
                os.remove(item)
                log.debug(f'Deleted {item}')

    def delete_empty_dirs(self, path):
        contents = glob.glob(os.path.join(path, '**'), recursive=True)
        for item in contents:
            if not os.path.exists(item) or not os.path.isdir(item) or os.listdir(item):
                continue
            os.removedirs(item)
            log.debug(f'Deleted {item}')

    def get_subdir_paths_names(self, path):
        if os.path.isdir(path):
            paths = [f.path for f in os.scandir(path) if f.is_dir()]
            names = [f.name for f in os.scandir(path) if f.is_dir()]
            return paths, names # returns tuple
        return 'DNE or not directory'

    def move_subtrees(self):
        source_subdirs = self.get_subdir_paths_names(self.source_dir)
        if source_subdirs:
            log.info(f'Moving contents of directory: {self.source_dir}')
            for source_subdir_path, subdir_name in zip(*source_subdirs): # * unpacks tuple
                os.makedirs(os.path.join(self.destination_dir, subdir_name), exist_ok=True) # Make subdir if needed
                items = os.listdir(source_subdir_path)
                for item in items:
                    shutil.move(os.path.join(source_subdir_path, item), os.path.join(self.destination_dir, subdir_name, item))
                    log.debug(f'Moved {item} to {os.path.join(self.destination_dir, subdir_name)}')
            for source_subdir_path in source_subdirs[0]:
                shutil.rmtree(source_subdir_path, ignore_errors=True)
                log.info(f'Deleted {source_subdir_path}')
        else:
            log.info(f'Nothing to move - directory DNE: {self.source_dir}')

    def move_files_only(self):
        source_subdirs = self.get_subdir_paths_names(self.source_dir)
        if source_subdirs:
            log.info(f'Moving files from: {self.source_dir}')
            for source_subdir_path, subdir_name in zip(*source_subdirs):
                os.makedirs(os.path.join(self.destination_dir, subdir_name), exist_ok=True)
                for i in glob.glob(os.path.join(source_subdir_path, '**'), recursive=True):
                    if os.path.isfile(i):
                        filename = os.path.basename(i)
                        shutil.move(i, os.path.join(self.destination_dir, subdir_name, filename))
                        log.debug(f'Moved {i} to {os.path.join(self.destination_dir, subdir_name)}')
            for source_subdir_path in source_subdirs[0]:
                shutil.rmtree(source_subdir_path, ignore_errors=True)
                log.info(f'Deleted {source_subdir_path}')
        else:
            log.info(f'Nothing to move - directory DNE: {self.source_dir}')

    def plex_scan(self):
        return BackgroundPopen(log.info, log.info, self.plex_command, bufsize=1)


def move():
    genres = list(config['genres'])
    for i in [Mover(i) for i in genres]:
        if not i.destination_dir:
            continue
        if i.is_dir_empty(i.source_dir):
            log.info(f'Directory is empty: {i.genre}')
            continue
        if i.file_exts_to_keep:
            i.delete_non_filetype(i.source_dir, i.file_exts_to_keep)
            log.info(f'Deleted extra files for: {i.genre}')
        if i.keep_dir_structure:
            i.move_subtrees()
            log.info(f'Moved subtrees for: {i.genre}')
        if not i.keep_dir_structure:
            i.move_files_only()
            log.info(f'Removed directory structure and moved files for: {i.genre}')
        if i.scan_plex:
            time.sleep(5)
            log.info(f'Running Plex scan subprocess for {i.genre}')
            i.plex_scan()

