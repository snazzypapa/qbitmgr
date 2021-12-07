import os
import time
import shutil
import logging
from pathlib import Path
from typing import Tuple

log = logging.getLogger("cleaner")


class CompletedSeed:
    def __init__(
        self,
        config,
        qbitclient,
        name,
        hash,
        content_path,
        save_path,
        category,
        completion_on,
        genre,
    ):
        self.qbitclient = qbitclient
        self.name = name
        self.hash = hash
        self.content_path = Path(
            content_path
        )  # path of torrent content (root path for multifile torrents, absolute file path for singlefile torrents)
        self.save_path = Path(save_path)  # path to category
        self.category = category
        self.time_complete = self.elapsed_seconds(completion_on)
        self.keep_dir_structure = config["genres"][genre]["keepDirStructure"]
        self.delete_from_client = config["genres"][genre]["deleteFromClientWhenDone"]
        self.file_exts_to_keep = tuple(config["genres"][genre]["keepSpecificFileTypes"])

    @staticmethod
    def elapsed_seconds(given_time_since_epoch):
        """seconds between now and given time in seconds
        elapsed_seconds(1636115660) --> 955
        """
        return time.time() - given_time_since_epoch

    @staticmethod
    def delete_non_filetype_recursively(dir_path, keep_extensions: Tuple):
        """deletes all files that do not have matching extension(s)
        Args:
            dir_path: path to directory to delete files from
            keep_extensions: tuple of file extensions including period ex: (".py", ".log")
        Returns:
            none
        """
        for root, dirs, files in os.walk(dir_path, topdown=False):
            [
                (Path(root, file).unlink(), log.debug(f"Deleted file: {file}"))
                for file in files
                if not file.endswith(keep_extensions)
            ]

    @staticmethod
    def delete_empty_dirs_recursively(dir_path):
        """deletes empty directories recursively
        Args:
            dir_path: top directory in tree
        Returns:
            none
        """
        for root, dirs, files in os.walk(dir_path, topdown=False):
            [
                (Path(root, dir).rmdir(), log.debug(f"Deleted empty directory: {dir}"))
                for dir in dirs
                if not any(Path(root, dir).iterdir())
            ]

    @staticmethod
    def move_all_files_in_tree_to_another_dir(source_dir, dest_dir):
        """moves all files in directory tree to a directory in another tree
        Args:
            source_dir: path to directory to get files
            dest_dir: path to directory to move files to
        Returns:
            none
        """
        for root, dirs, files in os.walk(source_dir, topdown=False):
            [
                (
                    shutil.move(Path(root, file), dest_dir),
                    log.debug(f"Moved file: {file}"),
                )
                for file in files
            ]

    @staticmethod
    def move_single_file(source, dest):
        shutil.move(source, dest)
        log.debug(f"Moved file: {source}")

    def delete_in_client(self):
        """deletes torrent from queue or adds 'Processed' tag"""
        if self.delete_from_client:
            self.qbitclient.torrents_delete(
                delete_files=False, torrent_hashes=self.hash
            )
            log.debug(f"Deleted from client: {self.name}")
        else:
            self.qbitclient.torrents_add_tags(
                tags="Processed", torrent_hashes=self.hash
            )
            log.debug(f"Added 'Processed' tag for {self.name}")

    def process_completed_seed(self, ignore_age):
        if self.time_complete < ignore_age:
            return
        if self.file_exts_to_keep and self.content_path.is_dir():
            self.delete_non_filetype_recursively(
                self.content_path, self.file_exts_to_keep
            )
        if not self.keep_dir_structure:
            if self.content_path.is_dir():
                self.move_all_files_in_tree_to_another_dir(
                    self.content_path, self.save_path
                )
                self.content_path.rmdir()
                log.debug(f"Deleted dir: {self.content_path}")
            if self.content_path.is_file():
                self.move_single_file(self.content_path, self.save_path)
                self.content_path.parent.rmdir()
                log.debug(f"Deleted dir for: {self.content_path}")
        self.delete_in_client()


class Cleaner:
    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient

    def get_completed_seeds(self):
        completed_list = self.qbitclient.torrents_info(status_filter="completed")
        seeding_list = self.qbitclient.torrents_info(status_filter="seeding")
        return [
            i
            for i in completed_list
            if i not in seeding_list
            and "Processed" not in i.tags
            and self.get_genre(i.save_path)
        ]

    def get_genre(self, save_path):
        """gets genre of torrent
        Args:
            save_path: torrent save_path
        Returns:
            genre from config or False
        """
        genre_path = Path(save_path).parent
        for key, val in self.config["genres"].items():
            if Path(val["moveToDir"]) == genre_path:
                return key
        return False

    def clean_seeds(self, ignore_age=120):
        if not self.get_completed_seeds():
            log.info("No completed seeds to clean")
        else:
            for i in [
                CompletedSeed(
                    self.config,
                    self.qbitclient,
                    i.name,
                    i.hash,
                    i.content_path,
                    i.save_path,
                    i.category,
                    i.completion_on,
                    self.get_genre(i.save_path),
                )
                for i in self.get_completed_seeds()
            ]:
                i.process_completed_seed(ignore_age)
