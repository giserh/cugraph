# Copyright (c) 2019, NVIDIA CORPORATION.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import random

import pytest
from scipy.io import mmread

import cudf
import cugraph


def read_mtx_file(mm_file):
    print('Reading ' + str(mm_file) + '...')
    return mmread(mm_file).asfptype()


def cugraph_call(G, partitions):
    df = cugraph.spectralBalancedCutClustering(G, partitions,
                                               num_eigen_vects=partitions)
    score = cugraph.analyzeClustering_edge_cut(G, partitions, df['cluster'])
    return set(df['vertex'].to_array()), score


def random_call(G, partitions):
    random.seed(0)
    num_verts = G.num_vertices()
    assignment = []
    for i in range(num_verts):
        assignment.append(random.randint(0, partitions-1))
    assignment_cu = cudf.Series(assignment)
    score = cugraph.analyzeClustering_edge_cut(G, partitions, assignment_cu)
    return set(range(num_verts)), score


DATASETS = [
    '../datasets/karate.mtx',
    '../datasets/dolphins.mtx',
    '../datasets/netscience.mtx']
PARTITIONS = [2, 4, 8]


@pytest.mark.parametrize('graph_file', DATASETS)
@pytest.mark.parametrize('partitions', PARTITIONS)
def test_modularity_clustering(graph_file, partitions):
    # Read in the graph and get a cugraph object
    M = read_mtx_file(graph_file).tocsr()
    row_offsets = cudf.Series(M.indptr)
    col_indices = cudf.Series(M.indices)

    M = M.tocoo()
    sources = cudf.Series(M.row)
    destinations = cudf.Series(M.col)

    G_adj = cugraph.Graph()
    G_adj.add_adj_list(row_offsets, col_indices)
    G_edge = cugraph.Graph()
    G_edge.add_edge_list(sources, destinations)

    # Get the modularity score for partitioning versus random assignment
    cu_vid, cu_score = cugraph_call(G_adj, partitions)
    rand_vid, rand_score = random_call(G_adj, partitions)

    # Assert that the partitioning has better modularity than the random
    # assignment
    assert cu_score < rand_score

    # Get the modularity score for partitioning versus random assignment
    cu_vid, cu_score = cugraph_call(G_edge, partitions)
    rand_vid, rand_score = random_call(G_edge, partitions)

    # Assert that the partitioning has better modularity than the random
    # assignment
    assert cu_score < rand_score


@pytest.mark.parametrize('graph_file', DATASETS)
@pytest.mark.parametrize('partitions', PARTITIONS)
def test_modularity_clustering_with_edgevals(graph_file, partitions):
    # Read in the graph and get a cugraph object
    M = read_mtx_file(graph_file).tocsr()
    row_offsets = cudf.Series(M.indptr)
    col_indices = cudf.Series(M.indices)
    val = cudf.Series(M.data)

    G_adj = cugraph.Graph()
    G_adj.add_adj_list(row_offsets, col_indices, val)

    M = M.tocoo()
    sources = cudf.Series(M.row)
    destinations = cudf.Series(M.col)
    values = cudf.Series(M.data)

    G_edge = cugraph.Graph()
    G_edge.add_edge_list(sources, destinations, values)

    # Get the modularity score for partitioning versus random assignment
    cu_vid, cu_score = cugraph_call(G_adj, partitions)
    rand_vid, rand_score = random_call(G_adj, partitions)

    # Assert that the partitioning has better modularity than the random
    # assignment
    assert cu_score < rand_score

    # Get the modularity score for partitioning versus random assignment
    cu_vid, cu_score = cugraph_call(G_edge, partitions)
    rand_vid, rand_score = random_call(G_edge, partitions)

    # Assert that the partitioning has better modularity than the random
    # assignment
    assert cu_score < rand_score
