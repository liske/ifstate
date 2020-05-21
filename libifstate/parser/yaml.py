from libifstate.util import logger
from libifstate.parser.base import Parser
import yaml

class YamlParser(Parser):
    def __init__(self, fn):
        logger.debug('YamlParser parsing %s', fn)
        with open(fn) as fh:
            self.ifstates = yaml.full_load(fh)
