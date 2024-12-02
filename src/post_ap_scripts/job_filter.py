'''
Script which will create filtering DIRAC jobs and use them to submit
filtering jobs
'''

import os
import argparse
from importlib.resources import files

from DIRAC.Interfaces.API.Dirac import Dirac
from DIRAC.Interfaces.API.Job   import Job
from DIRAC                      import initialize as initialize_dirac
from DIRAC                      import gLogger

from tqdm    import trange

# ---------------------------------------
class Data:
    '''
    Class used to hold shared attributes
    '''
    snd_dir = None
    njob    = None
    name    : str
    dset    = None
    conf    = None
    venv    = None
    mode    = None
    epat    = os.environ['VENVS']
    runner_path : str
# ---------------------------------------
def _get_job(jobid):
    j = Job()
    j.setCPUTime(36000)
    j.setDestination('LCG.CERN.cern')
    j.setExecutable(Data.runner_path, arguments=f'{Data.dset} {Data.conf} {Data.njob} {jobid} {Data.epat}')
    j.setInputSandbox([f'LFN:/lhcb/user/a/acampove/run3/venv/{Data.venv}/dcheck.tar'])
    j.setOutputData(['*.root'], outputPath=Data.name)
    j.setName(f'{Data.name}_{jobid:03}')

    return j
# ---------------------------------------
def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Used to send filtering jobs to the grid')
    parser.add_argument('-n', '--name' , type =str, help='Name of job, to identify it' , required=True)
    parser.add_argument('-c', '--conf' , type =str, help='Type of filter, e.g. comp'   , required=True)
    parser.add_argument('-d', '--dset' , type =str, help='Dataset, e.g. dt_2024_turbo' , required=True)
    parser.add_argument('-j', '--njob' , type =int, help='Number of grid jobs'         , required=True)
    parser.add_argument('-e', '--venv' , type =str, help='Index of virtual environment', required=True)
    parser.add_argument('-m', '--mode' , type =str, help='Run locally or in the grid'  , required=True,
                        choices=['local', 'wms'])

    args = parser.parse_args()

    return args
# ---------------------------------------
def _initialize() -> None:
    args         = _get_args()
    Data.snd_dir = f'{os.getcwd()}/sandbox_{args.name}_{args.dset}_{args.conf}'
    Data.name    = args.name
    Data.conf    = args.conf
    Data.dset    = args.dset
    Data.njob    = args.njob
    Data.venv    = args.venv
    Data.mode    = args.mode

    os.makedirs(Data.snd_dir, exist_ok=False)
    gLogger.setLevel('warning')
    initialize_dirac()

    runner_path      = files('post_ap_grid').joinpath('run_filter')
    Data.runner_path = str(runner_path)
# ---------------------------------------
def main():
    '''
    Script starts here
    '''
    _initialize()
    l_jobid = []
    dirac = Dirac()
    for jobid in trange(Data.njob, ascii=' -'):
        job    = _get_job(jobid)
        d_info = dirac.submitJob(job, mode=Data.mode)

        try:
            jobid = d_info['JobID']
        except KeyError:
            jobid = -1

        l_jobid.append(jobid)

        if 'test' in Data.name:
            break

        if Data.mode == 'local':
            break

    with open(f'{Data.snd_dir}/jobids.out', 'w', encoding='utf-8') as ofile:
        for jobid in l_jobid:
            ofile.write(f'{jobid}\n')
# ---------------------------------------
if __name__ == '__main__':
    main()
