import os
import time
import shutil
import logging
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
        self.config = config
        self.qbitclient = qbitclient
        self.name = name
        self.hash = hash
        self.content_path = content_path  # path of torrent content (root path for multifile torrents, absolute file path for singlefile torrents)
        self.save_path = os.path.normpath(save_path)  # path to category
        self.category = category
        self.time_complete = self.elapsed_seconds(completion_on)
        self.genre = genre
        self.keep_dir_structure = self.config["genres"][self.genre]["keepDirStructure"]
        self.delete_from_client = config["genres"][self.genre][
            "deleteFromClientWhenDone"
        ]
        self.file_exts_to_keep = tuple(
            self.config["genres"][self.genre]["keepSpecificFileTypes"]
        )

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
                (
                    os.remove(os.path.join(root, file)),
                    (log.debug(f"Deleted file: {file}")),
                )
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
                (
                    os.rmdir(os.path.join(root, dir)),
                    (log.debug(f"Deleted empty directory: {dir}")),
                )
                for dir in dirs
                if not os.listdir(os.path.join(root, dir))
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
                    shutil.move(os.path.join(root, file), dest_dir),
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
        """ """
        genre_path = os.path.dirname(save_path)
        for key, val in self.config["genres"].items():
            if val["moveToDir"] == genre_path:
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
                if i.time_complete < ignore_age:
                    continue
                if i.config["genres"][i.genre][
                    "keepSpecificFileTypes"
                ] and os.path.isdir(i.content_path):
                    i.delete_non_filetype_recursively(
                        i.content_path, i.file_exts_to_keep
                    )
                if not i.keep_dir_structure:
                    if os.path.isdir(i.content_path):
                        i.move_all_files_in_tree_to_another_dir(
                            i.content_path, i.save_path
                        )
                    if os.path.isfile(i.content_path):
                        i.move_single_file(i.content_path, i.save_path)
                    i.delete_empty_dirs_recursively(i.save_path)
                i.delete_in_client()
