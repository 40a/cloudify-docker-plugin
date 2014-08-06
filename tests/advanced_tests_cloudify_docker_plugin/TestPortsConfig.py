import socket

from docker_plugin import tasks
from tests.TestCaseBase import TestCaseBase


_INTERFACE = '127.0.0.1'
_HOST = _INTERFACE
_PORT1 = 1234
_PORT2 = 1235
_CMD = '/bin/nc -nvl {}'.format(str(_PORT1))


class TestPortsConfig(TestCaseBase):

    def test_ports_config(self):
        tasks.create(self.ctx)
        tasks.run(self.ctx)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((_HOST, _PORT2))
            s.close()
        except socket.error as e:
            raise AssertionError(e)

    def setUp(self):
        super(TestPortsConfig, self).setUp()
        self.ctx.properties['container_create'].update({'command': _CMD})
        self.ctx.properties['container_create'].update({'ports': [_PORT1]})
        self.ctx.properties['container_start'].update(
            {'port_bindings': {_PORT1: (_INTERFACE, _PORT2)}}
        )