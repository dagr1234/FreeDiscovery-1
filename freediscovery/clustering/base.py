# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import os.path

import numpy as np
from sklearn.externals import joblib

from ..base import BaseEstimator
from ..text import FeatureVectorizer
from ..utils import setup_model, _rename_main_thread
from ..stop_words import COMMON_FIRST_NAMES, CUSTOM_STOP_WORDS
from ..exceptions import (DatasetNotFound, ModelNotFound, InitException,
                            WrongParameter)


### Clustering methods for FreeDiscovery
### This is highly inspired by the scikit example


MAX_N_TOP_WORDS = 1000

def select_top_words(word_list, n=10):
    """ Filter out cluster term names"""
    import re
    from nltk.stem.porter import PorterStemmer
    st = PorterStemmer()
    out_st  = []
    out = []
    for word in word_list:
        word_st = st.stem(word)
        if len(word_st) <= 2 or\
               re.match('\d+', word_st) or \
               re.match('[^a-zA-Z0-9]', word_st) or\
               word    in COMMON_FIRST_NAMES or \
               word    in CUSTOM_STOP_WORDS or\
               word_st in out_st: # ignore stemming duplicate
            continue
        out_st.append(word_st)
        out.append(word)
        if len(out) >= n:
            break

    return out

def _generate_lsi(lsi_components=None):
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import Normalizer
    #from .lsi import TruncatedSVD_LSI
    from sklearn.decomposition import TruncatedSVD

    if lsi_components is not None:
        #svd = TruncatedSVD_LSI(lsi_components)
        ## do normalization by the singular values
        #svd.transform = svd.transform_lsi
        svd = TruncatedSVD(lsi_components)
        normalizer = Normalizer(copy=False)
        lsi = make_pipeline(svd, normalizer)
    else:
        lsi = None

    return lsi


class ClusterLabels(object):
    def __init__(self, vect, model, pars, lsi=None, cluster_indices=None):
        """ Calculate the cluster labels.

        This is an internal class that is called by Clustering

        Parameters
        ----------
        cluster_indices: list, default=None
           if not None, ignore clustering given by the clustering model and compute
           terms for the cluster provided by the given indices
        """
        self.model = model
        self.vect = vect
        self.n_clusters = pars['n_clusters']
        self.lsi = lsi
        self._compute_centroids(cluster_indices)


    def _compute_centroids(self, cluster_indices=None):
        model = self.model
        lsi = self.lsi
        if cluster_indices is None:
            method_name = type(model).__name__
            if method_name not in ['MiniBatchKMeans', 'AgglomerativeClustering',
                                        'Birch']:
                raise NotImplementedError('Method name: {} not implented!'.format(method_name))

            centroids = self.model.cluster_centers_ # centroids were previously computed
        else:
            centroids = cluster_indices['centroids']

        self.n_clusters = centroids.shape[0] # might happen that a cluster has 0 data points points
                                         # in which case n_clusters = centroids.shape[0]
        if lsi is None:
            order_centroids = centroids.argsort()[:, ::-1]
        else:
            svd = lsi.steps[0][1] # first step of the pipeline
            original_space_centroids = svd.inverse_transform(centroids)
            order_centroids = original_space_centroids.argsort()[:, ::-1]
        self._order_centroids = order_centroids


    def predict(self, method='centroid-frequency', n_top_words=6):
        """ Compute the cluster labels

        Parameters
        ----------

        method: str, optional, default='centroid-frequency'
            the method used to compute the centroid labels
            Must be one of 'centroid-frequency',
        n_top_words: int, default=10
           keep only most relevant n_top_words words

        Returns
        -------
        cluster_labels: array [n_samples]
        """
        self.n_top_words = n_top_words
        if self.n_top_words > MAX_N_TOP_WORDS:
            raise ValueError
        if method == 'centroid-frequency':
            return self._predict_centroid_freq()
        else:
            raise ValueError


    def _predict_centroid_freq(self):
        """ Return cluster labels based on the most frequent words (tfidf) at cluster centroids """
        terms = self.vect.get_feature_names()
        cluster_terms = []
        for i in range(self.n_clusters):
            terms_i = [terms[ind] for ind in self._order_centroids[i, :MAX_N_TOP_WORDS]]
            terms_i = select_top_words(terms_i, self.n_top_words)
            cluster_terms.append(terms_i)
        return cluster_terms


        #"if lsi is not None:
        #"    silhouette_score_res = silhouette_score(X, cluster_labels)
        #"else:
        #"    silhouette_score_res = np.nan # this takes too much memory to compute with the raw matrix



class Clustering(BaseEstimator):

    _DIRREF = "clustering"

    def __init__(self, cache_dir='/tmp/', dsid=None, mid=None):
        """
        Document clustering

        Parameters
        ----------
          cache_dir : str
             directory where to save temporary and regression files
          dsid : str, optional
             dataset id
          mid : str, optional
             model id
        """

        if dsid is None and mid is not None:
            self.dsid = dsid = self.get_dsid(cache_dir, mid)
            self.mid = mid
        elif dsid is not None:
            self.dsid  = dsid
            self.mid = None
        elif dsid is None and mid is None:
            raise ValueError

        self.fe = FeatureVectorizer(cache_dir=cache_dir, dsid=dsid)
        if self.fe._pars['use_hashing']:
            raise NotImplementedError('Using clustering with hashed features is not supported by FreeDiscovery!')

        self.model_dir = os.path.join(self.fe.cache_dir, dsid, self._DIRREF)

        if not os.path.exists(self.model_dir):
            os.mkdir(self.model_dir)

        if mid is not None:
            self.km = self.load(mid)
            self._pars = self._load_pars()
        else:
            self.km = None
            self._pars = None




    def _cluster_func(self, n_clusters, km, pars=None, lsi=None):
        """ A helper function for clustering, includes base method used by
        all clustering implementations """
        import warnings
        from sklearn.neighbors import NearestCentroid
        if pars is None:
            pars = {}
        pars.update(km.get_params(deep=True))
        pars['n_clusters'] = n_clusters
        X = joblib.load(os.path.join(self.fe.dsid_dir, 'features'))

        mid, mid_dir = setup_model(self.model_dir)

        if lsi is not None:
            X = lsi.fit_transform(X)
            joblib.dump(X, os.path.join(self.model_dir, mid,  'lsi_features'), compress=9)
            pars['lsi'] = lsi

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            km.fit(X)
        pars['lsi'] = lsi
        self.mid = mid
        self.mid_dir = mid_dir

        if not hasattr(km, 'cluster_centers_'):
            # i.e. model is not MiniBatchKMeans => compute centroids
            km.cluster_centers_ = NearestCentroid().fit(X, km.labels_).centroids_

        joblib.dump(km, os.path.join(self.model_dir, mid,  'model'), compress=9)
        joblib.dump(pars, os.path.join(self.model_dir, mid,  'pars'), compress=9)

        self.km = km
        self._pars  = pars

        htree = self._get_htree(km)

        return km.labels_, htree


    @staticmethod
    def _get_htree(km):
        method_name = type(km).__name__
        if method_name == 'AgglomerativeClustering':
            htree = {'n_leaves': km.n_leaves_,
                     'n_components': km.n_components_,
                     'children': km.children_}
        else:
            htree = {}
        return htree


    def compute_labels(self, label_method='centroid-frequency', n_top_words=6,
            cluster_indices=None):
        """ Compute the cluster labels

        Parameters
        ----------
        label_method: str, default='centroid-frequency'
            the method used for computing the cluster labels
        n_top_words: int, default=10
           keep only most relevant n_top_words words
        cluster_indices: list, default=None
           if not None, ignore clustering given by the clustering model and compute
           terms for the cluster provided by the given indices

        Returns
        -------
        cluster_labels: array [n_samples]

        """
        vect = joblib.load(os.path.join(self.fe.dsid_dir, 'vectorizer'))
        lsi = self._pars['lsi']
        if cluster_indices is not None:
            args = {'indices': cluster_indices}
            X = joblib.load(os.path.join(self.fe.dsid_dir, 'features'))
            X = X[cluster_indices]

            if lsi:
                X = lsi.transform(X)
            else:
                raise NotImplementedError('This case should work, '
                        'but it was not tested so far, disabling it')
            centroids = np.atleast_2d(X.mean(axis=0))
            args['centroids'] = centroids
        else:
            args = None

        lb = ClusterLabels(vect, self.km, self._pars, lsi=lsi,
                cluster_indices=args)
        terms = lb.predict(method=label_method, n_top_words=n_top_words)
        return terms


    def k_means(self, n_clusters, lsi_components=None, batch_size=1000):
        """
        Perform K-mean clustering

        Parameters
        ----------
        n_clusters: int
           number of clusters
        lsi_components: int
           apply LSA before the clustering algorithm
        batch_size: int
           the bath size for the MiniBatchKMeans algorithm
        """
        from sklearn.cluster import MiniBatchKMeans
        pars = {"batch_size": batch_size}
        lsi = _generate_lsi(lsi_components)

        km = MiniBatchKMeans(n_clusters=n_clusters, init='k-means++', n_init=10,
                    init_size=batch_size, batch_size=batch_size)

        return self._cluster_func(n_clusters, km, pars, lsi=lsi)


    def birch(self, n_clusters, threshold=0.5, lsi_components=None):
        """
        Perform Birch clustering

        Parameters
        ----------
        n_clusters: int
            number of clusters
        lsi_components: int
            apply LSA before the clustering algorithm
        threshold: float
            birch threshold
        """
        from sklearn.cluster import Birch
        pars = None
        if lsi_components is None:
            raise ValueError("lsi_components=None detected. You must use LSI with Birch \
                    clustering for scaling reasons.")

        lsi = _generate_lsi(lsi_components)

        km = Birch(n_clusters=n_clusters, threshold=threshold)

        return self._cluster_func(n_clusters, km, pars, lsi=lsi)


    def ward_hc(self, n_clusters, lsi_components=None, n_neighbors=10):
        """
        Perform Ward hierarchical clustering

        Parameters
        ----------
        n_clusters: int
            number of clusters
        lsi_components: int
            apply LSA before the clustering algorithm
        n_neighbors: int
            N nearest neighbors used for computing the connectivity matrix
        """
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.neighbors import kneighbors_graph
        pars = None
        if lsi_components is None:
            raise ValueError("lsi_components=None detected. You must use LSI with Birch \
                    clustering for scaling reasons.")

        lsi = _generate_lsi(lsi_components)

        # This is really not efficient as it's done a second time in _cluster_func
        X = joblib.load(os.path.join(self.fe.dsid_dir, 'features'))
        X_lsi = lsi.fit_transform(X)
        connectivity = kneighbors_graph(X_lsi, n_neighbors=n_neighbors,
                                   include_self=False)

        km = AgglomerativeClustering(n_clusters=n_clusters, linkage='ward',
                                       connectivity=connectivity)

        return self._cluster_func(n_clusters, km, pars, lsi=lsi)


    def scores(self, ref_labels, labels):
        """
        Parameters
        ----------
        ref_labels: list,
            reference labels
        labels: list,
            computed labels
        """
        from sklearn.metrics import ( v_measure_score, adjusted_rand_score,
                            #silhouette_score
                            )
        out = {}
        out['adjusted_rand_score'] = adjusted_rand_score(ref_labels, labels)
        out['v_measure_score'] = v_measure_score(ref_labels, labels)
        #out['silhouette_score'] = silhouette_score(X, labels, sample_size=1000)
        return out


    def _load_pars(self):
        """ Load parameters from cache specified by a mid """

        mid = self.mid

        mid_dir = os.path.join(self.model_dir, mid)
        if not os.path.exists(mid_dir):
            raise ValueError('Model id {} not found in the cache!'.format(mid))

        pars = joblib.load(os.path.join(mid_dir, 'pars'))

        return pars


    def load(self, mid):
        """ Load results from cache specified by a mid """

        mid_dir = os.path.join(self.model_dir, mid)
        if not os.path.exists(mid_dir):
            raise ValueError('Model id {} not found in the cache!'.format(mid))

        km = joblib.load(os.path.join(mid_dir, 'model'))
        return km


