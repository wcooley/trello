#!/usr/bin/env python
import argparse
import json
import os

import requests
if requests.__version__ < '1':
    raise ImportError('requests v{0} too old'.format(requests.__version__) +
        '; at least 1.0.0 required')

try:
    import colorama
    from colorama import Fore
except ImportError:
    class colorama:
        @staticmethod
        def init(): pass
    class Fore:
        GREEN = ''
        RESET = ''

API_KEY = 'a65c7d23c318237578a5f27c76c74f8e'
API_URL = 'https://api.trello.com/1/'
APP_NAME = 'trello-cmd'
CONFIG = os.path.join(os.environ['HOME'], '.trello')

from pprint import pprint

class NoConfigException(Exception):
    pass

class TrelloClient(object):

    def __init__(self, config={}):
        self._config = config
        self._orgs = {}

    def add_auth(self, hsh):
        """ Add 'key' and 'token' fields to request parameters
        """

        if not 'params' in hsh:
            hsh['params'] = {}

        hsh['params']['key'] = API_KEY
        hsh['params']['token'] = self._config['token']

    def get(self, url, **kwargs):
        """ Wrapper to simplify building the URL & getting the request
        """

        self.add_auth(kwargs)
        #print 'URL:', self.furl(url)

        #print "Getting URL '{0}'".format(url)
        r = requests.get(self.furl(url), **kwargs)
        #r.raise_for_status()
        return self.get_json(r)

    def post(self, url, data, **kwargs):
        self.add_auth(kwargs)
        r = requests.post(self.furl(url), data, **kwargs)
        return self.get_json(r)

    def furl(self, url):
        """ Build a full URL by prepending API_URL
        """
        if not url.startswith('http'):
            url = API_URL + url

        return url

    def get_json(self, result):

        try:
            json = result.json()
        except ValueError, e:
            if e.message == 'No JSON object could be decoded':
                msg = e.message + "\nResponse: {0} {1}".format(result.status_code, result.text,)
                msg = msg + "For URL '{0}'".format(result.url)
                raise ValueError(msg)
            else:
                raise ValueError(e)

        return json

    def get_cards(self, board):
        """ Generator of TrelloCards from a given board ID """

        url  = 'boards/{0}/cards?filter=visible'.format(board)

        for card in self.get(url):
            yield TrelloCard(card)

    def search_for_one(self, modeltype, name):
        """ Search for a single type by name """
        url = 'search'
        params = {
                'query': name,
                'modelTypes': modeltype,
                modeltype[:-1] + '_fields': 'all',
                modeltype + '_limit': '1',
        }

        result = self.get(url, params=params)

        return result[modeltype][0]

    def get_board(self, board_id=None, board_name=None):
        if board_id:
            url = 'boards/{0}'.format(board_id)
            result = self.get(url)
        elif board_name:
            result = self.search_for_one('boards', board_name)
        else: pass
            # FIXME: Raise appropriate exception

        return TrelloBoard(result)

    def get_boards(self, org):

        if not org:
            url = 'members/my/boards?filter=open'
        else:
            url = 'organization/{0}/boards?filter=open'.format(org)

        for board in self.get(url):
            yield TrelloBoard(board)

    def get_orgs(self):

        url = 'members/my/organizations'

        for org in self.get(url):
            yield TrelloOrg(org)

    def get_org(self, org_id=None):
        url = 'organizations/{0}'.format(org_id)
        return TrelloOrg(self.get(url))

    def copy_card(self, sourceid, dest_name, dest_listid):
        params = {
            'name': dest_name,
            'idCardSource': sourceid,
            'idList': dest_listid,
            'keepFromSource': ['checklists'],
        }

        return TrelloCard(self.post('card', params))

    def get_card(self, cardid):
        url = 'cards/{0}'.format(cardid)

        return TrelloCard(self.get(url))

    def get_list(self, listid):
        url = 'lists/{0}'.format(listid)

        return TrelloList(self.get(url))

    def get_lists(self, boardid):
        url = 'boards/{0}/lists/open'.format(boardid)

        for lst in self.get(url):
            yield TrelloList(lst)

class DictWrapper(object):
    _data = None

    def __init__(self, data):
        self._data = data

    def __getattr__(self, attr):
        return self._data[attr]

    def __setattr__(self, attr, val):
        if self._data:
            self._data[attr] = val
        else:
            object.__setattr__(self, attr, val)

class TrelloOrg(DictWrapper): pass
class TrelloBoard(DictWrapper): pass
class TrelloList(DictWrapper): pass
class TrelloCard(DictWrapper):
    @property
    def short_name(self):
        """Card names can have multiple lines, but we often only want one
        line"""
        return self.name.splitlines()[0]

class TrelloClientCLI(object):

    def __init__(self):
        self._config = {}

    def read_config(self):
        if os.path.isfile(CONFIG):
            config_file = open(CONFIG, 'r')
            self._config = json.loads(config_file.read())
        else:
            raise NoConfigException('Configuration file does not exists.')

        return self._config

    # Command line sub-commands
    def cmd_list_list(self, client, options):
        bid = options.boardid

        print Fore.GREEN + 'Lists for board ID {0}'.format(bid) + Fore.RESET

        for tlist in client.get_lists(bid):
            print ' {0.name:<25} [{0.id}]'.format(tlist)

    def cmd_list_show(self, client, options):
        lid = options.listid

        cardlist = client.get_list(lid)
        pprint(cardlist)

    def cmd_card_copy(self, client, options):
        print "Copying card {0.source} to new '{0.dest_name}'".format(options)
        card = client.copy_card(options.source, options.dest_name, options.dest_listid)
        print 'ID: {0.id}\nURL: {0.url}'.format(card)

    def cmd_card_show(self, client, options):

        card = client.get_card(options.cardid)
        #pprint(card)

        print 'Name: {0.name}\nId: {0.id}\nURL: {0.url}'.format(card)

        if card.desc:
            print 'Description: {0.desc}'.format(card)

        if card.due:
            print 'Due: {0.due}'.format(card)

    def cmd_card_list(self, client, options):
        print Fore.GREEN + 'Cards' + Fore.RESET

        for card in client.get_cards(options.board):
            print '{0.id:<25} {0.short_name}'.format(card)

    def cmd_board_list(self, client, options):
        org = options.org

        print Fore.GREEN + 'Boards' + Fore.RESET

        for board in client.get_boards(org):
            org_name = ''
            if board.idOrganization:
                org = client.get_org(board.idOrganization)
                org_name = ' ({0})'.format(org.name)
            print '  {1.name}{0} [{1.id}]'.format(org_name, board)

    def cmd_board_show(self, client, options):
        board = client.get_board(board_name=options.board_name)
        print 'Name: {0.name}\nURL: {0.url}'.format(board)
        #pprint(board._data)
        #print

    def cmd_org_list(self, client, options):

        print Fore.GREEN + 'Organizations' + Fore.RESET
        print '  {0:<15} {1}'.format('Board Name', 'Board Display Name')
        print '  {0:<15} {1}'.format('----------', '------------------')

        for org in client.get_orgs():
            print '  {0.name:<15s} {0.displayName}'.format(org)

    def cmd_setup(self, client, options):
        """Set up the client for configuration"""
        if os.path.isfile(CONFIG):
            os.remove(CONFIG)

        auth_url = client.furl('authorize?key={0}&name={1}&expiration=never&response_type='\
                'token&scope=read,write'.format(API_KEY, APP_NAME))

        if os.sys.platform == 'darwin':
            os.system("open '{0}'".format(auth_url))
        elif os.sys.platform == 'linux2':
            r = os.system("xdg-open '{0}'".format(auth_url))
            if r > 0:
                print 'Open "{0}" in your web browser'.format(auth_url)
        else:
            print 'Open "{0}" in your web browser'.format(auth_url)

        token = raw_input('Paste the token: ')

        config_file = open(CONFIG, 'w')
        os.chmod(CONFIG, 0600)
        config_file.write(json.dumps({'token': token}))
        config_file.close()

        print Fore.GREEN + 'Your config is ready to go!' + Fore.RESET

    def run(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(help='commands')

        board_subparser = subparsers.add_parser('board', help='boards') \
                                    .add_subparsers(help='board commands')

        board_list = board_subparser.add_parser('list', help='List boards')
        board_list.add_argument('-o', '--org', help='''List
            boards for specific organizations''')
        board_list.set_defaults(func=self.cmd_board_list)

        board_show = board_subparser.add_parser('show', help='Show board')
        board_show.add_argument('board_name', help='Name of board')
        board_show.set_defaults(func=self.cmd_board_show)

        org_parser = subparsers.add_parser('orgs', help='List organizations')
        org_parser.set_defaults(func=self.cmd_org_list)

        card_subparser = subparsers.add_parser('card', help='cards') \
                                   .add_subparsers(help='card commands')

        card_list = card_subparser.add_parser('list', help='List cards')
        card_list.add_argument('-b', '--board', required=True,
            help='Limit to cards on board')
        card_list.set_defaults(func=self.cmd_card_list)

        card_show = card_subparser.add_parser('show', help='Show a card')
        card_show.add_argument('cardid', help='ID of card to show')
        card_show.set_defaults(func=self.cmd_card_show)

        card_copy = card_subparser.add_parser('copy', help='Copy card')
        card_copy.add_argument('--destlist', '-L', required=True,
                help='Destination list', dest='dest_listid')
        card_copy.add_argument('source', help='Card ID to copy from')
        card_copy.add_argument('dest_name', help='Name of copied card')
        card_copy.set_defaults(func=self.cmd_card_copy)

        list_subparser = subparsers.add_parser('list', help='board lists') \
                                   .add_subparsers(help='list commands')

        list_list = list_subparser.add_parser('list', help='List lists')
        list_list.add_argument('boardid', help='ID of board')
        list_list.set_defaults(func=self.cmd_list_list)

        list_show = list_subparser.add_parser('show', help='Show list')
        list_show.add_argument('listid', help='ID of list')
        list_show.set_defaults(func=self.cmd_list_show)

        subparsers.add_parser('reconfig', help='Reconfigure the client') \
                  .set_defaults(func=self.cmd_setup)

        args = parser.parse_args()
        try:
            config = self.read_config()
        except NoConfigException:
            config = {}

        client = TrelloClient(config)

        if not os.path.isfile(CONFIG):
            self.cmd_setup(client, args)
        else:
            args.func(client, args)


if __name__ == '__main__':
    colorama.init()
    client = TrelloClientCLI()
    client.run()
