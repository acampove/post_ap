'''
Module containing FilterFile class
'''

import os
import tqdm
import utils_noroot          as utnr

from ROOT                  import RDataFrame, TFile, RDF
from log_store             import log_store

import data_checks.utilities as utdc
from data_checks.selector  import selector

log = log_store.add_logger('data_checks:FilterFile')
# --------------------------------------
class FilterFile:
    '''
    Class used to pick a ROOT file path and produce a smaller version
    '''
    # pylint: disable=too-many-instance-attributes
    # --------------------------------------
    def __init__(self, kind : str, file_path : str, cfg_nam : str):
        self._kind         = kind
        self._file_path    = file_path
        self._cfg_nam      = cfg_nam

        self._cfg_dat      : dict
        self._nevts        : int
        self._is_mc        : bool
        self._l_line_name  : list[str]
        self._store_branch : bool
        self._has_lumitree : bool

        self._initialized  = False
    # --------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._cfg_dat = utdc.load_config(self._cfg_nam)

        self._check_mcdt()
        self._set_tree_names()
        self._set_save_pars()

        self._initialized = True
    # --------------------------------------
    def _check_mcdt(self):
        '''
        Will set self._is_mc flag based on config name
        '''
        if   self._cfg_nam is None:
            raise ValueError('cfg_nam is set to None')
        elif self._cfg_nam.startswith('dt_'):
            self._is_mc = False
        elif self._cfg_nam.startswith('mc_'):
            self._is_mc = True
        else:
            log.error(f'Cannot determine Data/MC from config name: {self._cfg_nam}')
            raise
    # --------------------------------------
    def _set_save_pars(self):
        try:
            self._nevts = self._cfg_dat['saving']['max_events']
            log.info(f'Filtering dataframe with {self._nevts} entries')
        except KeyError:
            log.debug('Not filtering, max_events not specified')

        try:
            self._store_branch = self._cfg_dat['saving']['store_branch']
        except KeyError:
            log.debug('Not storing branches')
    # --------------------------------------
    def _get_names_from_config(self):
        '''
        Will return all the HLT line names from config
        '''
        d_l_name = self._cfg_dat['hlt_lines']
        l_name   = list()
        for val in d_l_name.values():
            l_name += val

        nline = len(l_name)
        log.debug(f'Found {nline} lines in config')

        return l_name
    # --------------------------------------
    def _set_tree_names(self):
        '''
        Will set the list of line names `self._l_line_name`
        '''
        ifile = TFile.Open(self._file_path)
        l_key = ifile.GetListOfKeys()
        l_nam = [ key.GetName() for key in l_key]
        ifile.Close()

        self._has_lumitree = 'lumiTree' in l_nam

        l_hlt = [ hlt           for hlt in l_nam if hlt.startswith('Hlt2RD_') ]
        nline = len(l_hlt)
        log.debug(f'Found {nline} lines in file')

        l_tree_name = self._get_names_from_config()
        l_flt = [ flt           for flt in l_hlt if flt in l_tree_name  ]

        nline = len(l_flt)
        log.info(f'Found {nline} lines in file that match config')
        self._l_line_name = l_flt
    # --------------------------------------
    def _keep_branch(self, name):
        '''
        Will take the name of a branch and return True (keep) or False (drop)
        '''
        l_svar = self._cfg_dat['drop_branches']['starts_with']
        for svar in l_svar:
            if name.startswith(svar):
                return False

        l_ivar = self._cfg_dat['drop_branches']['includes'   ]
        for ivar in l_ivar:
            if ivar in name:
                return False

        return True
    # --------------------------------------
    def _get_column_names(self, rdf : RDataFrame) -> list[str]:
        '''
        Takes dataframe, returns list of column names as strings
        '''
        v_name = rdf.GetColumnNames()
        l_name = [ name.c_str() for name in v_name ]

        return l_name
    # --------------------------------------
    def _rename_kaon_branches(self, rdf):
        '''
        Will define K_ = H_ for kaon branches. K_ branches will be dropped later
        '''

        l_name = self._get_column_names(rdf)
        l_kaon = [ name for name in l_name if name.startswith('K_') ]

        log.debug(110 * '-')
        log.info('Renaming kaon branches')
        log.debug(110 * '-')
        for old in l_kaon:
            new = 'H_' + old[2:]
            log.debug(f'{old:<50}{"->":10}{new:<50}')
            rdf = rdf.Define(new, old)

        return rdf
    # --------------------------------------
    def _rename_mapped_branches(self, rdf : RDataFrame) -> RDataFrame:
        '''
        Will define branches from mapping in config. Original branches will be dropped later
        '''
        l_name = self._get_column_names(rdf)
        d_name = self._cfg_dat['rename']
        log.debug(110 * '-')
        log.info('Renaming mapped branches')
        log.debug(110 * '-')
        for org, new in d_name.items():
            if org not in l_name:
                continue

            log.debug(f'{org:<50}{"->":10}{new:<50}')
            rdf = rdf.Define(new, org)

        return rdf
    # --------------------------------------
    def _rename_branches(self, rdf : RDataFrame) -> RDataFrame:
        rdf = self._rename_kaon_branches(rdf)
        rdf = self._rename_mapped_branches(rdf)

        return rdf
    # --------------------------------------
    def _define_branches(self, rdf : RDataFrame) -> RDataFrame:
        '''
        Will take dataframe and define columns if "define" field found in config
        Returns dataframe
        '''
        if 'define' not in self._cfg_dat:
            log.debug('Not defining any variables')
            return rdf

        log.debug(110 * '-')
        log.info('Defining variables')
        log.debug(110 * '-')
        for name, expr in self._cfg_dat['define'].items():
            log.debug(f'{name:<50}{expr:<200}')

            rdf = rdf.Define(name, expr)

        return rdf
    # --------------------------------------
    def _define_heads(self, rdf : RDataFrame) -> RDataFrame:
        '''
        Will take dataframe and define columns starting with head in _l_head to B_
        Returns dataframe
        '''
        log.info('Defining heads')

        d_redef = self._cfg_dat['redefine_head']
        l_name  = self._get_column_names(rdf)
        for org_head, trg_head in d_redef.items():
            l_to_redefine = [ name for name in l_name if name.startswith(org_head) ]
            if len(l_to_redefine) == 0:
                log.debug(f'Head {org_head} not found, skipping')
                continue

            rdf = self._define_head(rdf, l_to_redefine, org_head, trg_head)

        return rdf
    # --------------------------------------
    def _define_head(self, rdf : RDataFrame, l_name : list, org_head : str, trg_head : str):
        '''
        Will define list of columns with a target head (e.g. B_some_name) from some original head (e.g. Lb_some_name)
        '''

        log.debug(f'Original: {org_head}')
        log.debug(f'Target:   {trg_head}')
        log.debug(155 * '-')
        log.debug(f'{"Original":<70}{"--->":<15}{"New":<70}')
        log.debug(155 * '-')
        for org_name in l_name:
            tmp_name = org_name.removeprefix(org_head)
            trg_name = f'{trg_head}{tmp_name}'

            log.debug(f'{org_name:<70}{"--->":<15}{trg_name:<70}')
            rdf      = rdf.Define(trg_name, org_name)

        return rdf
    # --------------------------------------
    def _get_rdf(self, line_name):
        '''
        Will build a dataframe from a given HLT line and return the dataframe
        _get_branches decides what branches are kept
        '''

        log.debug(30 * '')
        log.debug(30 * '')
        log.debug(30 * '-')
        log.debug(30 * '')
        log.info(f'Processing line: {line_name}')
        log.debug(30 * '-')
        rdf      = RDataFrame(f'{line_name}/DecayTree', self._file_path)
        rdf      = self._define_heads(rdf)
        rdf      = self._rename_branches(rdf)
        rdf      = self._define_branches(rdf)
        rdf.lumi = False
        rdf      = self._attach_branches(rdf, line_name)
        l_branch = rdf.l_branch
        ninit    = rdf.ninit
        nfnal    = rdf.nfnal
        norg     = rdf.Count().GetValue()

        if not rdf.lumi:
            obj  = selector(rdf=rdf, cfg_nam=self._cfg_nam, is_mc=self._is_mc)
            rdf  = obj.run()
        nfnl     = rdf.Count().GetValue()

        log.debug(100 * '-')
        log.info(f'{line_name:<50}{ninit:<10}{"->":5}{nfnal:<10}{norg:<10}{"->":5}{nfnl:<10}')
        log.debug(100 * '-')

        rdf.name     = line_name
        rdf.l_branch = l_branch

        return rdf
    # --------------------------------------
    def _attach_branches(self, rdf, line_name):
        '''
        Will check branches in rdf
        Branches are dropped by only keeping branches in _keep_branch function
        line_name used to name file where branches will be saved.
        '''
        l_col = self._get_column_names(rdf)
        ninit = len(l_col)
        l_flt = [ flt         for flt in l_col if self._keep_branch(flt) ]
        nfnal = len(l_flt)

        rdf.ninit    = ninit
        rdf.nfnal    = nfnal
        rdf.l_branch = l_flt
        rdf.name     = line_name

        if self._store_branch:
            utnr.dump_json(l_flt, f'./{line_name}.json')

        return rdf
    # --------------------------------------
    def _tree_name_from_line_name(self, line_name : str) -> str:
        '''
        Given a line name, it will check the config file to return KEE or KMM
        to decide where the tree will be saved.
        '''
        d_cfg  = self._cfg_dat['saving']['tree_name']
        for tree_name, l_line_line in d_cfg.items():
            if line_name in l_line_line:
                log.debug(f'Using tree name {tree_name} for line {line_name}')
                return tree_name

        raise ValueError(f'No tree name found for line \"{line_name}\"')
    # --------------------------------------
    def _save_file(self, l_rdf):
        '''
        Will save all ROOT dataframes to a file
        '''
        opts                   = RDF.RSnapshotOptions()
        opts.fMode             = 'update'
        opts.fCompressionLevel = self._cfg_dat['saving']['compression']

        file_name = os.path.basename(self._file_path)
        preffix   = file_name.replace('.root', '').replace('.', '_')

        for rdf in tqdm.tqdm(l_rdf, ascii=' -'):
            line_name = rdf.name
            l_branch  = rdf.l_branch
            tree_name = self._tree_name_from_line_name(line_name)

            rdf.Snapshot(tree_name, f'{self._kind}_{preffix}_{line_name}.root', l_branch, opts)

            if not self._is_mc:
                lumi_rdf = RDataFrame('lumiTree', self._file_path)
                lumi_rdf.Snapshot('lumiTree', f'{self._kind}_{preffix}_{line_name}.root', [], opts)
    # --------------------------------------
    @utnr.timeit
    def run(self):
        '''
        Will run filtering of files
        '''
        self._initialize()

        log.debug(f'Filtering: {self._file_path}')
        log.debug(100 * '-')
        log.debug(f'{"Line":<50}{"BOrg":<10}{"":5}{"BFnl":<10}{"#Org":<10}{"":5}{"#Fnl":<10}')
        log.debug(100 * '-')
        l_rdf = [ self._get_rdf(tree_name) for tree_name in self._l_line_name ]

        self._save_file(l_rdf)
# --------------------------------------
