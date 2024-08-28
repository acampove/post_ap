#!/usr/bin/env python3

from importlib.resources import files
from log_store           import log_store

import apd
import logging
import argparse
import utils_noroot          as utnr
import data_checks.utilities as utdc

log=log_store.add_logger('data_checks:save_pfns')
#------------------------------------
class data:
    config = None
    log_lvl= None
#------------------------------------
def get_args():
    parser = argparse.ArgumentParser(description='Will use apd to save a list of paths to ROOT files in EOS')
    parser.add_argument('-c', '--config' , type=str, help='Name of config file, without TOML extension')
    parser.add_argument('-l', '--log_lvl', type=int, help='Logging level', default=20, choices=[10, 20, 30, 40])
    args = parser.parse_args()

    data.config = args.config
    data.log_lvl= args.log_lvl
#------------------------------------
def save_pfns():
    cfg_dat = utdc.load_config(data.config)
    d_samp  = cfg_dat['sample']
    d_prod  = cfg_dat['production']

    log.debug('Reading paths from APD')
    obj     = apd.get_analysis_data(**d_prod)
    l_path  = obj(**d_samp)
    l_path.sort()

    pfn_path= files('data_checks_data').joinpath(f'{data.config}.json')
    log.info(f'Saving to: {pfn_path}')
    utnr.dump_json(l_path, pfn_path)
#------------------------------------
def set_log():
    log_store.set_level('data_checks:save_pfns', data.log_lvl)
    if data.log_lvl == 10:
        log_store.set_level('data_checks:utilities', data.log_lvl)

        logging.basicConfig()
        log_apd=logging.getLogger('apd')
        log_apd.setLevel(data.log_lvl)
#------------------------------------
def main():
    get_args()
    set_log()
    save_pfns()
#------------------------------------
if __name__ == '__main__':
    main()

