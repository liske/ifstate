import logging
from pyroute2 import IPRoute

logger = logging.getLogger('ifstate')
ipr = IPRoute()
