'''
Module containing FilterFile class
'''

import os
import fnmatch
import tqdm

from ROOT                  import RDataFrame, TFile, RDF
from dmu.logging.log_store import LogStore

import dmu.generic.utilities as gut
from dmu.rfile.rfprinter   import RFPrinter

import post_ap.utilities as utdc
from post_ap.selector  import Selector

log = LogStore.add_logger('post_ap:FilterFile')
# --------------------------------------
class FilterFile:
    '''
    Class used to pick a ROOT file path and produce a smaller version
    '''
    # pylint: disable=too-many-instance-attributes
    # --------------------------------------
    def __init__(self, sample_name : str, file_path : str):
        '''
        sample_name : Sample name, e.g. mc_..., data_...
        file_path   : PFN or path to ROOT file
        '''
        self._sample_name  = sample_name
        self._file_path    = file_path

        self._cfg_dat      : dict
        self._d_trans      : dict
        self._nevts        : int
        self._is_mc        : bool
        self._l_line_name  : list[str]
        self._store_branch : bool
        self._has_lumitree : bool
        self._dump_contents: bool = False

        self._initialized  = False
    # --------------------------------------
    def _initialize(self):
        if self._initialized:
            return

        self._cfg_dat = utdc.load_config()
        self._d_trans = self._cfg_dat['transformations']

        self._check_mcdt()
        self._set_tree_names()
        self._set_save_pars()

        self._initialized = True
    # --------------------------------------
    @property
    def dump_contents(self) -> bool:
        '''
        Flag indicating if a text file with the file contents will be saved or only the ROOT file
        '''
        return self._dump_contents

    @dump_contents.setter
    def dump_contents(self, value) -> None:
        if not isinstance(value, bool):
            raise ValueError('Value is not a bool: {value}')

        self._dump_contents = value
    # --------------------------------------
    def _check_mcdt(self):
        '''
        Will set self._is_mc flag based on config name
        '''

        if   self._sample_name.startswith('mc_'):
            self._is_mc = True
        elif self._sample_name.startswith('data_'):
            self._is_mc = False
        else:
            raise ValueError(f'Cannot determine Data/MC from sample name: {self._sample_name}')
    # --------------------------------------
    def _set_save_pars(self):
        try:
            self._nevts = self._d_trans['saving']['max_events']
            log.info(f'Filtering dataframe with {self._nevts} entries')
        except KeyError:
            log.debug('Not filtering, max_events not specified')

        try:
            self._store_branch = self._d_trans['saving']['store_branch']
        except KeyError:
            log.debug('Not storing branches')
    # --------------------------------------
    def _get_names_from_config(self) -> list[str]:
        '''
        Will return all the HLT line names from config
        '''
        d_l_name = self._d_trans['hlt_lines']
        l_name   = []
        for val in d_l_name.values():
            l_name += val

        nline = len(l_name)
        log.debug(f'Found {nline} lines in config')

        return l_name
    # --------------------------------------
    def _set_tree_names(self) -> None:
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
        log.info(f'Found {nline} lines in file:')
        for line in l_hlt:
            log.debug(f'{"":<10}{line:<30}')

        l_tree_name = self._get_names_from_config()
        l_flt = [ flt           for flt in l_hlt if flt in l_tree_name  ]

        nline = len(l_flt)
        log.info(f'Found {nline} lines in file that match config')
        for line in l_flt:
            log.debug(f'{"":<10}{line:<30}')

        self._l_line_name = l_flt
    # --------------------------------------
    def _keep_branch(self, name : str) -> bool:
        '''
        Will take the name of a branch and return True (keep) or False (drop)
        '''
        l_svar = self._d_trans['drop_branches']['starts_with']
        for svar in l_svar:
            if name.startswith(svar):
                return False

        l_svar = self._d_trans['drop_branches']['ends_with']
        for svar in l_svar:
            if name.endswith(svar):
                return False

        l_ivar = self._d_trans['drop_branches']['includes'   ]
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
    def _rename_kaon_branches(self, rdf : RDataFrame) -> RDataFrame:
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
        d_name = self._d_trans['rename']
        log.debug(110 * '-')
        log.info('Renaming mapped branches')
        log.debug(110 * '-')
        for org, new in d_name.items():
            if org not in l_name:
                log.debug(f'Skipping: {org}')
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
        if 'define' not in self._d_trans:
            log.debug('Not defining any variables')
            return rdf

        log.debug(110 * '-')
        log.info('Defining variables')
        log.debug(110 * '-')
        for name, expr in self._d_trans['define'].items():
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

        d_redef = self._d_trans['redefine_head']
        l_name  = self._get_column_names(rdf)
        for org_head, trg_head in d_redef.items():
            l_to_redefine = [ name for name in l_name if name.startswith(org_head) ]
            if len(l_to_redefine) == 0:
                log.debug(f'Head {org_head} not found, skipping')
                continue

            rdf = self._define_head(rdf, l_to_redefine, org_head, trg_head)

        return rdf
    # --------------------------------------
    def _define_head(self, rdf : RDataFrame, l_name : list, org_head : str, trg_head : str) -> RDataFrame:
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
    def _get_sel_kind(self, line_name : str) -> str:
        d_cat : dict[str,list[str]] = self._d_trans['categories']
        for cat, l_line_name in d_cat:
            if line_name in l_line_name:
                return cat

        raise ValueError(f'Cannot find category for line {line_name}')
    # --------------------------------------
    def _get_rdf(self, line_name : str) -> RDataFrame:
        '''
        Will build a dataframe from a given HLT line and return the dataframe
        _get_branches decides what branches are kept
        '''

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
            sel_kin = self._get_sel_kind(line_name)
            obj     = Selector(rdf=rdf, is_mc=self._is_mc)
            rdf     = obj.run(sel_kind=sel_kin)

        nfnl = rdf.Count().GetValue()

        log.info(45 * '-')
        log.info(f'{"Line    ":<20}{"     ":5}{line_name:<20}')
        log.info(f'{"Branches":<20}{ninit:<10}{"->":5}{nfnal:<20}')
        log.info(f'{"Entries ":<20}{norg:<10}{"->":5}{nfnl:<20}')
        log.info(45 * '-')

        rdf.name     = line_name
        rdf.l_branch = l_branch

        return rdf
    # --------------------------------------
    def _wild_card_filter(self, l_name : list[str]) -> list[str]:
        '''
        Takes list of branch names
        removes only the ones matching wild card
        returns remaining list
        '''

        l_wild_card = self._d_trans['drop_branches']['wild_card']

        l_to_drop = []
        ndrop     = 0
        for wild_card in l_wild_card:
            l_found    = fnmatch.filter(l_name, wild_card)
            if not l_found:
                log.debug(f'No branches dropped for wildcard {wild_card}')
                continue

            ndrop     += len(l_found)
            l_to_drop += l_found

        log.debug(f'Dropping {ndrop} wildcard branches')

        return [ name for name in l_name if name not in l_to_drop ]
    # --------------------------------------
    def _attach_branches(self, rdf : RDataFrame, line_name : str) -> RDataFrame:
        '''
        Will check branches in rdf
        Branches are dropped by:
            - keeping branches in _keep_branch function
            - Removing wildcarded branches in _wild_card_filter functio

        line_name used to name file where branches will be saved.
        '''
        l_col = self._get_column_names(rdf)
        ninit = len(l_col)
        l_flt = [ flt for flt in l_col if self._keep_branch(flt) ]
        l_flt = self._wild_card_filter(l_flt)
        nfnal = len(l_flt)

        rdf.ninit    = ninit
        rdf.nfnal    = nfnal
        rdf.l_branch = l_flt
        rdf.name     = line_name

        if self._store_branch:
            gut.dump_json(l_flt, f'./{line_name}.json')

        return rdf
    # --------------------------------------
    def _tree_name_from_line_name(self, line_name : str) -> str:
        '''
        Given a line name, it will check the config file to return KEE or KMM
        to decide where the tree will be saved.
        '''
        d_cfg  = self._d_trans['saving']['tree_name']
        for tree_name, l_line_line in d_cfg.items():
            if line_name in l_line_line:
                log.debug(f'Using tree name {tree_name} for line {line_name}')
                return tree_name

        raise ValueError(f'No tree name found for line \"{line_name}\"')
    # --------------------------------------
    def _save_file(self, l_rdf : list[RDataFrame]) -> None:
        '''
        Will save all ROOT dataframes to a file
        '''
        opts                   = RDF.RSnapshotOptions()
        opts.fMode             = 'update'
        opts.fOverwriteIfExists= True
        opts.fCompressionLevel = self._d_trans['saving']['compression']

        file_name = os.path.basename(self._file_path)
        preffix   = file_name.replace('.root', '').replace('.', '_')

        for rdf in tqdm.tqdm(l_rdf, ascii=' -'):
            line_name = rdf.name
            l_branch  = rdf.l_branch
            tree_name = self._tree_name_from_line_name(line_name)

            file_path = f'{line_name}.root'
            rdf.Snapshot(tree_name, file_path, l_branch, opts)

            log.debug(f'Saved: {file_path}:{tree_name}')

            self._save_contents(file_path)

            if not self._is_mc:
                log.debug('Saving lumitree')
                lumi_rdf = RDataFrame('lumiTree', self._file_path)
                l_name   = self._get_column_names(lumi_rdf)
                lumi_rdf.Snapshot('lumiTree', f'{self._sample_name}_{preffix}_{line_name}.root', l_name, opts)
                log.debug('Saved lumitree')
    # --------------------------------------
    def _save_contents(self, file_path : str) -> None:
        if not self._dump_contents:
            log.debug('Not saving branch list')
            return

        log.debug('Saving branch list')

        obj = RFPrinter(path = file_path)
        obj.save()
    # --------------------------------------
    @gut.timeit
    def run(self) -> None:
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
