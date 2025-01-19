'''
Script that will make a list of dirac job IDs into a
text file with LFNs
'''
import os
import glob
import argparse
from importlib.resources import files

import tqdm
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('post_ap:lfns_from_csv')
# ----------------------------
class Data:
    '''
    Data storing shared attributes
    '''
    version  : str
    grid_dir = '/eos/lhcb/grid/user/lhcb/user/a/acampove'
    l_id     : list[str]
# ----------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Will use apd to save a list of paths to ROOT files in EOS')
    parser.add_argument('-v', '--version' , type=str, help='Version of production')
    parser.add_argument('-l', '--loglevel', type=int, help='Controls logging level', choices=[10, 20, 30], default=20)
    args = parser.parse_args()

    Data.version = args.version
    LogStore.set_level('post_ap:lfns_from_csv', args.loglevel)
# ----------------------------
def _get_jobids() -> list[str]:
    id_path = files('rx_data_lfns').joinpath(f'{Data.version}/jobid.csv')
    id_path = str(id_path)
    if not os.path.isfile(id_path):
        raise FileNotFoundError(f'Missing file: {id_path}')

    with open(id_path, encoding='utf-8') as ifile:
        text = ifile.read()

    text = text.replace('\n', '')

    l_id = text.split(',')
    nid  = len(l_id)

    log.info(f'Found {nid} job IDs')

    return l_id
# ----------------------------
def _get_lfns() -> list[str]:
    l_wc = [ f'{Data.grid_dir}/*/{jobid[:-3]}/{jobid}/' for jobid in Data.l_id ]

    l_path = []
    for wc in tqdm.tqdm(l_wc, ascii=' -'):
        l_path += glob.glob(f'{wc}/*.root')

    nlfn = len(l_path)
    if nlfn == 0:
        raise FileNotFoundError('No LFN was found')

    log.info(f'Found {nlfn} LFNs')

    return l_path
# ----------------------------
def _initialize() -> None:
    Data.l_id = _get_jobids()

    if not os.path.isdir(Data.grid_dir):
        raise FileNotFoundError(f'Missing grid directory: {Data.grid_dir}')

    log.debug(f'Looking into: {Data.grid_dir}')
# ----------------------------
def _save_lfns(l_lfn : list[str]) -> None:
    text = '\n'.join(l_lfn)
    with open('lfns.txt', 'w', encoding='utf-8') as ofile:
        ofile.write(text)

    log.info('Saved LFNs')
# ----------------------------
def main():
    '''
    Script starts here
    '''
    _parse_args()
    _initialize()

    l_lfn = _get_lfns()
    _save_lfns(l_lfn)
# ----------------------------
if __name__ == '__main__':
    main()

