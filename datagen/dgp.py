#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 17:00:40 2020

@author: harshparikh
"""

import itertools
import numpy as np
import pandas as pd
import scipy
from sklearn import preprocessing


def construct_sec_order(arr):
    # an intermediate data generation function used for generating second order information
    second_order_feature = []
    num_cov_sec = len(arr[0])
    for a in arr:
        tmp = []
        for i in range(num_cov_sec):
            for j in range(i+1, num_cov_sec):
                tmp.append( a[i] * a[j] )
        second_order_feature.append(tmp)
    return np.array(second_order_feature)


def data_generation_dense_mixed_endo(num_samples, num_cont_imp, num_disc_imp, num_cont_unimp, num_disc_unimp, std=1.5,
                                     t_imp=2, overlap=1, weights=None):
    def u(x):
        T = []
        second_T_term = t_imp * 1 if num_cont_imp >= 2 else t_imp * 0.5
        for row in x:
            l = scipy.special.expit(np.sum(row[:t_imp]) - second_T_term + np.random.normal(0, overlap))
            t = int(l > 0.5)
            T.append(t)
        return np.array(T)
    # the data generating function that we will use. include second order information
    xc = np.random.normal(1, std, size=(num_samples, num_cont_imp))
    xd = np.random.binomial(1, 0.5, size=(num_samples, num_disc_imp))
    x = np.hstack((xc, xd))

    errors_y0 = np.random.normal(0, 1, size=num_samples)
    errors_y1 = np.random.normal(0, 1, size=num_samples)

    num_cov_dense = num_cont_imp + num_disc_imp
    dense_bs_sign = np.random.choice([-1, 1], num_cov_dense)
    dense_bs = [np.random.normal(dense_bs_sign[i]*10, 9) for i in range(num_cov_dense)]

    if weights is not None:
        for idx, w in weights:
            dense_bs[idx] = w['control']
    y0_true = np.dot(x, np.array(dense_bs))

    treatment_eff_coef = np.random.normal(1.0, 0.25, size=num_cov_dense)
    if weights is not None:
        for idx, w in weights:
            dense_bs[idx] = 0
            treatment_eff_coef[idx] = w['treated']
    treatment_effect = np.dot(x, treatment_eff_coef)
    second = construct_sec_order(x)
    treatment_eff_sec = np.sum(second, axis=1)
    y1_true = np.dot(x, np.array(dense_bs)) + treatment_effect + treatment_eff_sec

    te = y1_true - y0_true
    y0 = y0_true + errors_y0
    y1 = y1_true + errors_y1
    T = u(x)
    y = T*y1 + (1-T)*y0
    xc2 = np.random.normal(1, std, size=(num_samples, num_cont_unimp))
    xd2 = np.random.binomial(1, 0.5, size=(num_samples, num_disc_unimp))
    x2 = np.hstack((xc2, xd2))
    num_covs_unimportant = num_cont_unimp + num_disc_unimp
    df = pd.DataFrame(np.hstack([x, x2]), columns = list( ['X%d'%(j) for j in range(num_cov_dense + num_covs_unimportant)] ))
    df['Y'] = y
    df['T'] = T
    binary = ['X%d'%(j) for j in range(num_cont_imp,num_cov_dense)] + ['X%d'%(j) for j in range(num_cov_dense + num_cont_unimp, num_cov_dense + num_covs_unimportant)]
    df_true = pd.DataFrame()
    df_true['Y1'] = y1
    df_true['Y0'] = y0
    df_true['TE'] = te
    df_true['Y0_true'] = y0_true
    df_true['Y1_true'] = y1_true
    return df, df_true, binary


def dgp_friedman(n):
    X = np.random.uniform(0, 1, (n, 10))
    y0_errors, y1_errors, t_errors = np.random.normal(0, 1, (n,)), np.random.normal(0, 1, (n,)), np.random.normal(0, 1, (n,))
    y0 = (10 * np.sin(np.pi * X[:, 0] * X[:, 1])) + (20 * ((X[:, 2] - 0.5) ** 2)) + (10 * X[:, 3]) + (
                5 * X[:, 4])
    y1 = (10 * np.sin(np.pi * X[:, 0] * X[:, 1])) + (20 * ((X[:, 2] - 0.5) ** 2)) + (10 * X[:, 3]) + (5 * X[:, 4]) + (
                X[:, 2] * np.cos(np.pi * X[:, 0] * X[:, 1]))
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    t = (scipy.special.expit(X[:, 0] + X[:, 1] - 0.5 + t_errors) > 0.5).astype(int)
    y = t * y1 + (1 - t) * y0

    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), (y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_sine(n_samples, n_imp, n_unimp):
    x_imp = np.random.normal(0, 1, size=(n_samples, n_imp))
    dense_bs = np.random.choice([-1, 1], size=(n_imp,)) * np.random.normal(10, 9, size=(n_imp,))
    dense_bs = preprocessing.normalize(dense_bs.reshape(1, -1), norm='l2').reshape(-1, )
    u = np.matmul(x_imp, dense_bs)
    y0 = np.sin(u) + np.sin(2*u) + np.sin(3*u) + np.sin(4*u) + 1
    y1 = np.sin(u) + np.sin(2*u) + np.sin(3*u) + np.sin(4*u) + np.sin(5*u) + 1
    y0_errors = np.random.normal(0, 0.04, size=n_samples)
    y1_errors = np.random.normal(0, 0.04, size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    t_errors = np.random.normal(0, 1, (n_samples,))
    t = (scipy.special.expit(x_imp[:, 0] + x_imp[:, 1] + t_errors) > 0.5).astype(int)
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.normal(0, 1, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), \
           (y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_polynomials(n_samples, n_imp, n_unimp):
    x_imp = np.random.normal(0, 1, size=(n_samples, n_imp))
    dense_bs = np.random.choice([-1, 1], size=(n_imp,)) * np.random.normal(10, 9, size=(n_imp,))
    dense_bs = preprocessing.normalize(dense_bs.reshape(1, -1), norm='l2').reshape(-1,)
    u = np.matmul(x_imp, dense_bs)
    y0 = u**3 + u**4 + 1
    y1 = u**3 + u**4 + u**5 + 1
    y0_errors = np.random.normal(0, 0.04, size=n_samples)
    y1_errors = np.random.normal(0, 0.04, size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    t_errors = np.random.normal(0, 1, (n_samples,))
    t = (scipy.special.expit(x_imp[:, 0] + x_imp[:, 1] + t_errors) > 0.5).astype(int)
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.normal(0, 1, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), \
           (y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_non_linear_mixed(n_samples, n_imp, n_unimp):
    x_imp = np.random.normal(0, 1, size=(n_samples, n_imp))
    dense_bs = np.random.choice([-1, 1], size=(n_imp,)) * np.random.normal(10, 9, size=(n_imp,))
    dense_bs = preprocessing.normalize(dense_bs.reshape(1, -1), norm='l2').reshape(-1, )
    u = np.matmul(x_imp, dense_bs)
    y0 = np.cos(u) + (1/(1+np.exp(-u))) - 2
    y1 = np.cos(u) + (1/(1+np.exp(-u))) - (u**3) - 2
    y0_errors = np.random.normal(0, 0.04, size=n_samples)
    y1_errors = np.random.normal(0, 0.04, size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    t_errors = np.random.normal(0, 1, (n_samples,))
    t = (scipy.special.expit(x_imp[:, 0] + x_imp[:, 1] + t_errors) > 0.5).astype(int)
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.normal(0, 1, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), (
                y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_test(n_samples, n_imp, n_unimp):
    x_imp = np.random.normal(0, 1, size=(n_samples, n_imp))
    dense_bs = np.random.choice([-1, 1], size=(n_imp,)) * np.random.normal(10, 9, size=(n_imp,))
    dense_bs = preprocessing.normalize(dense_bs.reshape(1, -1), norm='l2').reshape(-1, )
    u = np.matmul(x_imp, dense_bs)
    y0 = (u+1)**2 - 2*u
    y1 = (u+1)**2 - 2*u + np.exp(u) + 1
    y0_errors = np.random.normal(0, 0.04, size=n_samples)
    y1_errors = np.random.normal(0, 0.04, size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    t_errors = np.random.normal(0, 1, (n_samples,))
    t = (scipy.special.expit(x_imp[:, 0] + x_imp[:, 1] + t_errors) > 0.5).astype(int)
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.normal(0, 1, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), (
                y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_poly_no_interaction(n_samples, n_imp, n_unimp):
    # x_imp = np.linspace(-1, 1, n_samples).reshape(-1, 1)
    x_imp = np.random.uniform(-2, 2, size=(n_samples, n_imp))
    t_imp = np.random.binomial(1, 0.5, size=(n_imp,))
    t = np.random.binomial(1, 0.5, size=(n_samples,))

    eff_sign = np.random.choice([-1, 1], n_imp)
    eff_powers = np.random.randint(2, 3, size=(n_imp,))
    t_eff_sign = np.random.choice([-1, 1], n_imp)
    t_eff_powers = np.random.randint(2, 3, size=(n_imp,))
    y0 = np.sum(eff_sign*(x_imp ** eff_powers), axis=1)
    y1 = np.sum(eff_sign*(x_imp ** eff_powers), axis=1) + np.sum(t_eff_sign*((x_imp * t_imp) ** t_eff_powers), axis=1)
    y0_errors = np.random.normal(0, 0.03 * np.std(y0), size=n_samples)
    y1_errors = np.random.normal(0, 0.03 * np.std(y1), size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.uniform(-2, 2, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), (y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)


def dgp_poly_interaction(n_samples, n_imp, n_unimp):
    x_imp = np.random.uniform(0, 5, size=(n_samples, n_imp))
    t_imp = [1] * n_imp
    int_y = []
    int_te = []
    for c in itertools.combinations(range(n_imp), 2):
        r = np.random.binomial(1, 0.5, size=(2,))
        eff = np.random.choice([-1, 1]) * (x_imp[:, c[0]] * x_imp[:, c[1]])
        int_y.append((r[0] * eff).reshape(-1, 1))
        int_te.append((r[1] * eff).reshape(-1, 1))
    int_y = np.sum(np.concatenate(int_y, axis=1), axis=1)
    int_te = np.sum(np.concatenate(int_te, axis=1), axis=1)
    t = np.random.binomial(1, 0.5, size=(n_samples,))

    eff_sign = np.random.choice([-1, 1], n_imp)
    eff_powers = [3] * n_imp
    t_eff_sign = [1, -1, 1, 0, 0, 0, 0, 0]
    t_eff_powers = [3] * n_imp
    y0 = np.sum(eff_sign*(x_imp ** eff_powers), axis=1) + int_y
    y1 = np.sum(eff_sign*(x_imp ** eff_powers), axis=1) + int_y + np.sum(t_eff_sign*((x_imp * t_imp) ** t_eff_powers), axis=1) + int_te
    y0_errors = np.random.normal(0, 1, size=n_samples)
    y1_errors = np.random.normal(0, 1, size=n_samples)
    te = y1 - y0
    y0 = y0 + y0_errors
    y1 = y1 + y1_errors
    y = (y0 * (1 - t)) + (y1 * t)
    x_unimp = np.random.uniform(0, 5, size=(n_samples, n_unimp))
    X = np.concatenate([x_imp, x_unimp], axis=1)
    return X, y.reshape(-1, 1), t.reshape(-1, 1), y0.reshape(-1, 1), y1.reshape(-1, 1), te.reshape(-1, 1), (y0 - y0_errors).reshape(-1, 1), (y1 - y1_errors).reshape(-1, 1)

