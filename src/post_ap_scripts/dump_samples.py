'''
Script used to provide blocks of MC samples in a YAML file
Needed to write YAML config for post_ap
'''
# pylint: disable = too-many-ancestors

import re
import argparse
from functools           import cache
from importlib.resources import files

import yaml
from apd                    import AnalysisData
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('dmu:post_ap_scripts:dump_samples')
# ----------------------------------------------
class IndentedDumper(yaml.Dumper):
    '''
    Class needed to create indentation when saving lists as values of dictionaries in YAML files
    '''
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)
# ----------------------------------------------
class Data:
    '''
    Data class used to store shared data
    '''
    regex = r'mc_\d{2}_(w\d{2}_\d{2})_.*'
    vers  : str
    group : str
    prod  : str

    l_analysis : list[str]
# ----------------------------------------------
def _version_from_name(name : str) -> str:
    mtch = re.match(Data.regex, name)
    if not mtch:
        raise ValueError(f'Cannot find version in: {name}')

    return mtch.group(1)
# ----------------------------------------------
def _get_samples(samples) -> dict[str,list[str]]:
    d_data   = {}
    for sample in samples:
        if sample['version'] != Data.vers:
            continue

        name = sample['name']
        if not name.startswith('mc_'):
            continue

        vers = _version_from_name(name)
        if vers not in d_data:
            d_data[vers] = []

        d_data[vers].append(name)

    if len(d_data) == 0:
        raise ValueError('No samples found')

    for l_sam in d_data.values():
        l_sam.sort()

    return d_data
# ----------------------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to create a list of MC samples in YAML, split by sim production for a given (latest) version of the AP.')
    parser.add_argument('-v', '--vers'    , type =str, help='Version of AP, e.g. v1r2266', required=True)
    parser.add_argument('-p', '--prod'    , type =str, help='Production, e.g. rd_ap_2024', required=True)
    parser.add_argument('-g', '--group'   , type =str, help='Group, e.g. rd'             , required=True)
    parser.add_argument('-a', '--analyses', nargs='+', help='Analyses for which to check if samples are missing, e.g. RK, RKst')
    args = parser.parse_args()

    Data.vers       = args.vers
    Data.group      = args.group
    Data.prod       = args.prod
    Data.l_analysis = args.analyses
# ----------------------------------------------
@cache
def _load_samples() -> dict[str, list[str]]:
    path = files('post_ap_data').joinpath('samples/sample_run3.yaml')
    path = str(path)
    with open(path, encoding='utf-8') as ifile:
        d_analysis = yaml.safe_load(ifile)

    return d_analysis
# ----------------------------------------------
def _is_sample_found(sample :  str, l_sample : list[str]) -> bool:
    l_sample_lower = [ sample.lower() for sample in l_sample ]

    for sample_lower in l_sample_lower:
        if sample in sample_lower:
            return True

    return False
# ----------------------------------------------
def _get_missing_samples(l_samples_found : list[str]) -> list[str]:
    d_sam            = _load_samples()
    l_samples_needed = []
    for analysis in Data.l_analysis:
        if analysis not in d_sam:
            log.warning(f'Analysis {analysis} not found, skipping')
            continue

        l_samples_needed += d_sam[analysis]

    l_missing = [ sample for sample in l_samples_needed if _is_sample_found(sample, l_samples_found) ]

    return l_missing
# ----------------------------------------------
def _save_missing(d_sam : dict[str,list[str]]) -> None:
    if Data.l_analysis is None:
        log.info('No analysis specified, will not check for missing samples')
        return


    d_miss = {}
    for block_period, l_sam in d_sam.items():
        l_missing = _get_missing_samples(l_sam)
        d_miss[block_period] = l_missing

    with open(f'{Data.group}_{Data.prod}_{Data.vers}_miss.yaml', 'w', encoding='utf-8') as ofile:
        yaml.dump(d_miss, ofile, Dumper=IndentedDumper)
# ----------------------------------------------
def main():
    '''
    Script starts here
    '''
    _parse_args()

    datasets = AnalysisData(Data.group, Data.prod)
    samples  = datasets.all_samples()

    d_data = _get_samples(samples)
    with open(f'{Data.group}_{Data.prod}_{Data.vers}.yaml', 'w', encoding='utf-8') as ofile:
        yaml.dump(d_data, ofile, Dumper=IndentedDumper)

    _save_missing(d_data)
# ----------------------------------------------
if __name__ == '__main__':
    main()
