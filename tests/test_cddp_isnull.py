from django.test import TestCase
#import unittest
from django.core.cache import cache

import requests

from sqs.utils.das_schema_utils import DisturbanceLayerQuery, DisturbancePrefillData
from tests.no_createdb_test_runner import NoCreateDbTestRunner
from sqs.utils.loader_utils import DbLayerProvider

from sqs.utils.das_tests.isnull import select_isnull as select
#from sqs.utils.das_tests.select import multiselect_isnull as ms
#from sqs.utils.das_tests.select import radiobuttons_isnull as rb
#from sqs.utils.das_tests.select import checkbox_isnull as cb
#from sqs.utils.das_tests.select import other_isnull as other

import logging
logger = logging.getLogger(__name__)
logging.disable(logging.CRITICAL)


#class SetupCddpIsNullTests(unittest.TestCase):
class SetupCddpIsNullTests(TestCase):
    '''
    From: https://www.programcreek.com/python/?code=nesdis%2Fdjongo%2Fdjongo-master%2Ftests%2Fdjango_tests%2Ftests%2Fv21%2Ftests%2Ftest_runner%2Ftests.py#
          https://stackoverflow.com/questions/5917587/django-unit-tests-without-a-db

    To run:
        All tests in all files beginnig with 'tests_' in directory <base-dir>/tests
        ./manage.py test

        All tests in class SetupDatabasesTests
        ./manage.py test tests.test_cddp_isnull.SetupCddpIsNullTests
 
        Specific test
        ./manage.py test tests.test_cddp_isnull.SetupCddpIsNullTests.test_select_isnull

        Specific test, without caching
        ./manage.py test tests.test_cddp_isnull.SetupCddpIsNullTests.test_select_isnull --disable-cache
    '''

#     def setUp(self):
#        # runs (repeats) for every test below
#        # self.runner_instance = NoCreateDbTestRunner(verbosity=0)
#        pass

#    @classmethod
#    def setUpTestData(cls):
#        pass

    @classmethod
    def setUpClass(self):
        # runs once for every test below
        #import ipdb; ipdb.set_trace()
        cache.clear()

        # create layer in test DB
        name='cddp:local_gov_authority'
        url='https://kmi.dbca.wa.gov.au/geoserver/dummy'
        filename='sqs/utils/das_tests/layers/cddp_local_gov_authority.json'
        layer_info, layer_gdf = DbLayerProvider(layer_name=name, url=url).get_layer_from_file(filename)

        # create layer in test DB
        name='cddp:dpaw_regions'
        url='https://kmi.dbca.wa.gov.au/geoserver/dummy'
        filename='sqs/utils/das_tests/layers/cddp_dpaw_regions.json'
        layer_info, layer_gdf = DbLayerProvider(layer_name=name, url=url).get_layer_from_file(filename)

    @classmethod
    def tearDownClass(self):
        cache.clear()

    # TODO Need to confirm how a response from SQS is to  be handled for 'IsNull'
    def test_select_isnull(self):
        logger.info("Method: test_select_isnull.")
        #import ipdb; ipdb.set_trace()
        self.dlq = DisturbanceLayerQuery(select.MASTERLIST_QUESTIONS_GBQ, select.GEOJSON, select.PROPOSAL)
        res = self.dlq.query()
        self.assertTrue(res['data'] == select.TEST_RESPONSE['data'])

