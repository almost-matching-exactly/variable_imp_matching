# -*- coding: utf-8 -*-
"""
Created on Sat Apr 18 18:56:18 2020
@author: Harsh
"""

import numpy as np
import scipy.optimize as opt
import pandas as pd
import sklearn.linear_model as lm
import sklearn.ensemble as ensemble
import seaborn as sns
from sklearn.model_selection import StratifiedKFold
import rpy2
from rpy2.robjects.packages import importr
from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage
import rpy2.robjects.numpy2ri
from rpy2.robjects import pandas2ri

rpy2.robjects.numpy2ri.activate()
pandas2ri.activate()

utils = importr('utils')
dbarts = importr('dbarts')


def bart(outcome, treatment, data, n_splits=2, result='brief', method='new', gen_skf=None):
    if gen_skf is None:
        skf = StratifiedKFold(n_splits=n_splits)
        gen_skf = skf.split(data, data[treatment])
    cate_est = pd.DataFrame()
    for est_idx, train_idx in gen_skf:
        df_train = data.iloc[train_idx]
        df_est = data.iloc[est_idx]

        covariates = set(data.columns) - set([outcome, treatment])

        Xc = np.array(df_train.loc[df_train[treatment] == 0, covariates])
        Yc = np.array(df_train.loc[df_train[treatment] == 0, outcome])

        Xt = np.array(df_train.loc[df_train[treatment] == 1, covariates])
        Yt = np.array(df_train.loc[df_train[treatment] == 1, outcome])
        #
        if method == 'old':
            Xtest = df_train[covariates]
        elif method == 'new':
            Xtest = df_est[covariates]
        bart_res_c = dbarts.bart(Xc, Yc, Xtest, keeptrees=True, verbose=False)
        y_c_hat_bart = np.array(bart_res_c[7])
        bart_res_t = dbarts.bart(Xt, Yt, Xtest, keeptrees=True, verbose=False)
        y_t_hat_bart = np.array(bart_res_t[7])
        t_hat_bart = np.array(y_t_hat_bart - y_c_hat_bart)
        if method == 'old':
            cate_est_i = pd.DataFrame(t_hat_bart, index=df_train.index, columns=['CATE'])
        elif method == 'new':
            cate_est_i = pd.DataFrame(t_hat_bart, index=df_est.index, columns=['CATE'])
        cate_est = pd.concat([cate_est, cate_est_i], join='outer', axis=1)
    cate_est['avg.CATE'] = cate_est.mean(axis=1)
    cate_est['std.CATE'] = cate_est.std(axis=1)
    if result == 'full':
        return cate_est, bart_res_c, bart_res_t
    return cate_est