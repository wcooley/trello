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

class TrelloClient:

    def __init__(self):
        self._config = {}
        self._boards = {}
        self._orgs = {}

    def read_config(self):
        if os.path.isfile(CONFIG):
            config_file = open(CONFIG, 'r')
            self._config = json.loads(config_file.read())
        else:
            raise NoConfigException('Configuration file does not exists.')

    def add_auth(self, hsh):
        """ Add 'key' and 'token' fields to request parameters
        """

        if not 'params' in hsh:
            hsh['params'] = {}

        params = hsh['params']
        params['key'] = API_KEY
        params['token'] = self._config['token']

    def get(self, url, **kwargs):
        """ Wrapper to simplify building the URL & getting the request
        """

        self.add_auth(kwargs)
        #print 'URL:', self.furl(url)

        #print "Getting URL '{0}'".format(url)
        r = requests.get(self.furl(url), **kwargs)
        #r.raise_for_status()
        return r

    def post(self, url, data, **kwargs):
        self.add_auth(kwargs)
        r = requests.post(self.furl(url), data, **kwargs)
        return r

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

        #print json
        return json

    def get_cards(self, board):
        r = self.get('boards/{0}/cards?filter=visible'.format(board))
        cards = []
        for card in self.get_json(r):
            name = card['name'].splitlines()[0]
            yield (card['id'], name)


    def get_boards(self, org):

        if not org:
            url = 'members/my/boards?filter=open'
        else:
            url = 'organization/{0}/boards?filter=open'.format(org)

        r = self.get(url)

        for board in self.get_json(r):
            org_info = self.get_org(board['idOrganization'])

            board_name = board['name']
            board_id = board['id']

            yield((org_info, board_name, board_id))

    def get_orgs(self):

        if len(self._orgs) == 0:
            r = self.get('members/my/organizations')

            for org in self.get_json(r):
                self._orgs[org['id']] = {
                    'name': org['name'],
                    'displayName': org['displayName']
                }

                yield (org['id'], org['name'], org['displayName'])
        else:
            for orgid in self._orgs:
                yield (orgid, self.orgs[orgid]['name'], self.orgs[orgid]['displayName'])


    def get_org(self, org_id=None):
        if not org_id:
            return
        try:
            return self._orgs[org_id]
        except KeyError:
            r = self.get('organizations/{0}'.format(org_id))
            org = self.get_json(r)
            self._orgs[org['id']] = {
                'name': org['name'],
                'displayName': org['displayName']
            }
            return self._orgs[org['id']]

    def copy_card(self, sourceid, dest_name, dest_listid):
        params = {
            'name': dest_name,
            'idCardSource': sourceid,
            'idList': dest_listid,
            'keepFromSource': ['checklists'],
        }

        r = self.post('cards', params)

        return self.get_json(r)

    def get_card(self, cardid):
        r = self.get('cards/{0}'.format(cardid))

        card = self.get_json(r)
        return card

    def get_list(self, listid):
        r = self.get('lists/{0}'.format(listid))

        return self.get_json(r)

    def get_lists(self, boardid):
        r = self.get('boards/{0}/lists/open'.format(boardid))

        return [ (l['id'], l['name']) for l in self.get_json(r) ]

    # Command line sub-commands
    def cmd_list_list(self, options):
        bid = options.boardid

        print Fore.GREEN + 'Lists for board ID {0}'.format(bid) + Fore.RESET

        for tlist in self.get_lists(bid):
            print ' {1:<25} [{0}]'.format(*tlist)

    def cmd_list_show(self, options):
        lid = options.listid

        cardlist = self.get_list(lid)
        pprint(cardlist)

    def cmd_card_copy(self, options):
        print "Copying card {0.source} to new '{0.dest_name}'".format(options)
        card = self.copy_card(options.source, options.dest_name, options.dest_listid)
        print 'ID: {id}\nURL: {url}'.format(**card)

    def cmd_card_show(self, options):

        card = self.get_card(options.cardid)
        pprint(card)
        print

        print 'Name: {name}\nId: {id}\nURL: {url}'.format(**card)

        if card['desc']:
            print 'Description: {desc}'.format(**card)

        if card['due']:
            print 'Due: {due}'.format(**card)

        #if card['

    def cmd_card_list(self, options):
        print Fore.GREEN + 'Cards' + Fore.RESET

        for x in self.get_cards(options.board):
            print '{0:<25} {1}'.format(*x)

    def cmd_board_list(self, options):
        org = options.org

        print Fore.GREEN + 'Boards' + Fore.RESET

        for board in self.get_boards(options.org):
            if board[0]:
                org_name = ' ({0})'.format(board[0]['displayName'])
            else:
                org_name = ''

            print '  {1}{0} [{2}]'.format(org_name, *board[1:])

    def cmd_org_list(self, options):

        print Fore.GREEN + 'Organizations' + Fore.RESET
        print '  {0:<15} {1}'.format('Board Name', 'Board Display Name')
        print '  {0:<15} {1}'.format('----------', '------------------')

        for org in self.get_orgs():
            print '  {0:<15s} {1}'.format(*org[1:])

    def cmd_setup(self, options):
        """Set up the client for configuration"""
        if os.path.isfile(CONFIG):
            os.remove(CONFIG)

        auth_url = self.furl('authorize?key={0}&name={1}&expiration=never&response_type='\
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
        config_file.write(json.dumps({'token': token}))
        config_file.close()

        print Fore.GREEN + 'Your config is ready to go!' + Fore.RESET

    def run(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(help='commands')
        board_parser = subparsers.add_parser('boards', help='Board operations')
        board_parser.add_argument('-o', '--org', action='store', help='''List
            boards for specific organizations''')
        board_parser.set_defaults(func=self.cmd_board_list)

        org_parser = subparsers.add_parser('orgs', help='List organizations')
        org_parser.set_defaults(func=self.cmd_org_list)

        card_parser = subparsers.add_parser('card', help='cards')
        card_subparser = card_parser.add_subparsers(help='card commands')

        card_list = card_subparser.add_parser('list', help='List cards')
        card_list.add_argument('-b', '--board', action='store', required=True,
            help='Limit to cards on board')
        card_list.set_defaults(func=self.cmd_card_list)

        card_show = card_subparser.add_parser('show', help='Show a card')
        card_show.add_argument('cardid', action='store', help='ID of card to show')
        card_show.set_defaults(func=self.cmd_card_show)

        card_copy = card_subparser.add_parser('copy', help='Copy card')
        card_copy.add_argument('--destlist', '-L', action='store', required=True,
                help='Destination list', dest='dest_listid')
        card_copy.add_argument('source', action='store',
                help='Card ID to copy from')
        card_copy.add_argument('dest_name', action='store',
                help='Name of copied card')
        card_copy.set_defaults(func=self.cmd_card_copy)

        list_parser = subparsers.add_parser('list', help='board lists')
        list_subparser = list_parser.add_subparsers(help='list commands')

        list_list = list_subparser.add_parser('list', help='List lists')
        list_list.add_argument('boardid', action='store', help='ID of board')
        list_list.set_defaults(func=self.cmd_list_list)

        list_show = list_subparser.add_parser('show', help='Show list')
        list_show.add_argument('listid', action='store', help='ID of list')
        list_show.set_defaults(func=self.cmd_list_show)

        config_parser = subparsers.add_parser('reconfig',
                help='Reconfigure the client')
        config_parser.set_defaults(func=self.cmd_setup)

        args = parser.parse_args()

        if not os.path.isfile(CONFIG):
            self.cmd_setup(args)
        else:
            self.read_config()
            args.func(args)


if __name__ == '__main__':
    colorama.init()
    client = TrelloClient()
    client.run()
