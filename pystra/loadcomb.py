# -*- coding: utf-8 -*-

from .model import LimitState
from .model import StochasticModel
from .form import Form
from .correlation import CorrelationMatrix


class LoadCombination:
    """Class for running load combination cases.

    Attributes
    ----------
    lsf : function
        Limit State Function
    df_corr : DataFrame
        DataFrame of user defined correlation (if specified).
    distributions_max : dict
        Dictionary of maximum distributions
    distributions_pit : dict
        Dictionary of point-in-time distributions
    distributions_other : dict
        Dictionary of static distributions
    distributions_resistance : dict
        Dictionary of resistance distributions
    dict_dist_comb : dict
        Dictionary of distributions for all load combinations
    label_comb_vrs : str
        Labels of combination variables
    label_comb_cases : str
        Labels of combination variables
    label_resist : str
        Labels of resistance variables
    label_other : str
        Labels of static variables
    label_all : str
        Labels of all variables including design multiplier

    """

    def __init__(
        self,
        lsf,
        dict_dist_comb,
        list_dist_resist,
        list_dist_other=None,
        corr=None,
        list_const=None,
        opt=None,
        dict_comb_cases=None,
    ):
        """
        Initialize class instance.

        Parameters
        ----------
        lsf : Function
            Limit State Function.
        dict_dist_comb : Dictionary
            Nested dictionary of load effects and their corresponding max and
            pit distributions.
        list_dist_resist : List
            List of resistance distribution.
        list_dist_other : List, optional
            List of other remaining random variables.
        corr : DataFrame, optional
            User-defined Dataframe containing correlations between random
            variables. Note: corr.index = corr.columns = [<list-of-rvs>]
        list_const : List, optional
            List of LSF constants as Pystra Constants.
        opt : Object, optional
            Pystra AnalysisOptions object to specify options for the
            reliability analysis.
        dict_comb_cases : Dictionary, optional
            Dictionary containing the identifiers of load cases as keys and
            list of identifiers of max load effects as values, i.e.
            {<load-case-name>:[<max-load-effects>],}. By default, each combination
            load effect is taken as maximum in a load case.

        Returns
        -------
        None.

        """
        self.lsf = lsf
        self.distributions_comb = dict_dist_comb
        self.distributions_max = {
            xx: dict_dist_comb[xx]["max"] for xx in dict_dist_comb
        }
        self.distributions_pit = {
            xx: dict_dist_comb[xx]["pit"] for xx in dict_dist_comb
        }
        self.distributions_other = (
            {xx.name: xx for xx in list_dist_other}
            if list_dist_other is not None
            else None
        )
        self.distributions_resistance = {xx.name: xx for xx in list_dist_resist}
        self.dict_comb_cases = dict_comb_cases
        self.comb_cases_max = [dict_comb_cases[xx] for xx in dict_comb_cases]
        self._check_input()
        self.num_comb = self._set_num_comb()
        self.dict_dist_comb = self._create_dict_dist_comb()
        self.df_corr = corr
        self.options = opt
        self.label_comb_cases = list(dict_comb_cases.keys())
        self.label_comb_vrs = list(dict_dist_comb.keys())
        self.label_resist = list(self.distributions_resistance.keys())
        self.label_other = (
            list(self.distributions_other.keys()) if list_dist_other is not None else []
        )
        self.label_all = self.label_resist + self.label_other + self.label_comb_vrs
        if list_const is not None:
            self.constant = {xx.name: xx for xx in list_const}
            self.label_const = list(self.constant.keys())
            self.label_all = self.label_all + self.label_const
        else:
            self.constant = None
            self.label_const = None

        self.dict_label = {
            "resist": self.label_resist,
            "other": self.label_other,
            "comb_vrs": self.label_comb_vrs,
            "comb_cases": self.label_comb_cases,
            "const": self.label_const,
            "all": self.label_all,
        }

    def _check_input(self):
        """
        Check consistency of supplied input.

        Raises
        ------
        Exception
            Raised when Length of Max variables does not match length of
            point-in-time variables.

        Returns
        -------
        None.

        """
        if len(self.distributions_max) != len(self.distributions_pit):
            raise Exception(
                "\nLength of Max variables {} does not match\
                      length of point-in-time variables {}".format(
                    len(self.distributions_max), len(self.distributions_pit)
                )
            )

    def get_label(self, label_type):
        """
        Get Labels corresponding to label_type.

        Parameters
        ----------
        label_type : String
            Label type. Possible values: "resist", "other", "comb_vrs",
            "comb_cases", "const", and "all".

        Returns
        -------
        label : List
            List of labels corresponding to label_type.

        """
        label = self.dict_label[label_type]
        return label

    def _set_num_comb(self):
        """
        Set the number of load combination cases.

        Returns
        -------
        num_comb : Float
            Number of load combination cases..

        """
        self.comb_cases_max = (
            [[xx] for xx in self.distributions_max.keys()]
            if self.comb_cases_max is None
            else self.comb_cases_max
        )
        num_comb = len(self.comb_cases_max)
        return num_comb

    def get_num_comb(self):
        """
        Get the number of load combination cases.

        Returns
        -------
        Float
            Number of load combination cases.

        """
        return self.num_comb

    def get_dict_dist_comb(self):
        """
        Get the dictionary of distributions for all load combination cases.

        Returns
        -------
        Dictionary
            Dictionary of distributions for all load combination cases.

        """
        return self.dict_dist_comb

    def _create_dict_dist_comb(self):
        """
        Create a dictionary containing distributions for respective load
        combination cases.

        Returns
        -------
        dict_dist : Dictionary
            Dictionary of distributions for all load combination cases.

        """
        dict_dist = {}
        for loadc_name, loadc in self.dict_comb_cases.items():
            dict_loadc = {}
            for key, value in self.distributions_resistance.items():
                dict_loadc.update({key: value})
            if self.distributions_other is not None:
                for key, value in self.distributions_other.items():
                    dict_loadc.update({key: value})
            for key, value in self.distributions_max.items():
                if key in loadc:
                    dict_loadc.update({key: value})
                else:
                    dict_loadc.update({key: self.distributions_pit[key]})
            dict_dist.update({loadc_name: dict_loadc})
        return dict_dist

    def _get_corr_for_stochastic_model(self, stochastic_model):
        """
        Get correlation data for stochastic model.

        This function utilizes the input correlation data and re-creates
        the correlation matrix based on the sequence of random variables
        as per the stochastic model.

        Parameters
        ----------
        stochastic_model : Object
            Pystra StochasticModel object for the reliability analysis.

        Returns
        -------
        corr : Numpy Array
            Correlation matrix with variables sequenced as per the stochastic
            model.

        """
        sequence_rvs = list(stochastic_model.getVariables().keys())
        dfcorr_tmp = self.df_corr.reindex(columns=sequence_rvs, index=sequence_rvs)
        corr = dfcorr_tmp.values
        return corr

    def run_reliability_case(self, lcn=None, **kwargs):
        """
        Create and run reliability analysis using input LSF
        for a given load case, lcn.

        Parameters
        ----------
        lcn : float, optional
            Load case number. The default is 1.
        **kwargs : Keyword arguments
            Specify any distribution overrides for the stochastic model random
            variables or constants as keyword arguments.
            Therefore, if kwargs contains any LSF argument, then kwarg specified
            distribution is used for that argument in the reliability analyses.

        Returns
        -------
        form : Pystra FORM object
            FORM reliability analysis object.

        """
        lcn = self.label_comb_cases[0] if lcn is None else lcn
        ls = LimitState(self.lsf)
        sm = StochasticModel()
        if self.constant is not None:
            for key, value in self.constant.items():
                if key in kwargs:
                    sm.addVariable(kwargs[key])
                else:
                    sm.addVariable(value)
        dict_dist = self.dict_dist_comb[lcn]
        for key, value in dict_dist.items():
            if key in kwargs:
                sm.addVariable(kwargs[key])
            else:
                sm.addVariable(value)
        if self.df_corr is not None:
            corr = self._get_corr_for_stochastic_model(sm)
            sm.setCorrelation(CorrelationMatrix(corr))
        form = Form(sm, ls) if self.options is None else Form(sm, ls, self.options)
        form.run()

        return form

    def eval_lsf_kwargs(self, set_value=0.0, set_const=None, **kwargs):
        """
        Evaluate the LSF based on the supplied Keyword arguments, setting
        all others to set_value.

        Parameters
        ----------
        set_value : Float, optional
            Set value of random variable LSF arguments other than those
            supplied as keyword arguments. The default is 0.0.
        set_const : Float, optional
            Set value of constant LSF arguments other than those supplied as
            keyword arguments. The default is None.
        **kwargs : Keyword arguments
            LSF Keyword arguments.

        Returns
        -------
        gX : Float
            Evaluation of the LSF.

        """
        ## Identify the RVs which are missing in kwargs
        if self.constant is not None:
            set_miss = (
                set(self.label_all) - set(kwargs.keys()) - set(self.constant.keys())
            )
        else:
            set_miss = set(self.label_all) - set(kwargs.keys())
        ## Set value of missing RVs to set_value
        if len(set_miss) > 0:
            kwargs.update({xx: set_value for xx in set_miss})
        ## Set value of constants
        for key, values in self.constant.items():
            if key not in kwargs and set_const is None:
                kwargs.update({key: self.constant[key].getValue()})
            elif key not in kwargs and set_const is not None:
                kwargs.update({key: set_const})
        gX = self.lsf(**kwargs)
        return gX
