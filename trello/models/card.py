from trello.dictwrapper import DictWrapper

class TrelloCard(DictWrapper):
    @property
    def short_name(self):
        """Card names can have multiple lines, but we often only want one
        line"""
        return self.name.splitlines()[0]
