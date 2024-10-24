#!/usr/bin/env python3

from importlib.resources import files
from log_store           import log_store

import re
import apd
import logging
import argparse
import utils_noroot          as utnr
import data_checks.utilities as utdc

log=log_store.add_logger('data_checks:save_pfns')
#------------------------------------
class data:
    config      = None
    log_lvl     = None
    local_config=False
#------------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Will use apd to save a list of paths to ROOT files in EOS')
    parser.add_argument('-c', '--config' , type=str, help='Name of config file, without TOML extension')
    parser.add_argument('-l', '--log_lvl', type=int, help='Logging level', default=20, choices=[10, 20, 30, 40])
    parser.add_argument('-L', '--loc_cfg', type=int, help='Will pick up local (1) or remote (0, default) version of TOML config', default=0, choices=[0, 1])
    args = parser.parse_args()

    data.config       = args.config
    data.log_lvl      = args.log_lvl
    data.local_config = args.loc_cfg
#------------------------------------
def get_pfns():
    utdc.local_config = data.local_config

    cfg_dat = utdc.load_config(data.config)
    d_prod  = cfg_dat['production']

    log.debug('Reading paths from APD')
    obj     = apd.get_analysis_data(**d_prod)

    if   data.config.startswith('dt_'):
        d_pfn = get_dt_pfns(obj)
    elif data.config.startswith('mc_'):
        d_pfn = get_mc_pfns(obj)
    else:
        log.error(f'Unrecognized start of config: {data.config}')
        raise

    print_pfn_info(d_pfn)

    return d_pfn
#------------------------------------
def print_pfn_info(d_pfn):
    nsample=0
    for l_sam in d_pfn.values():
        nsample += len(l_sam)

    log.info(f'Found {nsample} PFNs')
#------------------------------------
def get_dt_pfns(ap_obj):
    cfg_dat = utdc.load_config(data.config)
    l_samp  = cfg_dat['sample']['names']
    l_path  = []
    for samp in l_samp:
        l_path += ap_obj(name=samp)

    return {data.config : l_path}
#------------------------------------
def get_mc_pfns(ap_obj):
    '''
    Reads from AP object sample info and returns samplename -> PFNs dictionary
    '''
    cfg_dat   = utdc.load_config(data.config)
    regex     = cfg_dat['sample']['name_rx']
    version   = cfg_dat['sample']['version']
    pattern   = re.compile(regex)
    collection= ap_obj.all_samples()

    d_path = {}
    for d_info in collection:
        name = d_info['name']
        vers = d_info['version']

        if vers != version:
            continue

        if not pattern.match(name):
            continue

        sam          = collection.filter(name=name)
        d_path[name] = sam.PFNs()

    return d_path
#------------------------------------
def _save_pfns(d_path):
    '''
    Save dictionary of samplename -> PFNs to JSON
    '''
    pfn_path= files('data_checks_data').joinpath(f'{Data.config}.json')
    log.info(f'Saving to: {pfn_path}')
    utnr.dump_json(d_path, pfn_path)
#------------------------------------
def _set_log():
    log_store.set_level('data_checks:save_pfns', Data.log_lvl)
    if Data.log_lvl == 10:
        log_store.set_level('data_checks:utilities', Data.log_lvl)

        logging.basicConfig()
        log_apd=logging.getLogger('apd')
        log_apd.setLevel(Data.log_lvl)
#------------------------------------
def main():
    '''
    Script starts here
    '''
    _get_args()
    _set_log()
    d_pfn=_get_pfns()
    _save_pfns(d_pfn)
#------------------------------------
if __name__ == '__main__':
    main()
