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
        print 'Open {0} in your web browser'.format(auth_url)
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
