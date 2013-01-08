#!/usr/bin/env python

import argparse
from colorama import init, Fore
import json
import os
import requests

API_KEY = 'a65c7d23c318237578a5f27c76c74f8e'
API_URL = 'https://api.trello.com/1/'
APP_NAME = 'trello-cmd'
CONFIG = os.path.join(os.environ['HOME'], '.trello')

class NoConfigException(Exception):
    pass

class TrelloClient:

    def __init__(self):
        self._config = {}

    def read_config(self):
        if os.path.isfile(CONFIG):
            config_file = open(CONFIG, 'r')
            self._config = json.loads(config_file.read())
        else:
            raise NoConfigException('Configuration file does not exists.')

    def setup(self):
        """Set up the client for configuration"""
        if os.path.isfile(CONFIG):
            os.remove(CONFIG)

        auth_url = '%sauthorize?key=%s&name=%s&expiration=never&response_type='\
                'token&scope=read,write' % (API_URL, API_KEY, APP_NAME)
        print 'Open %s in your web browser' % auth_url
        token = raw_input('Paste the token: ')

        config_file = open(CONFIG, 'w')
        config_file.write(json.dumps({'token': token}))
        config_file.close()

        print Fore.GREEN + 'Your config is ready to go!' + Fore.RESET

    def run(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(help='commands')
        board_parser = subparsers.add_parser('board', help='Board operations')
        board_parser.add_argument('-o', '--org', action='store', help='''List
            boards for specific organizations''')
        board_parser.set_defaults(which='board')

        config_parser = subparsers.add_parser('reconfig',
                help='Reconfigure the client')
        config_parser.set_defaults(which='reconfig')


        """parser.add_argument('boards', help='List all boards',
                action='store_false')
        parser.add_argument('reconfig', help='Reconfigure the client',
                action='store_false')
        parser.add_argument('--all', help='Show all cards',
                action='store_false')"""
        options = parser.parse_args()

        if not os.path.isfile(CONFIG) or options.which is 'reconfig':
            self.setup()

        self.read_config()


if __name__ == '__main__':
    init() # Initialize colorama
    client = TrelloClient()
    client.run()
