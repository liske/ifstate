from libifstate.util import logger
from libifstate.parser.base import Parser
from libifstate.exception import ParserOpenError, ParserIncludeError
import yaml
import os


class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        try:
            self._basedir = os.path.split(stream.name)[0]
        except AttributeError:
            pass

        if not self._basedir:
            self._basedir = os.path.curdir

        super(Loader, self).__init__(stream)
        self.add_constructor('!include', self.include)

    def include(self, id, node):
        filename = self.construct_scalar(node)
        if not os.path.isabs(filename):
            filename = os.path.join(self._basedir, filename)

        try:
            with open(filename, 'r') as fh:
                return yaml.load(fh, Loader)
        except OSError as ex:
            raise ParserIncludeError(ex)


class YamlParser(Parser):
    def __init__(self, fn):
        logger.debug('YamlParser parsing %s', fn)
        try:
            with open(fn) as fh:
                self.ifstates = yaml.load(fh, Loader)
        except OSError as ex:
            raise ParserOpenError(ex)
