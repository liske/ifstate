from libifstate.util import logger
from libifstate.parser.base import Parser
import yaml
import os


class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._basedir = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._basedir, self.construct_scalar(node))
        with open(filename, 'r') as fh:
            return yaml.load(fh, Loader)


class YamlParser(Parser):
    def __init__(self, fn):
        logger.debug('YamlParser parsing %s', fn)
        with open(fn) as fh:
            self.ifstates = yaml.load(fh, Loader)
