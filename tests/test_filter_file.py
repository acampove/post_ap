'''
File containing tests for FilterFile class
'''
import os
import glob
import shutil
from importlib.resources   import files

import pytest
from dmu.logging.log_store import LogStore
from post_ap.filter_file   import FilterFile

log = LogStore.add_logger('post_ap:test_filter_file')
# --------------------------------------
class Data:
    '''
    Data class with shared attributes
    '''
    mc_test_turbo    = 'root://eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/MC/2024/TUPLE.ROOT/00265061/0000/00265061_00000002_1.tuple.root'
    data_test_turbo  = 'root://eoslhcb.cern.ch//eos/lhcb/grid/prod/lhcb/anaprod/lhcb/LHCb/Collision24/FTUPLE.ROOT/00231371/0000/00231371_00000001_1.ftuple.root'

    output_dir       = '/tmp/post_ap/tests/filter_file'

    l_args_config    = [True, False]
# --------------------------------------
def _move_outputs(test_name : str) -> None:
    l_root = glob.glob('*.root')
    l_text = glob.glob('*.txt' )
    l_path = l_root + l_text
    npath  = len(l_path)

    target_dir = f'{Data.output_dir}/{test_name}'
    log.info(f'Moving {npath} to {target_dir}')
    os.makedirs(target_dir, exist_ok=True)
    for source in l_path:
        file_name = os.path.basename(source)
        shutil.move(source, f'{target_dir}/{file_name}')
# --------------------------------------
@pytest.fixture(scope='session', autouse=True)
def _initialize():
    '''
    Will set loggers, etc
    '''
    log.info('Initializing')

    cfg_path = files('post_ap_data').joinpath('post_ap/v5.yaml')
    os.environ['CONFIG_PATH'] = str(cfg_path)

    LogStore.set_level('dmu:rdataframe:atr_mgr', 30)
    LogStore.set_level('post_ap:selector'      , 20)
    LogStore.set_level('post_ap:utilities'     , 30)
    LogStore.set_level('post_ap:FilterFile'    , 20)
# --------------------------------------
@pytest.mark.parametrize('kind' , ['turbo'])
def test_dt(kind : bool):
    '''
    Run test on data
    '''
    sample_name = 'data_test'
    path        = getattr(Data, f'{sample_name}_{kind}')

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_dt')
# --------------------------------------
@pytest.mark.parametrize('kind' , ['turbo'])
def test_mc(kind : str):
    '''
    Run test on MC
    '''
    sample_name = 'mc_test'
    path        = getattr(Data, f'{sample_name}_{kind}')
    sample_name = 'mc_24_w37_39_magdown_sim10d_12113002_bu_kmumu_eq_btosllball05_dpc_tuple'

    obj = FilterFile(sample_name=sample_name, file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_mc')
# --------------------------------------
def test_bad_mcdt():
    '''
    Run test on MC with broken MCDT
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/mc_bad_mcdt.root'

    obj = FilterFile(sample_name='mc_test', file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_bad_mcdt')
# --------------------------------------
def test_rpk_ee_mc():
    '''
    Run test on MC for RpK electron sample
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_ee_mc.root'

    obj = FilterFile(sample_name='mc_test', file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_rpk_ee_mc')
# --------------------------------------
def test_rpk_mm_mc():
    '''
    Run test on MC for RpK muon sample
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_mm_mc.root'

    obj = FilterFile(sample_name='mc_test', file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_rpk_mm_mc')
# --------------------------------------
def test_rpk_data():
    '''
    Run test on data for RpK
    '''
    path= '/home/acampove/cernbox/Run3/analysis_productions/for_local_tests/rpk_data.root'

    obj = FilterFile(sample_name='data_rpk_test', file_path=path)
    obj.dump_contents  = True
    obj.max_run        = 1000
    obj.max_save       =  100
    obj.run(skip_saving=False)

    _move_outputs('test_rpk_data')
# --------------------------------------
