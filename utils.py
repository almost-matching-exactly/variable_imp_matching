import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor as RFR
from sklearn.linear_model import RidgeCV
from sklearn.neighbors import NearestNeighbors
import time


def get_match_groups(df_estimation, k, covariates, treatment, M, return_original_idx=True, check_est_df=True):
    if check_est_df:
        check_df_estimation(df_cols=df_estimation.columns, necessary_cols=covariates + [treatment])
    old_idx = np.array(df_estimation.index)
    df_estimation = df_estimation.reset_index(drop=True)
    X = df_estimation[covariates].to_numpy()
    T = df_estimation[treatment].to_numpy()
    X = M[M > 0] * X[:, M > 0]
    control_nn = NearestNeighbors(n_neighbors=k, leaf_size=50, algorithm='kd_tree', n_jobs=10).fit(X[T == 0])
    treatment_nn = NearestNeighbors(n_neighbors=k, leaf_size=50, algorithm='kd_tree', n_jobs=10).fit(X[T == 1])
    control_dist, control_mg = control_nn.kneighbors(X, return_distance=True)
    treatment_dist, treatment_mg = treatment_nn.kneighbors(X, return_distance=True)
    control_mg = pd.DataFrame(np.array(df_estimation.loc[df_estimation['T'] == 0].index)[control_mg])
    treatment_mg = pd.DataFrame(np.array(df_estimation.loc[df_estimation['T'] == 1].index)[treatment_mg])
    control_dist = pd.DataFrame(control_dist)
    treatment_dist = pd.DataFrame(treatment_dist)
    if return_original_idx:
        control_dist.index = old_idx
        treatment_dist.index = old_idx
        return convert_idx(control_mg, old_idx), convert_idx(treatment_mg, old_idx), control_dist, treatment_dist
    return control_mg, treatment_mg, control_dist, treatment_dist


def convert_idx(mg, idx):
    return pd.DataFrame(idx[mg.to_numpy()], index=idx)


def get_CATES(df_estimation, control_mg, treatment_mg, method, covariates, outcome, treatment, model_C, model_T, M,
              augmented=False, control_preds=None, treatment_preds=None, check_est_df=True):
    if check_est_df:
        check_df_estimation(df_cols=df_estimation.columns, necessary_cols=covariates + [outcome])
    df_estimation, old_idx = check_mg_indices(df_estimation, control_mg.shape[0], treatment_mg.shape[0])
    if method == 'mean':
        mg_cates = df_estimation[outcome].to_numpy()[treatment_mg.to_numpy()].mean(axis=1) - \
                df_estimation[outcome].to_numpy()[control_mg.to_numpy()].mean(axis=1)
    else:
        full_mg = control_mg.join(treatment_mg, lsuffix='_c', rsuffix='_t')
        if 'pruned' in method:
            imp_covs = list(np.array(covariates)[M > 0])
        else:
            imp_covs = covariates
        if augmented:
            if control_preds is None:
                control_preds = model_C.predict(df_estimation[covariates])
            if treatment_preds is None:
                treatment_preds = model_T.predict(df_estimation[covariates])
            model_cates = treatment_preds - control_preds
            full_mg = np.concatenate([df_estimation[imp_covs + [treatment]].to_numpy(),
                                      (df_estimation[treatment].to_numpy()*control_preds) +
                                      ((1 - df_estimation[treatment].to_numpy())*treatment_preds).reshape(-1, 1)],
                                     axis=1)[full_mg.reset_index().to_numpy()]
        else:
            full_mg = df_estimation[imp_covs + [treatment, outcome]].to_numpy()[full_mg.reset_index().to_numpy()]
        if 'linear' in method:
            model_type = 'linear'
        elif 'rf' in method:
            model_type = 'rf'
        else:
            raise Exception(f'CATE Method type {method} not supported. Supported methods are: mean, linear, and rf.')
        # if 'linear' in method:
        mg_cates = np.array([cate_model_pred(full_mg[i, :, :]) for i in range(full_mg.shape[0])])
        # else:
        #     mg_cates = np.array([cate_model_pred2(full_mg[i, :, :], model_type) for i in range(full_mg.shape[0])])
    if augmented:
        cates = model_cates + mg_cates
    else:
        cates = mg_cates
    return pd.Series(cates, index=old_idx, name=f'CATE_{method}')


def cate_model_pred2(a, model_type):
    if model_type == 'linear':
        return RidgeCV().fit(a[1:, :-1], a[1:, -1]).coef_[-1]
    elif model_type == 'rf':
        m = RFR().fit(a[1:, :-1], a[1:, -1])
        return m.predict(np.concatenate([a[0, :-2], [1]]).reshape(1, -1))[0] - \
               m.predict(np.concatenate([a[0, :-2], [0]]).reshape(1, -1))[0]


def cate_model_pred(a):
    mc = RidgeCV().fit(a[1:61, :-2], a[1:61, -1])
    mt = RidgeCV().fit(a[61:, :-2], a[61:, -1])
    # print('Ridge')
    # print(mc.score(a[1:61, :-2], a[1:61, -1]))
    # print(mt.score(a[61:, :-2], a[61:, -1]))
    # mc = RFR().fit(a[1:61, :-2], a[1:61, -1])
    # mt = RFR().fit(a[61:, :-2], a[61:, -1])
    # print('RFR')
    # print(mc.score(a[1:61, :-2], a[1:61, -1]))
    # print(mt.score(a[61:, :-2], a[61:, -1]))
    return mt.predict(a[0, :-2].reshape(1, -1))[0] - \
           mc.predict(a[0, :-2].reshape(1, -1))[0]


def check_df_estimation(df_cols, necessary_cols):
    missing_cols = [c for c in necessary_cols if c not in df_cols]
    if len(missing_cols) > 0:
        raise Exception(f'df_estimation missing necessary column(s) {missing_cols}')


def check_mg_indices(df_estimation, control_nrows, treatment_nrows):
    old_idx = df_estimation.index
    df_estimation = df_estimation.reset_index(drop=True)
    est_nrows = df_estimation.shape[0]
    if (est_nrows == control_nrows) and (est_nrows == treatment_nrows):
        return df_estimation, old_idx
    raise Exception(f'Control match group dataframe missing {len([c for c in df_idx if c not in control_idx])} and '
                    f'treatment match group dataframe missing {len([c for c in df_idx if c not in treatment_idx])} '
                    f'samples that are present in estimation dataframe.')
