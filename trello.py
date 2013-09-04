#!/usr/bin/env python

from urllib import urlencode
import argparse
import json
import os

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

from trello.client import TrelloClient

API_KEY = 'a65c7d23c318237578a5f27c76c74f8e'
API_URL = 'https://api.trello.com/1/'
APP_NAME = 'trello-cmd'
CONFIG = os.path.join(os.environ['HOME'], '.trello')

from pprint import pprint

class NoConfigException(Exception):
    pass

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
        card = client.copy_card(options.source,
                options.dest_name, options.dest_listid)
        print 'ID: {0.id}\nURL: {0.url}'.format(card)

    def cmd_card_show(self, client, options):

        card = client.get_card(name=options.card)
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

        auth_url = client.furl('authorize?' + urlencode({
                                'key': API_KEY,
                                'name': APP_NAME,
                                'expiration': 'never',
                                'response_type': 'token',
                                'scope': 'read,write'
            }))

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
        card_show.add_argument('card', help='Name of card to show')
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

        config['API_KEY'] = API_KEY
        config['API_URL'] = API_URL
        config['APP_NAME'] = APP_NAME

        client = TrelloClient(config)

        if not os.path.isfile(CONFIG):
            self.cmd_setup(client, args)
        else:
            args.func(client, args)


if __name__ == '__main__':
    colorama.init()
    client = TrelloClientCLI()
    client.run()
