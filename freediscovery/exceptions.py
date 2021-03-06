# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from contextlib import contextmanager
import os
import sys

from flask import jsonify


class _BaseException(Exception):
    status_code = -1
    message = 'base exception'

    def __init__(self, message=None):
        Exception.__init__(self, message)
        if message is not None:
            self.message = message

    def to_dict(self):
        rv = {'message':  '{} {}: {}'.format(self.status_code,
                        type(self).__name__, self.message)}
        return rv


class NotFound(_BaseException):
    status_code = 404
    message = 'Not Found'


class DatasetNotFound(NotFound):
    status_code = 500
    message = 'Dataset Not Found'


class ModelNotFound(NotFound):
    status_code = 500
    message = 'Model Not Found'


class InitException(_BaseException):
    status_code = 500
    message = 'Model Not Found'


class WrongParameter(_BaseException):
    status_code = 500
    message = 'Model Not Found'


class NotImplementedFD(_BaseException):
    status_code = 500
    message = 'Not implemented'

class OptionalDependencyMissing(_BaseException):
    status_code = 500
    message = 'Not Found'
