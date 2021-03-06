# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os.path

from flask import Flask
from flask_restful import Api, Resource
from flask import jsonify

from .resources import (FeaturesApi, FeaturesApiElement, LsiApi, ModelsApi,
                            ModelsApiElement, ModelsApiPredict,
                            ModelsApiTest, LsiApiElement,
                            LsiApiElementTest, LsiApiElementPredict,
                            ClusteringApiElement, KmeanClusteringApi,
                            BirchClusteringApi, WardHCClusteringApi,
                            DupDetectionApi, DupDetectionApiElement
                            )


class CatchAll(Resource):
    def get(self, url):
        print("accessing", url)
    def post(self, url):
        print("accessing", url)


def fd_app(cache_dir):
    """ API app for FreeDiscovery """

    if not os.path.exists(cache_dir):
        raise ValueError('Cache_dir {} does not exist!'.format(cache_dir))
    app = Flask('freediscovery_api')
    api = Api(app)
    #app.config['DEBUG'] = False


    ## Actually setup the Api resource routing here

    for resource_el, url in [(FeaturesApi,          "/feature-extraction"),
                             (FeaturesApiElement,   '/feature-extraction/<dsid>'),
                             (ModelsApi,            '/categorization/'),
                             (ModelsApiElement,     '/categorization/<mid>'),
                             (ModelsApiPredict,     '/categorization/<mid>/predict'),
                             (ModelsApiTest,        "/categorization/<mid>/test"),
                             (LsiApi,               '/lsi/'),
                             (LsiApiElement,        '/lsi/<mid>'),
                             (LsiApiElementPredict, '/lsi/<mid>/predict'),
                             (LsiApiElementTest,    '/lsi/<mid>/test'),
                             (KmeanClusteringApi,   '/clustering/k-mean/'),
                             (BirchClusteringApi,   '/clustering/birch'),
                             (WardHCClusteringApi,  '/clustering/ward_hc'),
                             (ClusteringApiElement, '/clustering/<method>/<mid>'),
                             (DupDetectionApi,      '/duplicate-detection/simhash'),
                             (DupDetectionApiElement,'/duplicate-detection/simhash/<mid>'),
                             #(CatchAll, "/<url>")
                             ]:
        # monkeypatching, not great
        resource_el._cache_dir = cache_dir
        api.add_resource(resource_el, '/api/v0' + url, strict_slashes=False)

    @app.errorhandler(500)
    def handle_error(error):
        #response = jsonify(error.to_dict())
        response = jsonify({'message': 'help'})
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_404_error(error):
        response = jsonify({"message": str(error)})
        response.status_code = 404 
        return response

    @app.errorhandler(400)
    def handle_400_error(error):
        response = jsonify({"message": str(error)})
        response.status_code = 400
        return response

    return app

