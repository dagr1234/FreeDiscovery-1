
# coding: utf-8

# # Document Clustering example (Python)

# In[1]:

import os
import re
import numpy as np

import pandas as pd
import sys
import shutil
from IPython.display import display, HTML
from freediscovery.text import FeatureVectorizer
from freediscovery.clustering import Clustering
from freediscovery.utils import _silent
from time import time
import requests

pd.options.display.float_format = '{:,.3f}'.format

data_dir = "../freediscovery_shared/tar_fd_benchmark"
examples_to_server_path = "../" # relative path between this file and the FreeDiscovery source folder

BASE_URL = "http://localhost:5001/api/v0"  # FreeDiscovery server URL


# # 1. Feature extraction (non hashed)

# In[2]:

n_features = 30000
cache_dir = '/tmp/'

fe = FeatureVectorizer(cache_dir=cache_dir)
uuid = fe.preprocess("../"+data_dir+'/data',
                             n_features=n_features, use_hashing=False,
                             use_idf=True, stop_words='english')
uuid, filenames  = fe.transform()


# # 2. Document Clustering (LSI + K-Means)

# In[4]:

cat = Clustering(cache_dir=cache_dir, dsid=uuid)

n_clusters = 10
n_top_words = 6
lsi_components = 50

def repr_clustering(labels, terms):
    out = []
    for ridx, row in enumerate(terms):
        out.append({'cluster_names': row, 'N_documents': (labels == ridx).sum()})
    out = pd.DataFrame(out).sort_values('N_documents', ascending=False)
    return out

t0 = time()
with _silent('stderr'): # ignore some deprecation warnings
    labels, tree  = cat.k_means(n_clusters, lsi_components=lsi_components)
    terms = cat.compute_labels(n_top_words=n_top_words)
t1 = time()

print('    .. computed in {:.1f}s'.format(t1 - t0))
display(repr_clustering(labels, terms))


# # 3. Document Clustering (LSI + Ward Hierarchical Clustering)

# In[6]:

t0 = time()
with _silent('stderr'): # ignore some deprecation warnings
    labels, tree  = cat.ward_hc(n_clusters,
                        lsi_components=lsi_components,
                        n_neighbors=5   # this is the connectivity constraint
                        )
    terms = cat.compute_labels(n_top_words=n_top_words)
t1 = time()

print('    .. computed in {:.1f}s'.format(t1 - t0))
display(repr_clustering(labels, terms))


# In[ ]:



