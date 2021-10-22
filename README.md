# qbitmgr
Automatically manage qbittorrent share limits, RSS rules, and file moves

Supports qBittorrent v4.1.0+ (i.e. Web API v2.0+). Currently supports up to qBittorrent [v4.3.8](https://github.com/qbittorrent/qBittorrent/releases/tag/release-4.3.8) (Web API v2.8.2) released on Aug 28, 2021.

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-blue.svg?style=flat-square)](https://www.python.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%203-blue.svg?style=flat-square)](https://github.com/snazzypapa/qbitmgr/blob/master/LICENSE.md)

---



# Introduction

Qbitmgr has 3 main functions:

1. Automaticly set share limits for torrents in qbittorrent based on trackers and categories.

2. Automatically manage files once completed: delete unwanted files by type and move files based on genre.

3. Add templated RSS auto download rules and download categories from the command line.


# Requirements

1. Ubuntu/Debian OS (could work in other OSes with some tweaks).

2. Qbittorrent with WebUI accessible on localhost

3. Automatic download handling turned on in qbittorrent with an incomplete directory and a completed directory. It does not matter what these are named as long as you know their paths. 

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

1. Create a shortcut for Qbitmgr.

   ```
   sudo ln -s /opt/qbitmgr/qbitmgr.py /usr/local/bin/qbitmgr
   ```

1. Edit the config file example saved in /utils.

   ```
   nano utils/config.toml
   ```

1. To have Qbitmgr run automatically do the following:

   ```
   sudo cp /opt/qbitmgr/systemd/qbitmgr_watcher.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable qbitmgr_watcher.service
   sudo systemctl start qbitmgr_watcher.service
   ```   

# Usage

## Automatic

A filesystem watcher service looks for changes to the incomplete downloads directory and 

## Manual (CLI)

Command:
```
qbitmgr
```

```
usage: qbitmgr {add-cat,add-rule,move,set-limits} [--name] [--genre]
                 
positional arguments:
  {add-cat,add-rule,move,set-limits,watch}
                        "add-cat": adds new category to qbittorrent and sets completed download directory to specified genre, requires '--genre ' 
                        "add-rule": adds new categgory and new RSS auto download rule to qbittorrent and sets completed download directory to specified genre, requires '--genre '
                        "move":  deletes unwanted files and moves completed downloads from the qbittorrent downloads directory to whatever directory you prefer  
                        "set-limits": sets share limits in qbittorrent via the qbittorrent API
                        "watch": starts filesystem watcher for new and completed torrents

keyword arguments:
  -h, --help            Show this help message and exit
  --name                Name of new category and/or rule. This name is included in the 'must contain' in new RSS rules 
  --genre               Specifies the completed download subdirectory and which template to use for the auto downloading rule 
```


***

# Credits

This is my first project and I want to credit a few other programmers for their contributions on their own projects and for inspiring me to create a project of my own.

* l3uddz for all of his useful and professional projects.  I used his logging configuration from Cloudplow and his README template from TQM -- another qbittorrent manager. https://github.com/l3uddz
* Tomodoro for his simple but elegant solution for managing seed queues and uses some of the same tools as I used.  https://github.com/Tomodoro/qbitseedmgr
* Countless stackoverflow users for their questions and answers. 


  
