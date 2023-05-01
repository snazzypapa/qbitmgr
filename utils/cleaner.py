import logging
import os
import shutil
import subprocess
import time
from pathlib import Path

log = logging.getLogger(__name__)


class CompletedSeed:
    """
    Object representing a download that has completed seeding
    determines if any post-processing of files is required and executes steps including:
        1. deleting unwanted files by file extension
        2. removing the directory structure of the download to put
            all files in one directory for the category
    """

    def __init__(
        self,
        config,
        qbitclient,
        name,
        hash,
        content_path,
        save_path,
        completion_on,
        genre,
    ):
        self.config = config
        self.genre = genre
        self.qbitclient = qbitclient
        self.name = name
        self.hash = hash
        self.content_path = Path(
            content_path
        )  # path of torrent content (root path for multi-file torrents, absolute file path for single-file torrents)
        self.save_path = Path(save_path)
        self.time_complete = self.elapsed_seconds(completion_on)
        self.keep_dir_structure = config["genres"][genre]["keepDirStructure"]
        self.delete_from_client = config["genres"][genre]["deleteFromClientWhenDone"]
        self.file_exts_to_keep = tuple(config["genres"][genre]["keepSpecificFileTypes"])
        log.debug(f"{self.name} genre: {genre}")

    @staticmethod
    def elapsed_seconds(given_time_since_epoch):
        """seconds between now and given time in seconds
        elapsed_seconds(1636115660) --> 955
        """
        return time.time() - given_time_since_epoch

    @staticmethod
    def delete_non_filetype_recursively(dir_path, keep_extensions: tuple):
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
    def move_all_files_to_another_dir(source_dir: Path, dest_dir: Path):
        """moves all files in directory tree to a directory in another tree
        Args:
            source_dir: path to directory to get files
            dest_dir: path to directory to move files to
        Returns:
            none
        """
        for fs_obj in source_dir.rglob("*"):
            if fs_obj.is_file():
                new_path = Path(dest_dir, fs_obj.name)
                if new_path.exists():
                    log.info(
                        f"Cannot move to {dest_dir}, because path already exists for: {fs_obj.name}"
                    )
                    continue
                fs_obj.rename(new_path)

    @staticmethod
    def move_single_file(source, dest):
        """moves single file from source to destination
        Args:
            source: source path
            dest: destination path
        Returns:
            None
        """
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
        """performs class functions based on config.
        ignores downloads older than specified time to avoid race conditions with periodic cleaner
        Args:
            ignore_age: time in seconds since download completion to ignore
        Returns:
            None
        """
        if self.time_complete < ignore_age:
            return
        if self.file_exts_to_keep and self.content_path.is_dir():
            self.delete_non_filetype_recursively(
                self.content_path, self.file_exts_to_keep
            )
        if not self.keep_dir_structure:
            if self.content_path.is_dir():
                self.move_all_files_to_another_dir(self.content_path, self.save_path)
                if not any(
                    self.content_path.iterdir()
                ):  # if content path is empty, delete it
                    self.content_path.rmdir()
                    log.debug(f"Deleted dir: {self.content_path}")
            if self.content_path.is_file():
                self.move_single_file(self.content_path, self.save_path)
                self.content_path.parent.rmdir()
                log.debug(f"Deleted dir for: {self.content_path}")
        self.delete_in_client()  # this occurs always now. it should handle cases when not able to move files
        if self.config["genres"][self.genre]["scriptOnDone"]:
            log.debug("Running subprocess for completed seed")
            subprocess.run(self.config["genres"][self.genre]["scriptOnDone"])

        log.info(f"Processed completed seed: {self.name}")


class Cleaner:
    """
    reviews completed seeds for post-processing steps and creates CompletedSeed objects
    """

    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient

    def get_completed_seeds(self):
        """returns list of torrents that are done seeding
        Args:
            None
        Returns:
            list of completed seeds
        """
        completed_list = self.qbitclient.torrents_info(status_filter="completed")
        seeding_list = self.qbitclient.torrents_info(status_filter="seeding")
        return [
            i
            for i in completed_list
            if i not in seeding_list
            and "Processed" not in i.tags
            and self.get_genre(i.save_path, i.category)
        ]

    def get_genre(self, save_path, category: str):
        """gets genre of torrent
        first tries to match the torrent's category to a named genre
        then tries to match based on save path

        Args:
            save_path: torrent save_path
        Returns:
            genre from config or False
        """
        genre_path = Path(save_path).parent
        for key, val in self.config["genres"].items():
            if key == category:
                return key
        for key, val in self.config["genres"].items():
            if Path(val["moveToDir"]) == genre_path:
                return key
        return False

    def clean_seeds(self, ignore_age=120):
        """creates objects and tells them to process themselves"""
        if not self.get_completed_seeds():
            return log.debug("No completed seeds to clean")
        for i in [
            CompletedSeed(
                self.config,
                self.qbitclient,
                i.name,
                i.hash,
                i.content_path,
                i.save_path,
                i.completion_on,
                self.get_genre(i.save_path, i.category),
            )
            for i in self.get_completed_seeds()
        ]:
            i.process_completed_seed(ignore_age)
