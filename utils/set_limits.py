import qbittorrentapi
import logging
import toml

log = logging.getLogger('set_limits')
config = toml.load('utils/config.toml')

client = qbittorrentapi.Client(host=config['host'], username=config['username'], password=config['password'])


class LimitGroup:

    def __init__(self, group, names, hashes):
        self.group = group
        self.names = names
        self.hashes = hashes
        self.ratio_limit = config['shareLimits'][self.group]['ratio_limit']
        self.seeding_time_limit = config['shareLimits'][self.group]['seeding_time_limit']
        self.upload_speed_limit = config['shareLimits'][self.group]['upload_speed_limit']
        self.tags = config['shareLimits'][group]['tags']

    def set_attributes(self):
        client.torrents_set_share_limits(self.ratio_limit, self.seeding_time_limit, torrent_hashes=self.hashes)
        client.torrents_set_upload_limit(self.upload_speed_limit, torrent_hashes=self.hashes)
        client.torrents_add_tags(self.tags, torrent_hashes=self.hashes)
        log.info(f'Limit set to {self.group} for {self.names}')
        if self.group != 'private':
            return
        client.torrents_top_priority(torrent_hashes=self.hashes)
        log.info(f'Moved private torrent to top of queue: {self.names}')


def return_index_of_dict_in_list(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


class GroupAssignments:

    def __init__(self):
        self.groups = list(config['shareLimits'])

    def assign_categories(self):
        categories = [{'group': i, 'names': [], 'hashes': []} for i in self.groups]

        for torrent in client.torrents_info():
            if torrent.tags != '':
                continue
            if torrent.trackers[0]['msg'] == 'This torrent is private':
                index = return_index_of_dict_in_list(categories, 'group', 'private')
            elif torrent.category in self.groups:
                index = return_index_of_dict_in_list(categories, 'group', torrent.category)
            else:
                index = return_index_of_dict_in_list(categories, 'group', 'default')
            categories[index]['hashes'].append(torrent.hash)
            categories[index]['names'].append(torrent.name)

        #[categories.remove(i) for i in categories.copy() if not i['hashes']]

        return [LimitGroup(**i) for i in categories if i['hashes']] # The double splat converts dict to keyword arguments


def set_limits():
    handler = GroupAssignments()
    [i.set_attributes() for i in handler.assign_categories()]
