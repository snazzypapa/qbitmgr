# qbitmgr
Automatically manage qbittorrent share limits, RSS rules, and file moves.

Supports qBittorrent v4.1.0+ (i.e. Web API v2.0+). Currently supports up to qBittorrent [v4.3.8](https://github.com/qbittorrent/qBittorrent/releases/tag/release-4.3.8) (Web API v2.8.2) released on Aug 28, 2021.

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-blue.svg?style=flat-square)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%203-blue.svg?style=flat-square)](https://github.com/snazzypapa/qbitmgr/blob/master/LICENSE.md)

---



# Introduction

Qbitmgr has 3 main functions:

1. Automaticly set upload speed and seeding limits for torrents in qbittorrent based on trackers and categories.

2. Automatically manage files once completed: delete unwanted files by file extension and move files based on genre/category.

3. Add templated RSS auto download rules and download categories from the command line.


# Requirements

1. Ubuntu/Debian OS (likely works woth other OSes but have not tried).

2. Qbittorrent with WebUI accessible on localhost

3. Automatic download handling turned on, torrent content layout set to create subfolder, and an incomplete downloads directory set in qbittorrent preferences. 

4. Python 3.6 or higher (`sudo apt install python3 python3-pip`).

5. Required Python modules (see below).


# Installation

1. Clone the Qbitmgr repo.

   ```
   sudo git clone https://github.com/snazzypapa/qbitmgr /opt/qbitmgr
   ```

1. Fix permissions of the Qbitmgr folder (replace `user`/`group` with your info; run `id` to check).

   ```
   sudo chown -R user:group /opt/qbitmgr
   ```

1. Go into the Qbitmgr folder.

   ```
   cd /opt/qbitmgr
   ```

1. Install Python PIP.

   ```
   sudo apt-get install python3-pip
   ```

1. Install the required python modules.

   ```
   sudo python3 -m pip install -r requirements.txt
   ```

1. Rename the config file and edit it.

   ```
   mv config.toml.example config.toml && nano config.toml
   ```

1. To have Qbitmgr run automatically do the following:

   ```
   mv /opt/qbitmgr/systemd/qbitmgr_watcher.service.example /opt/qbitmgr/systemd/qbitmgr_watcher.service 
   sudo cp /opt/qbitmgr/systemd/qbitmgr_watcher.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable qbitmgr_watcher.service
   sudo systemctl start qbitmgr_watcher.service
   ```   

# Usage

## Automatic

A filesystem watcher service looks for changes to the incomplete downloads directory and sets share limits and moves files according to the config file. This is set up via the final step of the installation process.

## Manual (CLI)

Command:
```
qbitmgr
```

```
usage: qbitmgr {"run", "add-cat", "add-rule", "clean", "set-limits"} [-name] [-genre]
                 
positional arguments:
  {"run", "add-cat", "add-rule", "clean", "set-limits"}
                        "run": starts filesystem watcher for new and completed torrents
                        "add-cat": adds new category to qbittorrent and sets completed download directory to specified genre. Requires '-genre' and '-name' keyword arguments.
                        "add-rule": adds new categgory and new RSS auto download rule to qbittorrent and sets completed download directory to specified genre. Requires '-genre' and '-name' keyword arguments.
                        "clean":  checks for completed seeds and deletes extra files and moves files as specified in config   
                        "set-limits": sets share limits for torrents in qbittorrent via the qbittorrent API

keyword arguments:
  -h, --help            Show this help message and exit
  -name                Name of new category and/or rule. This name is included in the 'must contain' in new RSS rules 
  -genre               Specifies the completed download subdirectory and which template to use for the auto downloading rule 
```


***

# Credits

This is my first project and I want to credit a few other programmers for their contributions on their own projects and for inspiring me to create a project of my own.

* l3uddz for all of his useful and professional projects.  I used his logging configuration and README template from Cloudplow.  https://github.com/l3uddz
* Tomodoro for his simple but elegant solution for managing seed queues and uses some of the same tools as I used.  https://github.com/Tomodoro/qbitseedmgr
* Countless stackoverflow users for their questions and answers. 

