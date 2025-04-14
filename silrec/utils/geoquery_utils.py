from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from rest_framework import status

import gc
import pandas as pd
import geopandas as gpd
import requests
import json
import os
import io
import pytz
import traceback
from datetime import datetime
import time
import itertools

from sqs.components.gisquery.models import Layer #, Feature#, LayerHistory
from sqs.utils.loader_utils import DbLayerProvider, print_system_memory_stats
from sqs.utils.helper import (
    DefaultOperator,
    #HelperUtils,
    #pop_list,
)
from sqs.utils import (
    TEXT_WIDGETS,
    RADIOBUTTONS,
    CHECKBOX,
    MULTI_SELECT,
    SELECT,
)

from sqs.utils import HelperUtils
from sqs.exceptions import LayerProviderException

import logging
logger = logging.getLogger(__name__)

DATE_FMT = '%Y-%m-%d'
DATETIME_FMT = '%Y-%m-%d %H:%M:%S'

RESPONSE_LEN = 75


class DisturbanceLayerQueryHelper():

    def __init__(self, masterlist_questions, geojson, proposal):
        self.masterlist_questions = masterlist_questions
        self.geojson = self.read_geojson(geojson)
        self.proposal = proposal
        self.unprocessed_questions = []
        self.metrics = []

    def read_geojson(self, geojson):
        """ geojson is the user specified shapefile/polygon, used to intersect the layers """
        try:
            shapefile_gdf = gpd.read_file(json.dumps(geojson))
        except Exception as e:
            raise Exception(f'Error reading geojson file: {str(e)}')

        return shapefile_gdf

    def get_shapefile_gdf(self, layer, layer_crs):
        '''
        1. Converts Polar Projection from EPSG:xxxx (eg. EPSG:4326) in deg to Cartesian Projection (in meters),
        add buffer (in meters) to the new projection, then reverts the buffered polygon to 
        the original projection

        2. Converts user provided shapefile_gdf to a common CRS (same as layer's CRS) --> to allow overlay

        Input: buffer_size -- in meters

        Returns the the original shapefile, perimeter increased/decreased by the buffer size and converted to a common CRS
        '''

        #shapefile_gdf = self.geojson[['geometry']] if 'geometry' in self.geojson else self.geojson
        shapefile_gdf = self.geojson
        if layer_crs.lower() != shapefile_gdf.crs.srs.lower():
            # need a common CRS before overlaying shapefile with layer
            shapefile_gdf.to_crs(layer_crs, inplace=True)

        if 'POLYGON' not in str(shapefile_gdf):
            logger.warn(f'Proposal ID {self.proposal.get("id")}: Uploaded Shapefile/Polygon is NOT a POLYGON\n {shapefile_gdf}.')

        try:
            # if buffer specified in layer definition, increase the perimeter by the buffer amount. Otherwise, 
            # reduce the perimeter by settings.DEFAULT_BUFFER
            buffer_size = layer['buffer'] if layer['buffer'] else settings.DEFAULT_BUFFER
            if buffer_size and buffer_size != 0:
                crs_orig =  shapefile_gdf.crs

                # convert to new projection so that buffer can be added in meters
                shapefile_cart_gdf = shapefile_gdf.to_crs(settings.CRS_CARTESIAN)
                shapefile_cart_gdf['geometry'] = shapefile_cart_gdf['geometry'].buffer(buffer_size)

                # revert to original projection
                shapefile_buffer_gdf = shapefile_cart_gdf.to_crs(crs_orig)

                return shapefile_buffer_gdf
            
        except Exception as e:
            logger.error(f'Error adding buffer {buffer_size} to polygon.\n{e}')
            
        return shapefile_gdf

    def get_attributes(self, layer_gdf):
        cols = layer_gdf.columns.drop(['id','md5_rowhash', 'geometry'])
        attrs = layer_gdf[cols].to_dict(orient='records')
        #return layer_gdf[cols].to_dict(orient='records')

        # drop duplicates
        attrs = pd.DataFrame(attrs).drop_duplicates().to_dict('r')
        return attrs

    def get_grouped_questions(self, question):
        """
        Return the entire question group. 
        For example, given a radiobutton or checkbox question, return the all question/answer combinations for that question
        """
        try:
            for question_group in self.masterlist_questions:
                if question_group['question_group'] == question:
                    return question_group

        except Exception as e:
            logger.error(f'Error searching for question_group: \'{question}\'\n{e}')

        return []

    def set_metrics(self, cddp_question, layer_provider, expired, condition, time_retrieve_layer, time_taken, error):
        self.metrics.append(
            dict(
                question=cddp_question['masterlist_question']['question'],
                answer_mlq=cddp_question['answer_mlq'],
                expired=expired,
                layer_name=layer_provider.layer_name,
                #layer_cached=layer_provider.layer_cached,
                condition=condition,
                time_retrieve_layer=round(time_retrieve_layer, 3),
                time=round(time_taken, 3),
                error=f'{error}',
                result=None,
                assessor_answer=None,
                operator_response=None,
            )
        )
        return self.metrics

    def get_overlay_gdf(self, layer_gdf, shapefile_gdf, how, column_name):
        ''' how = ['intersection','symmetric_difference','difference']
        '''

        # how='Overlapping' - get layer features 'intersected by' shapefile_gdf
        overlay_gdf = layer_gdf.overlay(shapefile_gdf[['geometry']], how='intersection', keep_geom_type=False)
        if how=='Outside':
            # all layer features completely outside shapefile_gdf
            overlay_gdf = layer_gdf[~layer_gdf[column_name].isin( overlay_gdf[column_name].unique() )]

        elif how=='Inside':
            # all layer features completely within/inside shapefile_gdf
            diff_gdf = layer_gdf.overlay(shapefile_gdf[['geometry']], how='difference', keep_geom_type=False)
            overlay_gdf = layer_gdf[~layer_gdf[column_name].isin( diff_gdf[column_name].unique() )]

        if column_name not in overlay_gdf.columns:
            _list = HelperUtils.pop_list(overlay_gdf.columns.to_list())
            error_msg = f'Property Name "{column_name}" not found in layer "{layer_name}".\nAvailable properties are "{_list}".'
            logger.error(error_msg)

        return overlay_gdf

    def spatial_join_gbq(self, question, widget_type):
        '''
        Process new Question (grouping by like-questions) and results stored in cache 

        NOTE: All questions for the given layer 'layer_name' will be processed by 'spatial_join()' and results stored in cache. 
              This will save time reloading and querying layers for questions from the same layer_name. 
              It is CPU cost effective to query all questions for the same layer now, and cache results for 
              subsequent potential question/answer queries.
        '''

        def unique_list(_list):
            return list(set(_list))

        def to_str(_list):
            return '\n'.join(_list).replace(',',', ').replace('\\n', '\n')

        try:
            error_msg = ''
            today = datetime.now(pytz.timezone(settings.TIME_ZONE))
            layer_info = {}
            expired = False
            layer_res = []
            question_group_res = []

            grouped_questions = self.get_grouped_questions(question)
            if len(grouped_questions)==0:
                return question_group_res

#            if grouped_questions['questions'][0]['masterlist_question']['question'] == '2.0 What is the land tenure or classification?':
#                import ipdb; ipdb.set_trace()

            for cddp_question in grouped_questions['questions']:
                start_time = time.time()

                layer_res = []
                for layer in cddp_question['layers']:
                 
                    layer_name = layer['layer']['layer_name']
                    layer_url = layer['layer']['layer_url']

                    layer_question_expiry = datetime.strptime(layer['expiry'], DATE_FMT).date() if layer['expiry'] else None
                    if layer_question_expiry is None or layer_question_expiry >= today.date():

                        start_time_retrieve_layer = time.time()

                        answer_str = f'A: \'{cddp_question.get("answer_mlq")[:25]}\'' if cddp_question.get('answer_mlq') else ''
                        logger.info('---------------------------------------------------------------------------------------------')
                        logger.info(f'{layer_name} - Proposal ID {self.proposal["id"]}: Processing Question \'{cddp_question.get("masterlist_question")["question"][:25]}\' {answer_str} ...')
          
                        time_retrieve_layer = time.time() - start_time_retrieve_layer
                        how = layer['how']
                        column_name = layer['column_name']
                        operator = layer['operator']
                        value = layer['value']

                        print_system_memory_stats(f'Ready to load layer {layer_name}')
                        layer_provider = DbLayerProvider(layer_name, url=layer_url)
                        layer_info, layer_gdf = layer_provider.get_layer()

                        mem_usage = round(float(layer_gdf.memory_usage(index=True).sum()/1024**2), 2)
                        print_system_memory_stats(f'{layer_name}, gdf mem_usage {mem_usage} MB')

                        shapefile_gdf = self.get_shapefile_gdf(layer, layer_info['layer_crs'])
                        overlay_gdf = self.get_overlay_gdf(layer_gdf, shapefile_gdf, how, column_name)

                        op = DefaultOperator(layer, overlay_gdf, widget_type)
                        operator_result  = op.answer_prefix('proponent_items') + unique_list(op.operator_result())
                        proponent_answer = to_str(op.answer_prefix('proponent_items') + unique_list(op.proponent_answer()))
                        assessor_answer  = to_str(op.answer_prefix('assessor_items') + unique_list(op.assessor_answer()))

                        logger.info(f'Operator Result: {operator_result}'[:200])
                        condition = f'{column_name} -- {operator}'
                        if operator != 'IsNotNull':
                            condition += f' -- {value}'

                        res = dict(
                                visible_to_proponent=layer['visible_to_proponent'],
                                layer_details = dict(**layer_info,
                                    column_name=column_name,
                                    sqs_timestamp=today.strftime(DATETIME_FMT),
                                    error_msg = error_msg,
                                ),
                                condition=[how, condition],
                                operator_response=operator_result,
                                proponent_answer=proponent_answer,
                                assessor_answer=assessor_answer,
                            )
                        layer_res.append(res)

                        self.set_metrics(cddp_question, layer_provider, expired, condition, time_retrieve_layer, time.time() - start_time, error=None)
                        logger.info(f'Time Taken: {round(time.time() - start_time, 3)} secs')

                        HelperUtils.force_gc([layer_gdf, overlay_gdf, shapefile_gdf])
                    else:
                        logger.warn(f'Expired {layer_question_expiry}: Ignoring question {cddp_question["masterlist_question"]["question"]} - {layer_name}')
                        expired = True

                question_group_res.append(
                    dict(
                        question=cddp_question['masterlist_question']['question'],
                        answer=cddp_question['answer_mlq'],
                        other_data=cddp_question['other_data'],
                        layers=layer_res,
                    )
                )

        except Exception as e: 
            logger.error(e)
            #self.set_metrics(cddp_question, layer_provider, expired, condition, time_retrieve_layer, time.time() - start_time, error=e)

#        if grouped_questions['questions'][0]['masterlist_question']['question'] == '2.0 What is the land tenure or classification?':
#            import ipdb; ipdb.set_trace()

        return question_group_res

    def query_question(self, item, answer_type):

        def set_metric_result(response):
            ''' Adds result from the intersection (and label) to metrics'''
            try:
                if 'layer_details' in response:
                    for layer_detail in response['layer_details']:
                        question = layer_detail['question']['question']
                        answer_mlq = layer_detail['question']['answer']
                        layers = layer_detail['question']['layers']
                        for idx, metric in enumerate(self.metrics):
                            if metric['question']==question and metric['answer_mlq']==answer_mlq:
                                if response['result']:
                                    metric.update({'result': response['result']})
                                else:
                                    proponent_answer = layer_detail['question']['proponent_answer']
                                    metric.update({'result': proponent_answer})

                                #assessor_answer = layer_detail['question']['assessor_answer']
                                assessor_answer = str([i['assessor_answer'] for i in layers])
                                #operator_response = ', '.join(map(str, layer_detail['question']['operator_response']))
                                operator_response = str([i['operator_response'] for i in layers])
                                operator_response = operator_response[:RESPONSE_LEN] + ' ...' if len(operator_response)>RESPONSE_LEN else operator_response
                                metric.update({'assessor_answer': assessor_answer})
                                metric.update({'operator_response': operator_response})
            except Exception as e:
                logger.warn(f'Could not add result to Metrics\n{e}')


        #start_time = time.time()
        response = {}
        if answer_type == RADIOBUTTONS:
            response = self.find_radiobutton(item)

        elif answer_type == CHECKBOX:
            response = self.find_checkbox(item)

        elif answer_type == MULTI_SELECT:
            response = self.find_multiselect(item)

        elif answer_type == SELECT:
            response = self.find_select(item)

        elif answer_type == TEXT_WIDGETS:
            response = self.find_other(item)

        set_metric_result(response)
        #self.total_query_time += time.time() - start_time
        return response

    def find_radiobutton(self, item):
        ''' Widget --> radiobutton
            1. question['operator_response']  --> contains results from SQS intersection and equality comparison
            2. Iterate through item_options (from proposal.schema) and compare with question['answer']

            If item_options==question['answer'] && len(question['operator_response'])>0, then return rb as checked

            result --> result (str, returns first label from list of labels that match operator_response)
        '''
        response = {}
        question = {}
        try:
            schema_question  = item['label']
            schema_section = item['name']
            item_options   = item['options']

            #processed_questions = self.get_processed_question(schema_question, widget_type=item['type'])
            processed_questions = self.spatial_join_gbq(schema_question, widget_type=item['type'])
            if len(processed_questions)==0:
                return {}

            layer_details=[]
            for item in item_options:
                label = item['label']
                value = item['value']
                # return first checked radiobutton in order rb's appear in 'item_option_labels' (schema question)
                for question in processed_questions:
                    for layer in question['layers']:
                        #details = question['layer_details']
                        details = layer['layer_details']
                        #if label not in result and label.casefold() == question['answer'].casefold() and len(layer['operator_response'])>0:
                        if label.casefold() == question['answer'].casefold() and len(layer['operator_response'])>0:

                            raw_data = layer
                            details = raw_data.pop('layer_details', None)

                            response =  dict(
                                result=label,
                                assessor_info=[],
                                layer_details=[dict(name=schema_section, label=value, details=details, question=question)],
                            )

                            return response
                        else:
                            #logger.warn(f'Iterating Layers - \'{question["question"][:25]} ...\': operator_response {layer["operator_response"]} not found from layer details["layer_name"]')
                            pass

        except Exception as e:
            logger.error(f'RADIOBUTTON: Searching Question in SQS processed_questions dict: \'{question}\'\n{e}')

        return response

    def find_checkbox(self, item):
        ''' Widget --> checkbox
            1. question['operator_response']  --> contains results from SQS intersection and equality comparison
            2. Iterate through item_options (from proposal.schema) and compare with question['answer']

            If item_options==question['answer'] && len(question['operator_response'])>0, then return cb as checked

            result --> result (list, list of labels that match operator_response)
        '''
        response = {}
        question = {}
        try:
            schema_question = item['label']
            item_options    = item['children']

            item_options_dict = [dict(name=i['name'], label=i['label']) for i in item_options]
            #processed_questions = self.get_processed_question(schema_question, widget_type=item['type'])
            processed_questions = self.spatial_join_gbq(schema_question, widget_type=item['type'])
            if len(processed_questions)==0:
                return {}

            result=[]
            layer_details=[]
            for _d in item_options_dict:
                name = _d['name']
                label = _d['label']
                for question in processed_questions:
                    for layer in question['layers']:
                        if label not in result and label.casefold() == question['answer'].casefold() and len(layer['operator_response'])>0:
                            result.append(label) # result is in an array list 
                            #raw_data = question
                            raw_data = layer
                            details = raw_data.pop('layer_details', None)
                            # [lbl] - next line 'list' hack for disturbance/components/proposals/api.py 'refresh()' method, when only a single checkbox is selected
                            layer_details.append(dict(name=name, label=[label], details=details, question=raw_data))
                        else:
                            #logger.warn(f'Iterating Layers - \'{question["question"][:25]} ...\': operator_response {layer["operator_response"]} not found from layer layer["layer_details"]')
                            pass

            response =  dict(
                result=result,
                assessor_info=[],
                layer_details=layer_details,
            )

        except Exception as e:
            logger.error(f'CHECKBOX: Searching Question in SQS processed_questions dict: \'{question}\'\n{e}')

        return response

    def find_select(self, item):
        ''' Widget --> select
            1. question['operator_response']  --> contains results from SQS intersection and equality comparison
            
            result --> result (str, first item in sorted list of labels that match operator_response)
        '''
        response = {}
        question = {}
        try:
            schema_question  = item['label']
            schema_section = item['name']
            item_options   = item['options']

            #processed_questions = self.get_processed_question(schema_question, widget_type=item['type'])
            processed_questions = self.spatial_join_gbq(schema_question, widget_type=item['type'])
#            if len(processed_questions) != 1:
#                # for multi-select questions, there must be only one question
#                logger.error(f'SELECT: For select question, there must be only one question, {len(processed_questions)} found: \'{question}\'')
#                return {}
#            question = processed_questions[0]
            item_labels = [i['label'] for i in item_options] # these are the available answer options proponent can choose from
            for question in processed_questions:
                for layer in question['layers']:

                    #operator_response = question['operator_response'] # these are the answers from the query intersection/difference (truncated to no. of polygons/answers to return)
                    operator_response = layer['operator_response'] # these are the answers from the query intersection/difference (truncated to no. of polygons/answers to return)

                    # return only those labels that are in the available choices to the proponent
                    # case-insensitive intersection. returns labels found in both lists
                    labels_found = list({str.casefold(x) for x in item_labels} & {str.casefold(x) for x in operator_response})
                    #labels_found = [str.casefold(x) for x in operator_response]
                    labels_found.sort()

                    #raw_data = question
                    raw_data = layer
                    details = raw_data.pop('layer_details', None)
                    if len(labels_found)>0:
                        result = labels_found[0] # return the first one found
                        response =  dict(
                            result=result, # returns str
                            #assessor_info=[question['assessor_answer']],
                            assessor_info=[],
                            #layer_details=[dict(name=schema_section, label=result, details=details, question=question)]
                            layer_details=[dict(name=schema_section, label=result, details=details, question=question)]
                        )
                        return response
                    else:
                        #logger.warn(f'Iterating Layers - \'{question["question"][:25]} ...\': operator_response {operator_response} not found from layer details["layer_name"]')
                        pass

        except Exception as e:
            logger.error(f'SELECT: Searching Question in SQS processed_questions dict: \'{question}\'\n{e}')

        return response

    def find_multiselect(self, item):
        ''' Widget --> multi-select
            1. question['operator_response']  --> contains results from SQS intersection and equality comparison

            result --> result (list of labels that match operator_response)
        '''
        response = {}
        question = {}
        try:
            schema_question  = item['label']
            schema_section = item['name']
            item_options   = item['options']

            #processed_questions = self.get_processed_question(schema_question, widget_type=item['type'])
            processed_questions = self.spatial_join_gbq(schema_question, widget_type=item['type'])
#            if len(processed_questions) != 1:
#                # for multi-select questions, there must be only one question
#                logger.error(f'MULTI-SELECT: For multi-select question, there must be only one question, {len(processed_questions)} found: \'{question}\'')
#                return {}
#            question = processed_questions[0]

            item_labels = [i['label'] for i in item_options] # these are the available answer options proponent can choose from
            for question in processed_questions:
                for layer in question['layers']:
                    operator_response = layer['operator_response'] # these are the answers from the query intersection/difference (truncated to no. of polygons/answers to return)

                    # return only those labels that are in the available choices to the proponent
                    # case-insensitive intersection. returns labels found in both lists
                    labels_found = list({str.casefold(x) for x in item_labels} & {str.casefold(x) for x in operator_response})
                    #labels_found = [str.casefold(x) for x in operator_response]
                    labels_found.sort()

                    raw_data = layer
                    details = raw_data.pop('layer_details', None)
                    if labels_found:
                        result = list(set(labels_found))
                        response =  dict(
                            result=result,
                            #assessor_info=[question['assessor_answer']],
                            assessor_info=[],
                            layer_details=[dict(name=schema_section, label=result, details=details, question=question)]
                        )
                        return response
                    else:
                        #logger.warn(f'Iterating Layers - \'{question["question"][:25]} ...\': operator_response {operator_response} not found from layer {details["layer_name"]}')
                        pass

        except Exception as e:
            logger.error(f'MULTI-SELECT: Searching Question in SQS processed_questions dict: \'{question["question"][:25]}\'\n{e}')

        return response

    def find_other(self, item):
        ''' Widget --> text, text_area
            Iterate through spatial join response and return all items retrieved by spatial join method, that also 
            exists in item_options (from proposal.schema)

            Returns --> str 

            list1 = ['fox', 'rabbit', 'tiger']
            list2 = [12, 13]
            zipped_list = list(itertools.zip_longest(list1, list2, fillvalue ='_' ))
            [', '.join(map(str, i)) for i in zipped_list]

            Out[1]: ['fox, 12', 'rabbit, 13', 'tiger, _']
        '''
        response = {}
        question = {}
        try:
            schema_question = item['label']
            schema_section  = item['name']
            schema_label    = schema_question

            #processed_questions = self.get_processed_question(schema_question, widget_type=item['type'])
            processed_questions = self.spatial_join_gbq(schema_question, widget_type=item['type'])
            if len(processed_questions)==0:
                return {}

            layer_name = ''
            error_msg = ''
            layers_agg = []
            grouped_label = []
            grouped_resp_agg = ''
            proponent_resp_agg = ''
            assessor_resp_agg = ''
            for idx, question in enumerate(processed_questions):
                layer_details = []
                for layer in question['layers']:
                    details = layer.pop('layer_details', None)
                    label = layer['proponent_answer'] if layer['proponent_answer'] else None
                    assessor_info = layer['assessor_answer']

                    proponent_resp_agg += layer['proponent_answer'] + "\n\n"
                    assessor_resp_agg += layer['assessor_answer'] + "\n\n"

                    #print(layer)
                    #print(label)
                    #print()

                    layers_agg.append(
                        dict(
                            layer_name=details['layer_name'],
                            layer_version=details['layer_version'],
                            layer_created_date=details['layer_created_date'],
                            layer_modified_date=details['layer_modified_date'],
                            sqs_timestamp=details['sqs_timestamp'],
                            visible_to_proponent=layer['visible_to_proponent'],
                            condition=layer['condition'],
                            operator_response=layer['operator_response'],
                            proponent_answer=layer['proponent_answer'],
                            assessor_answer=layer['assessor_answer'],
                            error_msg=details['error_msg'],
                        )
                    ) 

                proponent_resp_agg = proponent_resp_agg.strip('\n')
                assessor_resp_agg = assessor_resp_agg.strip('\n')

                unique_layers = list(set([i['layer_name'] for i in layers_agg]))
                details_agg = dict(
                        layer_name=', '.join(unique_layers),
                        layer_version=details['layer_version'] if details else '',
                        layer_created_date=details['layer_created_date'] if details else '',
                        layer_modified_date=details['layer_modified_date'] if details else '',
                        sqs_timestamp=details['sqs_timestamp'] if details else '',
                    )

            question_agg = dict(
                question=question['question'] if question else '',
                answer=question['answer'] if question else '',
                other_data=question['other_data'] if question else '',
                layers=layers_agg,
            )
            response = dict(
                    result=proponent_resp_agg,
                    assessor_info = assessor_resp_agg,
                    layer_details=[dict(name=schema_section, label=proponent_resp_agg, details=details_agg, question=question_agg)]
                )

        except LayerProviderException as e:
            raise LayerProviderException(str(e))
        except Exception as e:
            logger.error(f'SELECT: Searching Question in SQS processed_questions dict: \'{question}\'\n{e}')

        #print(f'response: {response}')
        return response


class PointQueryHelper():
    """
    pq = PointQueryHelper('cddp:dpaw_regions', ['region','office'], 121.465836, -30.748890)
    pq.spatial_join()
    """

    def __init__(self, layer_name, layer_attrs, longitude, latitude):
        self.layer_name = layer_name
        self.layer_attrs = layer_attrs
        self.longitude = longitude
        self.latitude = latitude

    def spatial_join(self, predicate='within'):

        layer = Layer.objects.get(name=self.layer_name)
        layer_gdf = layer.to_gdf(all_features=True)

        # Lat Long for Kalgoolie, Goldfields
        # df = pd.DataFrame({'longitude': [121.465836], 'latitude': [-30.748890]})
        # settings.CRS = 'EPSG:4236'
        df = pd.DataFrame({'longitude': [self.longitude], 'latitude': [self.latitude]})
        point_gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude), crs=settings.CRS)

        overlay_res = gpd.sjoin(point_gdf, layer_gdf, predicate=predicate)

        attrs_exist = all(item in overlay_res.columns for item in self.layer_attrs)

        if attrs_exist:
            errors = None
            if len(self.layer_attrs)==0 or overlay_res.empty:
                # no attrs specified - so return them all
                layer_attrs = overlay_res.drop('geometry', axis=1).columns
            elif len(self.layer_attrs)>0 and attrs_exist:
                # return only requested attrs
                layer_attrs = self.layer_attrs 
            else: #elif not attrs_exist:
                # one or more attr requested not found in layer - return all attrs and error message
                layer_attrs = overlay_res.drop('geometry', axis=1).columns
                errors = f'Attribute(s) not available: {self.layer_attrs}. Attributes available in layer: {list(layer_attrs.array)}'

            #layer_attrs = self.layer_attrs if len(self.layer_attrs)>0 and attrs_exist else overlay_res.drop('geometry', axis=1).columns
            overlay_res = overlay_res.iloc[0] if not overlay_res.empty else overlay_res # convert row to pandas Series (removes index)

            try: 
                res = dict(status=status.HTTP_200_OK, name=self.layer_name, errors=errors, res=overlay_res[layer_attrs].to_dict() if not overlay_res.empty else None)
            except Exception as e:
                logger.error(e)
                res = dict(status=status.HTTP_400_BAD_REQUEST, name=self.layer_name, error=str(e), res=overlay_res.to_dict() if not overlay_res.empty else None)
        else:
            layer_attrs = overlay_res.drop('geometry', axis=1).columns
            errors = f'Attribute(s) not available: {self.layer_attrs}. Attributes available in layer: {list(layer_attrs.array)}'
            res = dict(status=status.HTTP_400_BAD_REQUEST, name=self.layer_name, errors=errors, res=None)

        return res


#from rest_framework import serializers
#class QuestionLayerMap():
#
#    def __init__(self):
#        self.questions = []
#
#    def add(self, question_layer):
#        self.questions.append(question_layer)
#
#    def __repr__(self):
#        layers = ''.join([question.layer.layer_details.layer_name for question in self.question])
#        return f'(Q): {self.question} - (A): {self.answer} ({layers})'
#
#    def serialize(self):
#        return f'{self.question_layer}'
#
#
#class QuestionLayer():
#
#    def __init__(self, question, answer, other_data):
#        self.question = question
#        self.answer = answer
#        self.other_data = other_data
#        self.layers = []
#
#    def add(self, layer_result):
#        self.layers.append(layer_result)
#
#    def __repr__(self):
#        layers = ''.join([layer.layer_details.layer_name for layer in self.layers])
#        return f'(Q): {self.question} - (A): {self.answer} ({layers})'
#
#    def serialize(self):
#        return f'{self.layer_details}'
#
#
#class LayerResult():
#
#    def __init__(self, visible_to_proponent, layer_details, condition, operator_response, proponent_answer, assessor_answer):
#        self.visible_to_proponent = visible_to_proponent
#        self.layer_details = layer_details
#        self.condition = condition
#        self.operator_response = operator_response
#        self.proponent_answer = proponent_answer
#        self.assessor_answer = assessor_answer
#
#    def __repr__(self):
#        return f'{self.layer_details}'
# 
#    def serialize(self):
#        return f'{self.layer_details}'
#
#
#class LayerConditionSerializer(serializers.Serializer):
#    intersection_operator = serializers.CharField(max_length=100)
#    attr_name = serializers.CharField(max_length=100)
#    operator = serializers.CharField(max_length=20)
#    value = serializers.CharField(max_length=100)
#
#
#class LayerCondition():
#
#    def __init__(self, intersection_operator, attr_name, operator, value):
#        self.intersection_operator = intersection_operator
#        self.attr_name = attr_name
#        self.operator = operator
#        self.value = value
#
#    def __repr__(self):
#        _str = f'{self.intersection_operator}, {self.attr_name} -- {self.operator}'
#        if self.value:
#            _str = f'{_str} -- {self.value}' 
#        return _str
# 
#    def serialize(self):
#        return f'{self.intersection_operator}, version {self.attr_name}'
#
#
#class LayerDetail():
#
#    def __init__(self, layer_name, layer_version, layer_crs, layer_created_date, layer_modified_date, column_name, sqs_timestamp, error_msg):
#        self.layer_name = layer_name
#        self.layer_version = layer_version
#        self.layer_crs = layer_crs
#        self.layer_created_date = layer_created_date
#        self.layer_dified_date = layer_modified_date
#        self.column_name = column_name
#        self.sqs_timestamp = sqs_timestamp
#        self.error_msg = error_msg
#
#    def __repr__(self):
#        return f'{self.layer_name} (v{self.layer_version})'
# 
#    def serialize(self):
#        return f'{self.layer_name}, version {self.layer_version}'


''' 
from sqs.utils.geoquery_utils import LayerDetail, LayerCondition, LayerResult, QuestionLayer, QuestionLayerMap                                                                                             

condition1 = LayerCondition(intersection_operator='Overlapping', attr_name='CPT_DBCA_REGIONS', operator='IsNotNull', value=None)

layer_result1 = LayerResult(visible_to_proponent=True,  layer_details=layer_details1, condition=condition1, operator_response=['P1:', 'National Park'], proponent_answer=['P1:', 'National Park'], assessor_answer=['A1:', 'National Park'])

question_result = QuestionLayer(question='1.0 Proposal title', answer=None, other_data=[{'show_add_info_section_prop': True}])

question_result.add(layer_result1)

questions = QuestionLayerMap()
questions.add(question_layer)
'''
