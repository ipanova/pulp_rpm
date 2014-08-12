# -*- coding: utf-8 -*-

import os
import unittest

from mock import patch, Mock

from pulp_rpm.common import constants
from pulp.server.exceptions import PulpCodedValidationException
from pulp_rpm.plugins.db import models
from pulp_rpm.plugins.importers.yum.parse import treeinfo


DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'data')
DISTRIBUTION_DATA_PATH = os.path.join(DATA_PATH, 'pulp_distribution')
DISTRIBUTION_GOOD_FILE = os.path.join(DISTRIBUTION_DATA_PATH, 'distribution_good.xml')
DISTRIBUTION_BAD_SYNTAX_FILE = os.path.join(DISTRIBUTION_DATA_PATH,
                                            'distribution_bad_xml_syntax.xml')
DISTRIBUTION_BAD_SCHEMA_VALIDATION_FILE = os.path.join(DISTRIBUTION_DATA_PATH,
                                                       'distribution_bad_schema_validation.xml')


class TestRealData(unittest.TestCase):
    def test_rhel5(self):
        path = os.path.join(DATA_PATH, 'treeinfo-rhel5')

        model, files = treeinfo.parse_treefile(path)

        self.assertTrue(isinstance(model, models.Distribution))
        self.assertEqual(model.id, 'ks-Red Hat Enterprise Linux Server-foo-5.9-x86_64')

        self.assertEqual(len(files), 19)
        for item in files:
            self.assertTrue(item['relativepath'])
        self.assertEquals('foo', model.variant)
        self.assertEquals('Server', model.metadata[treeinfo.KEY_PACKAGEDIR])

    def test_rhel5_optional(self):
        path = os.path.join(DATA_PATH, 'treeinfo-rhel5-no-optional-keys')

        model, files = treeinfo.parse_treefile(path)

        self.assertTrue(isinstance(model, models.Distribution))
        self.assertEqual(model.id, 'ks-Red Hat Enterprise Linux Server-5.9-x86_64')

        self.assertEqual(len(files), 19)
        for item in files:
            self.assertTrue(item['relativepath'])

        self.assertEquals(None, model.variant)
        self.assertEquals(None, model.metadata[treeinfo.KEY_PACKAGEDIR])


class TestProcessDistribution(unittest.TestCase):
    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.get_distribution_file',
           return_value=DISTRIBUTION_GOOD_FILE)
    def test_parse_good_file(self, mock_get_dist):
        feed = Mock()
        tmp_dir = Mock()
        nectar_config = Mock()
        model = Mock(metadata=dict())
        report = Mock()
        files = treeinfo.process_distribution(feed, tmp_dir, nectar_config, model, report)

        self.assertEquals(3, len(files))
        self.assertEquals('foo/bar.txt', files[0]['relativepath'])
        self.assertEquals('baz/qux.txt', files[1]['relativepath'])
        self.assertEquals(constants.DISTRIBUTION_XML, files[2]['relativepath'])
        self.assertEquals(model.metadata[constants.CONFIG_KEY_DISTRIBUTION_XML_FILE],
                          constants.DISTRIBUTION_XML)

    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.get_distribution_file',
           return_value=None)
    def test_no_distribution(self, mock_get_dist):
        feed = Mock()
        tmp_dir = Mock()
        nectar_config = Mock()
        model = Mock(metadata=dict())
        report = Mock()
        files = treeinfo.process_distribution(feed, tmp_dir, nectar_config, model, report)

        self.assertEquals(0, len(files))
        self.assertEquals(None, model.metadata.get(constants.CONFIG_KEY_DISTRIBUTION_XML_FILE))

    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.get_distribution_file',
           return_value=DISTRIBUTION_BAD_SYNTAX_FILE)
    def test_bad_distribution_syntax(self, mock_get_dist):
        feed = Mock()
        tmp_dir = Mock()
        nectar_config = Mock()
        model = Mock(metadata=dict())
        report = Mock()
        self.assertRaises(PulpCodedValidationException, treeinfo.process_distribution, feed,
                          tmp_dir, nectar_config, model, report)

    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.get_distribution_file',
           return_value=DISTRIBUTION_BAD_SCHEMA_VALIDATION_FILE)
    def test_bad_distribution_schema(self, mock_get_dist):
        feed = Mock()
        tmp_dir = Mock()
        nectar_config = Mock()
        model = Mock(metadata=dict())
        report = Mock()
        self.assertRaises(PulpCodedValidationException, treeinfo.process_distribution, feed,
                          tmp_dir,
                          nectar_config, model, report)


class TestGetDistributionFile(unittest.TestCase):
    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.nectar_factory.create_downloader')
    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.AggregatingEventListener')
    def test_get_distribution_file_exists(self, mock_listener, mock_create_downloader):
        mock_listener.return_value.succeeded_reports = ['foo']
        working_path = '/tmp/'
        feed = 'http://www.foo.bar/flux/'
        file_name = treeinfo.get_distribution_file(feed, working_path, Mock())
        request = mock_create_downloader.return_value.method_calls[0][1][0][0]
        self.assertEquals(request.url, os.path.join(feed, constants.DISTRIBUTION_XML))
        self.assertEquals(request.destination, os.path.join(working_path,
                                                            constants.DISTRIBUTION_XML))
        self.assertEquals(file_name, os.path.join(working_path, constants.DISTRIBUTION_XML))

    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.nectar_factory.create_downloader')
    @patch('pulp_rpm.plugins.importers.yum.parse.treeinfo.AggregatingEventListener')
    def test_get_distribution_file_does_not_exists(self, mock_listener, mock_create_downloader):
        mock_listener.return_value.succeeded_reports = []
        working_path = '/tmp/'
        feed = 'http://www.foo.bar/flux/'
        file_name = treeinfo.get_distribution_file(feed, working_path, Mock())
        self.assertEquals(None, file_name)
