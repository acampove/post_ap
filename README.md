# Description

This project is used to:

- Filter, slim, trim the trees from a given AP production
- Rename branches

This is done using configurations in a YAML file and through Ganga jobs.

## Installation

You will need to install this project in a virtual environment provided by micromamba. 
For that, check [this](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html)
Once micromamba is installed in your system:

- Make sure that the `${HOME}/.local` directory does not exist. If a dependency
of `post_ap` is installed there, `ganga` would have to be pointed to that location and to
the location of the virtual environment. This is too complicated and should not be done.

- Create a new environment:

```bash
# python 3.11 is used by DIRAC and it's better to also use it here 
micromamba create -n post_ap python==3.11
micromamba activate post_ap
```

- In the `$HOME/.bashrc` export `POSTAP_PATH`, which will point to the place where your environment
is installed, e.g.:

```bash
export POSTAP_PATH=/home/acampove/micromamba/envs/run3/bin
```

which is needed to find the executables.

- Install `XROOTD` using:

```bash
micromamba install xrootd
```

which is needed to download the ntuples and is not a python project, therefore
it cannot be installed with `pip`.

- Install this project

```bash
pip install post_ap
```

- In order to make Ganga aware of the `post_ap` package, in `$HOME/.ganga.py` add:

```python
import sys

# Or the proper place where the environment is installed in your system
sys.path.append('/home/acampove/micromamba/envs/post_ap/lib/python3.11/site-packages')
```

- This project is used from inside Ganga. To have access to Ganga do:

```bash
. cvmfs/lhcb.cern.ch/lib/LbEnv

# Make a proxy that lasts 100 hours
lhcb-proxy-init -v 100:00
```

- To check that this is working, open ganga and run:

```python
from post_ap.pfn_reader        import PFNReader
```

# Submitting jobs

For this one would run a line like:

```bash
job_filter_ganga -n job_name -p PRODUCTION -s SAMPLE -c /path/to/config/file.yaml -b BACKEND -v VERSION_OF_ENV 
```
- The number of jobs will be equal to the number of PFNs, up to 500 jobs.
- The code used to filter reside in the grid and the only thing the user has to do is to provide the latest version

## Check latest version of virtual environment

The jobs below will run with code from a virtual environment that is already in the grid. One should use the
latest version of this environment. To know the latest versions, run:

```bash
# In a separate terminal open a shell with access to dirac
post_shell

# Run this command for a list of environmets
list_venvs
```

The `post_shell` terminal won't be used to send jobs.

## Config file

Here is where all the configuration goes and an example of a config can be found [here](https://github.com/acampove/config_files/blob/main/post_ap/v3.yaml)

## Optional

- In order to improve the ganga experience use: 

```bash
# Minimizes messages when opening ganga
# Does not start monitoring of jobs by default
alias ganga='ganga --quiet --no-mon'
```

in the `$HOME/.bashrc` file. Monitoring can be turned on by hand as explained [here](https://twiki.cern.ch/twiki/bin/viewauth/LHCb/FAQ/GangaLHCbFAQ#How_can_I_run_the_monitoring_loo)
