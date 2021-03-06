#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
#from __future__ import unicode_literals

import os.path
from unittest import SkipTest

import numpy as np
from numpy.testing import assert_allclose, assert_equal
import pytest

from freediscovery.text import FeatureVectorizer
from .run_suite import check_cache


# adapted from https://github.com/seomoz/simhash-py/blob/master/test/test.py
jabberwocky = '''
    Twas brillig, and the slithy toves
      Did gyre and gimble in the wabe:
    All mimsy were the borogoves,
      And the mome raths outgrabe.
    "Beware the Jabberwock, my son!
      The jaws that bite, the claws that catch!
    Beware the Jubjub bird, and shun
      The frumious Bandersnatch!"
    He took his vorpal sword in hand:
      Long time the manxome foe he sought --
    So rested he by the Tumtum tree,
      And stood awhile in thought.
    And, as in uffish thought he stood,
      The Jabberwock, with eyes of flame,
    Came whiffling through the tulgey wood,
      And burbled as it came!
    One, two! One, two! And through and through
      The vorpal blade went snicker-snack!
    He left it dead, and with its head
      He went galumphing back.
    "And, has thou slain the Jabberwock?
      Come to my arms, my beamish boy!
    O frabjous day! Callooh! Callay!'
      He chortled in his joy.
    `Twas brillig, and the slithy toves
      Did gyre and gimble in the wabe;
    All mimsy were the borogoves,
      And the mome raths outgrabe.'''
jabberwocky_author = ' - Lewis Carroll (Alice in Wonderland)'

def fd_setup():
    basename = os.path.dirname(__file__)

    cache_dir = check_cache()

    data_dir = os.path.join(basename, "..", "data", "ds_001", "raw")

    n_features = 110000

    fe = FeatureVectorizer(cache_dir=cache_dir)
    uuid = fe.preprocess(data_dir, file_pattern='.*\d.txt',
                         n_features=n_features, use_hashing=True,
            stop_words='english')
    uuid, filenames  = fe.transform()
    return cache_dir, uuid, filenames, fe


def test_simhash():

    try:
        from simhash import num_differing_bits
    except ImportError:
        raise SkipTest
    from sklearn.feature_extraction.text import HashingVectorizer
    from freediscovery.simhash import SimhashDuplicates

    DISTANCE = 4

    fe = HashingVectorizer(ngram_range=(4,4), analyzer='word', n_features=2**30)

    X = fe.fit_transform([jabberwocky,
                          jabberwocky + jabberwocky_author,
                          jabberwocky_author,
                          jabberwocky])

    sh = SimhashDuplicates()
    sh.fit(X)

    # make sure small changes in the text results in a small number of different bytes
    assert num_differing_bits(*sh._fit_shash[:2]) <= 2
    # different text produces a large number of different bytes
    assert num_differing_bits(*sh._fit_shash[1:3]) >= 30

    # same text produces a zero bit difference
    assert num_differing_bits(*sh._fit_shash[[0,-1]]) == 0

    simhash, cluster_id, dup_pairs = sh.query(distance=DISTANCE, blocks=42)

    assert simhash[0] == simhash[-1]       # duplicate documents have the same simhash
    assert cluster_id[0] == cluster_id[-1] # and belong to the same cluster

    for idx, shash in enumerate(simhash):
        if (shash == simhash).sum() == 1: # ignore duplicates
            assert sh.get_index_by_hash(shash) == idx

    for pairs in dup_pairs:
        assert num_differing_bits(*pairs) <= DISTANCE


def test_dup_detection():
    try:
        import simhash
    except ImportError:
        raise SkipTest
    from freediscovery.simhash import DuplicateDetection
    cache_dir, uuid, filenames, fe = fd_setup()

    dd = DuplicateDetection(cache_dir=cache_dir, dsid=uuid)
    dd.fit()
    simhash, cluster_id, dup_pairs = dd.query(distance=3)
