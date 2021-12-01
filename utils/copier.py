import os
import glob
import time
import shutil
import logging
import subprocess
from typing import Tuple
from fnmatch import filter


log = logging.getLogger("copier")


class CompletedDownload:
    def __init__(self, config, name, hash, content_path, save_path, category):
        self.config = config
        self.name = name
        self.hash = hash
        self.content_path = content_path
        self.save_path = os.path.normpath(save_path)  # path to category
        self.category = category
        self.genre = os.path.basename(
            os.path.dirname(self.save_path)
        )  # returns one directory up from given directory
        self.destination_dir = os.path.join(
            self.config["genres"][self.genre]["moveToDir"], self.category
        )
        self.keep_dir_structure = self.config["genres"][self.genre]["keepDirStructure"]
        self.file_exts_to_keep = (
            ("*")
            if not self.config["genres"][self.genre]["keepSpecificFileTypes"]
            else tuple(self.config["genres"][self.genre]["keepSpecificFileTypes"])
        )
        self.scan_plex = self.config["genres"][self.genre]["scanPlex"]
        self.plex_command = self.config["plexScanCommand"]
        self.files_to_copy = []
        self.copied_paths = []

    def list_files_with_exts(self):
        """gets list of files that have the extensions specified - defaults to all if file_exts_to_keep is ('*')"""
        files = []
        if os.path.isfile(self.content_path):
            extensions_mod = tuple(i.replace("*", "") for i in self.file_exts_to_keep)
            if self.content_path.endswith(extensions_mod):
                files.append(self.content_path)
                return self.files_to_copy.extend(files)
        for ext in self.file_exts_to_keep:
            files.extend(
                glob.iglob(
                    os.path.join(glob.escape(self.content_path), "**", ext),
                    recursive=True,
                )
            )
        return self.files_to_copy.extend(files)

    def link_or_copy_file(self, source, destination_dir):
        file_name = os.path.basename(source)
        destination_path = os.path.join(destination_dir, file_name)
        try:
            os.link(source, destination_path)
            log.debug(f"Hard linked {file_name} to {destination_dir}")
        except:
            shutil.copy2(source, destination_path)
            log.debug(f"Hard link failed, copied {file_name} to {destination_dir}")
        finally:
            return self.copied_paths.append(destination_path)

    def copy_files_only(self):
        os.makedirs(self.destination_dir, exist_ok=True)
        for i in self.files_to_copy:
            self.link_or_copy_file(i, self.destination_dir)

    @staticmethod
    def include_patterns(patterns: Tuple):
        """Arguments define a sequence of glob-style patterns that are used to specify what files to NOT ignore.
        Creates and returns a function that determines this for each directory
        in the file hierarchy rooted at the source directory when used with shutil.copytree().
        https://stackoverflow.com/q/42487578/16625038
        """

        def _ignore_patterns(path, names):
            keep = {name for pattern in patterns for name in filter(names, pattern)}
            return {
                name
                for name in names
                if name not in keep and not os.path.isdir(os.path.join(path, name))
            }

        return _ignore_patterns

    def link_or_copy_tree(self, source, destination_dir):
        dir_name = os.path.basename(source)
        destination_path = os.path.join(destination_dir, dir_name)
        try:
            shutil.copytree(
                source,
                destination_path,
                ignore=self.include_patterns(self.file_exts_to_keep),
                copy_function=os.link,
            )
            log.debug(f"Hard linked {dir_name} to {destination_dir}")
        except:
            shutil.copytree(
                source,
                destination_path,
                ignore=self.include_patterns(self.file_exts_to_keep),
            )
            log.debug(f"Hard link failed, copied {dir_name} to {destination_dir}")
        finally:
            return self.copied_paths.append(destination_path)

    def copy_subtree(self):
        if not os.path.isfile(self.content_path):
            log.debug("Content path is not file, copying tree")
            return self.link_or_copy_tree(self.content_path, self.destination_dir)

        if str(os.path.dirname(self.content_path)) == str(
            self.save_path
        ):  # then the download is a single file without a directory
            os.makedirs(self.destination_dir, exist_ok=True)
            return self.copy_files_only()
        else:
            parent_dir = self.get_one_fsobj_below(
                self.content_path, self.save_path
            )  # solves edge case for single file downloads in mutliple layers of directories
            return self.link_or_copy_tree(parent_dir, self.destination_dir)

    @staticmethod
    def get_one_fsobj_below(fsobject, parentdir):
        """gets highest in a paths ancestry before the specified parent directory. can return fsobject if file is in parentdir"""
        while os.path.dirname(fsobject) != parentdir:
            fsobject = os.path.dirname(fsobject)
        return fsobject

    def plex_scan(self):
        time.sleep(5)
        s = subprocess.check_output(self.plex_command).strip().decode("UTF-8")
        if "Got nothing for: It's All Connected" in s:
            log.info(f"Plex scan succes, stdout: '{s}'")
        else:
            log.info(f"Plex scan failed, stdout: '{s}'")

    def check_copy_completed(self):
        files_to_copy_count = len(self.files_to_copy)
        copied_paths_count = len(self.copied_paths)
        log.debug(
            f"copied_paths_count: {copied_paths_count}. files_to_copy_count: {files_to_copy_count}. Difference: {copied_paths_count - files_to_copy_count}"
        )
        if copied_paths_count < files_to_copy_count:
            log.info("Exiting: copied fewer files than supposed to")
            return False
        for path in self.copied_paths:
            if os.path.exists(path):
                continue
            log.info(f"Exiting: path not copied: {path}")
            return False
        return True

    def delete_empty_dirs_recursively(self, path):
        for item in glob.iglob(os.path.join(path, "**"), recursive=True):
            if not os.path.exists(item) or not os.path.isdir(item) or os.listdir(item):
                continue
            os.rmdir(item)
            log.debug(f"Deleted empty directory: {item}")


class Copier:
    def __init__(self, config, qbitclient):
        self.config = config
        self.qbitclient = qbitclient
        self.to_copy = self.identify_completes_to_copy()

    def identify_completes_to_copy(self):
        completed_torrents = [
            i
            for i in self.qbitclient.torrents_info(status_filter="completed")
            if "Copied" not in i.tags
        ]
        completed_objs = [
            CompletedDownload(
                self.config, i.name, i.hash, i.content_path, i.save_path, i.category
            )
            for i in completed_torrents
        ]
        return [
            i
            for i in completed_objs
            if i.genre in list(self.config["genres"])
            and self.config["genres"][i.genre]["moveToDir"]
        ]

    def copy_completes(self):
        if not self.to_copy:
            log.info("No completed downloads to copy")
            return
        for i in self.to_copy:
            i.list_files_with_exts()
            if not i.files_to_copy:
                log.info(
                    f"Completed download had no files with correct extension(s) to copy: {i.name}"
                )
                continue
            if i.keep_dir_structure:
                i.copy_subtree()
                log.info(f"Copied subtrees for: {i.name}")
            if not i.keep_dir_structure:
                i.copy_files_only()
                log.info(f"Copied files for: {i.name}")
            if i.check_copy_completed():
                self.qbitclient.torrents_add_tags(tags="Copied", torrent_hashes=i.hash)
            i.delete_empty_dirs_recursively(i.destination_dir)
            if i.scan_plex:
                log.info(f"Running Plex scan subprocess for {i.name}")
                i.plex_scan()
