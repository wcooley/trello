import requests

from trello.models import *

if requests.__version__ < '1':
    raise ImportError('requests v{0} too old'.format(requests.__version__) +
        '; at least 1.0.0 required')

class TrelloClient(object):

    def __init__(self, config={}):
        self._config = config
        self._orgs = {}

    def add_auth(self, hsh):
        """ Add 'key' and 'token' fields to request parameters
        """

        if not 'params' in hsh:
            hsh['params'] = {}

        hsh['params']['key'] = self._config['API_KEY']
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
            url = self._config['API_URL'] + url

        return url

    def get_json(self, result):

        try:
            json = result.json()
        except ValueError, e:
            if e.message == 'No JSON object could be decoded':
                msg = e.message + "\nResponse: {0} {1}".format(
                        result.status_code, result.text)
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

    def get_card(self, id=None, name=None):

        if id:
            result = self.get('cards/{0}'.format(id))
        elif name:
            result = self.search_for_one('cards', name)
        else: pass
            # FIXME: Raise appropriate exception

        return TrelloCard(result)

    def get_list(self, listid):
        url = 'lists/{0}'.format(listid)

        return TrelloList(self.get(url))

    def get_lists(self, boardid):
        url = 'boards/{0}/lists/open'.format(boardid)

        for lst in self.get(url):
            yield TrelloList(lst)


