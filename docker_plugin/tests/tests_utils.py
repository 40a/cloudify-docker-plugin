########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Built-in Imports
import testtools
import json

# Third Party Imports
import docker

# Cloudify Imports is imported and used in operations
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError
from docker_plugin import utils


class TestUtils(testtools.TestCase):

    def setUp(self):
        super(TestUtils, self).setUp()

    def get_mock_context(self, test_name):

        test_node_id = test_name
        test_properties = {
            'name': test_name,
            'image': {
                'repository': 'docker-test-image'
            }
        }

        ctx = MockCloudifyContext(
            node_id=test_node_id,
            properties=test_properties
        )

        return ctx

    def get_bad_image_id(self):
        return 'z0000000z000z0zzzzz0zzzz000000' \
               '0000zzzzz0zzz00000z0zz0000000000zz'

    def get_bad_container_id(self):
        return 'z0zz0z000z00'

    def get_docker_client(self):
        return docker.Client()

    def pull_image(self, client):
        output = []
        for line in client.pull('docker-test-image', stream=True):
            output.append(json.dumps(json.loads(line)))
        return output

    def create_container(self, client, name, image_id):
        return client.create_container(
            name=name, stdin_open=True, tty=True,
            image=image_id, command='/bin/sh')

    def get_docker_images(self, client):
        return [image for image in client.images()]

    def get_tags_for_docker_image(self, image):
        return [tag for tag in image.get('RepoTags')]

    def get_id_from_image(self, image):
        return image.get('Id')

    def test_get_image_id_no_image_id(self):
        name = 'test_get_image_id_no_image_id'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)
        image_id = self.get_bad_image_id()
        tag = 'latest'
        client = self.get_docker_client()
        ex = self.assertRaises(
            NonRecoverableError, utils.get_image_id,
            tag, image_id, client, ctx=ctx)
        self.assertIn(
            'Unable to verify', ex.message)

    def test_inspect_container_no_container(self):

        name = 'test_inspect_container_no_container'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)

        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)
        ctx.instance.runtime_properties['container_id'] = container

        client.remove_container(
            container=container)

        ex = self.assertRaises(
            NonRecoverableError, utils.inspect_container, client, ctx=ctx)
        self.assertIn('Unable to inspect container', ex.message)

    def test_wait_for_processes_bad_container(self):

        name = 'test_inspect_container_no_container'
        client = self.get_docker_client()
        ctx = self.get_mock_context(name)

        ctx.instance.runtime_properties['container_id'] = \
            self.get_bad_container_id()

        processes = ['/bin/sleep', 'mongod']

        ex = self.assertRaises(
            NonRecoverableError, utils.wait_for_processes,
            processes, 1, client, ctx=ctx)

        self.assertIn('Unable get container processes from top', ex.message)

    def test_wait_for_processes(self):

        name = 'test_wait_for_processes'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)

        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)

        ctx.instance.runtime_properties['container_id'] = container.get('Id')

        processes = ['/bin/sh']

        client.start(name)

        out = utils.wait_for_processes(processes, 1, client, ctx=ctx)
        client.stop(container=container, timeout=1)
        client.remove_container(
            container=container)
        self.assertEquals(True, out)

    def test_get_container_dictionary_none(self):

        name = 'test_get_container_dictionary_none'
        client = self.get_docker_client()
        ctx = self.get_mock_context(name)
        ctx.instance.runtime_properties['container_id'] = None
        out = utils.get_container_dictionary(client, ctx=ctx)
        self.assertIsNone(out)

    def test_get_container_dictionary(self):

        name = 'test_get_container_dictionary'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)

        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)

        ctx.instance.runtime_properties['container_id'] = container.get('Id')

        out = utils.get_container_dictionary(client, ctx=ctx)
        client.stop(container=container, timeout=1)
        client.remove_container(
            container=container)
        self.assertEquals(container['Id'], out['Id'])

    def test_get_remove_container_params(self):
        name = 'test_get_remove_container_params'
        ctx = self.get_mock_context(name)
        container_id = self.get_bad_container_id()
        ctx.instance.runtime_properties['container_id'] = \
            container_id
        params = {
            'container': container_id,
            'v': True,
            'link': False,
            'force': True
        }
        out = utils.get_remove_container_params(container_id, params, ctx=ctx)

        self.assertEquals(params, out)

    def test_get_container_stop_params(self):
        name = 'test_get_container_stop_params'
        ctx = self.get_mock_context(name)
        container_id = self.get_bad_container_id()
        ctx.instance.runtime_properties['container_id'] = \
            container_id
        params = {
            'container': container_id,
            'timeout': 1
        }
        out = utils.get_stop_params(container_id, params, ctx=ctx)

        self.assertEquals(params, out)

    def test_get_start_params(self):
        name = 'test_get_start_params'
        ctx = self.get_mock_context(name)
        container_id = self.get_bad_container_id()
        ctx.instance.runtime_properties['container_id'] = \
            container_id
        params = dict()
        out = utils.get_start_params(container_id, params, ctx=ctx)

        self.assertEquals(params, out)

    def test_get_create_container_params(self):
        name = 'test_get_create_container_params'
        ctx = self.get_mock_context(name)
        container_id = self.get_bad_container_id()
        ctx.instance.runtime_properties['container_id'] = \
            container_id
        params = dict()
        out = utils.get_create_container_params(params, ctx=ctx)
        self.assertEquals(params, out)

    def test_check_container_status(self):

        name = 'test_check_container_status'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)

        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)

        ctx.instance.runtime_properties['container_id'] = container.get('Id')
        client.start(name)
        out = utils.check_container_status(client, ctx=ctx)
        client.stop(container=container, timeout=1)
        client.remove_container(
            container=container)
        self.assertIn('Up', out)

    def test_get_container_id_from_name(self):
        name = 'test_get_container_id_from_name'
        ctx = self.get_mock_context(name)
        client = self.get_docker_client()
        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)
        container = self.create_container(client, name, image_id)
        ex = self.assertRaises(
            NonRecoverableError, utils.get_container_id_from_name,
            name, client, ctx=ctx)
        self.assertIn(
            'No such container', ex.message)
        client.remove_container(
            container=container)

    def test_get_top_info_bad_container(self):

        name = 'test_get_top_info_bad_container'
        client = self.get_docker_client()
        ctx = self.get_mock_context(name)
        ctx.instance.runtime_properties['container_id'] = \
            self.get_bad_container_id()

        ex = self.assertRaises(
            NonRecoverableError, utils.get_top_info,
            client, ctx=ctx)

        self.assertIn('Unable get container processes from top', ex.message)

    def test_get_params_bad_param(self):
        supported_params = ['good', 'evil']
        params = {
            'good': True,
            'evil': True,
            'ambiguety': False
        }
        ex = self.assertRaises(
            NonRecoverableError, utils.get_params,
            params, supported_params)
        self.assertIn('Unsupported', ex.message)

    def test_get_container_dictionary_bad_id(self):

        name = 'test_get_container_dictionary'
        client = self.get_docker_client()
        self.pull_image(client)
        ctx = self.get_mock_context(name)

        for image in self.get_docker_images(client):
            if 'docker-test-image:latest' in \
                    self.get_tags_for_docker_image(image):
                image_id = self.get_id_from_image(image)

        container = self.create_container(client, name, image_id)

        ctx.instance.runtime_properties['container_id'] = \
            self.get_bad_container_id()

        out = utils.get_container_dictionary(client, ctx=ctx)
        client.stop(container=container, timeout=1)
        client.remove_container(
            container=container)
        self.assertIsNone(out)
