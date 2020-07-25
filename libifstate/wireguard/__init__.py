from wgnlpy import WireGuard as WG

class WireGuard():
    def __init__(self, iface, wireguard):
        self.iface = iface
        self.wireguard = wireguard

