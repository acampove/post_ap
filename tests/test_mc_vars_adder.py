'''
Module containing tests for MCVarsAdder class
'''
# pylint: disable=no-member

import numpy
import pytest
from ROOT                    import RDataFrame
from ROOT                    import RDF
from dmu.logging.log_store   import LogStore

from post_ap.mc_vars_adder   import MCVarsAdder

log = LogStore.add_logger('post_ap:test_mc_vars_adder')
# -------------------------------------------------
class Data:
    '''
    Class used to hold shared attributes
    '''
    ngen    = 1000
    nrec    =  500
    rng     = numpy.random.default_rng(seed=10)
    sam     = 'mc_24_w31_34_magup_sim10d_11102005_bd_kplpimn_eq_cpv2017_dpc_tuple'
    arr_bpt = rng.uniform(0, 10_000, ngen)
# -------------------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    LogStore.set_level('post_ap:mc_vars_adder'     , 10)
    LogStore.set_level('post_ap:test_mc_vars_adder', 10)
# -------------------------------------------------
def _get_rdf(kind : str, with_block : bool) -> RDataFrame:
    nentries = {'gen' : Data.ngen, 'rec' : Data.nrec}[kind]
    d_data   = {}

    arr_bpt        = Data.rng.choice(Data.arr_bpt, size=nentries)
    d_data['B_PT'] = numpy.sort(arr_bpt)

    if kind == 'rec':
        d_data['EVENTNUMBER'] = Data.rng.integers(0, 1000_000, size=nentries)

    if with_block:
        d_data['block']       = Data.rng.choice([1,2], size=nentries)

    return RDF.FromNumpy(d_data)
# -------------------------------------------------
def test_add_to_gen():
    '''
    Tests addition of columns to MCDT
    '''

    rdf_gen = _get_rdf(kind='gen', with_block=False)
    rdf_rec = _get_rdf(kind='rec', with_block=True)

    obj = MCVarsAdder(
            sample_name = Data.sam,
            rdf_rec     = rdf_rec,
            rdf_gen     = rdf_gen)
    _   = obj.get_rdf()
# -------------------------------------------------
def test_add_to_rec():
    '''
    Tests addition of columns to DecayTree
    '''

    rdf_rec = _get_rdf(kind='rec', with_block=False)

    obj = MCVarsAdder(
            sample_name = Data.sam,
            rdf_rec     = rdf_rec)
    rdf       = obj.get_rdf()
    arr_block = rdf.AsNumpy(['block'])['block']

    none = numpy.sum(arr_block == 1)
    ntwo = numpy.sum(arr_block == 2)

    assert none == 53
    assert ntwo == 47
# -------------------------------------------------
