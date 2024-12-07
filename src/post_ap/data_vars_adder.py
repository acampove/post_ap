'''
Module containing DataVarsAdder class
'''

from ROOT import RDataFrame, Numba

from dmu.logging.log_store import LogStore

log = LogStore.add_logger('post_ap:data_vars_adder')
# -------------------------------------
@Numba.Declare(['int', 'int'], 'int')
def get_block(run_number : int, fill_number : int) -> int:
    block_run = 298626 <=  run_number <= 301278
    block_fil = 9808   <= fill_number <= 9910
    if block_run and block_fil:
        return 4

    block_run = 301325 <=  run_number <= 302403
    block_fil = 9911   <= fill_number <= 9943
    if block_run and block_fil:
        return 3

    block_run = 302429 <=  run_number <= 303010
    block_fil = 9945   <= fill_number <= 9978
    if block_run and block_fil:
        return 2

    block_run = 303092 <=  run_number <= 304604
    block_fil = 9982   <= fill_number <= 10056
    if block_run and block_fil:
        return 1

    block_run = 304648 <=  run_number <= 305739
    block_fil = 10059  <= fill_number <= 10102
    if block_run and block_fil:
        return 5

    block_run = 305802 <= run_number  <= 307544
    block_fil = 10104  <= fill_number <= 10190
    if block_run and block_fil:
        return 6

    block_run = 307576 <= run_number  <= 308098
    block_fil = 10197  <= fill_number <= 10213
    if block_run and block_fil:
        return 7

    block_run = 308104 <= run_number  <= 308540
    block_fil = 10214  <= fill_number <= 10232
    if block_run and block_fil:
        return 8

    return -1
# -------------------------------------
class DataVarsAdder:
    '''
    Class used to add variables to dataframes that only make sense for data
    It adds:

    - block      : Block number
    - is_good_run: Check for run data quality
    '''
    # -------------------------------------
    def __init__(self, rdf : RDataFrame):
        self._rdf = rdf

        self._l_name : list[str] = []
    # -------------------------------------
    def _add_dataq(self, rdf : RDataFrame, name : str) -> RDataFrame:
        log.info(f'Defining {name}')

        return rdf
    # -------------------------------------
    @property
    def names(self) -> list[str]:
        '''
        Returns names of added branches
        '''
        return self._l_name
    # -------------------------------------
    def _add_block(self, rdf : RDataFrame, name : str) -> RDataFrame:
        log.info(f'Defining {name}')
        rdf = rdf.Define(name, 'Numba::get_block(RUNNUMBER, FillNumber)')
        self._l_name.append(name)

        return rdf
    # -------------------------------------
    def get_rdf(self) -> RDataFrame:
        '''
        Returns dataframe with all variables added (or booked in this case)
        '''
        rdf = self._rdf
        rdf = self._add_dataq(rdf, 'dataq')
        rdf = self._add_block(rdf, 'block')

        return rdf
# -------------------------------------
