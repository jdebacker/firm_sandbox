'''
------------------------------------------------------------------------
Last updated: 7/13/2015

Calculates steady state of OLG model with S age cohorts, J types, mortality risk

This py-file calls the following other file(s):

This py-file creates the following other file(s):
    (make sure that an OUTPUT folder exists)
            OUTPUT/
------------------------------------------------------------------------
'''

# Packages
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import time
import scipy.optimize as opt
import pickle


'''
------------------------------------------------------------------------
Setting up the Model
------------------------------------------------------------------------
S            = number of periods an individual lives
J            = number of different ability groups
T            = number of time periods until steady state is reached
bin_weights  = percent of each age cohort in each ability group
starting_age = age of first members of cohort
ending age   = age of the last members of cohort
E            = number of cohorts before S=1
beta_annual  = discount factor for one year
beta         = discount factor for each age cohort
sigma        = coefficient of relative risk aversion
alpha        = capital share of income
nu_init      = contraction parameter in steady state iteration process
               representing the weight on the new distribution gamma_new
A            = total factor productivity parameter in firms' production
               function
delta_annual = depreciation rate of capital for one year
delta        = depreciation rate of capital for each cohort
ctilde       = minimum value amount of consumption
bqtilde      = minimum bequest value
ltilde       = measure of time each individual is endowed with each
               period
chi_n        = discount factor of labor
chi_b        = discount factor of incidental bequests
eta          = Frisch elasticity of labor supply
g_y_annual   = annual growth rate of technology
g_y          = growth rate of technology for one cohort
TPImaxiter   = Maximum number of iterations that TPI will undergo
TPImindist   = Cut-off distance between iterations for TPI
------------------------------------------------------------------------
'''


# Parameters
sigma = 1.9 # coeff of relative risk aversion for hh
beta = 0.98 # discount rate
delta = 0.1 # depreciation rate
alpha = 0.3 # capital's share of output
nu = 2.0 # elasticity of labor supply 
chi_n = 0.5 #utility weight, disutility of labor
chi_b = 0.2 #utility weight, warm glow bequest motive
ltilde = 1.0 # maximum hours
e = [0.5, 1.0, 1.2, 1.5] # effective labor units for the J types
S = 5 # periods in life of hh
J = 4 # number of lifetime income groups
surv_rate = np.array([0.99, 0.98, 0.6, 0.4, 0.0]) # probability of surviving to next period
#surv_rate = np.array([1.0, 1.0, 1.0, 1.0, 0.0]) # probability of surviving to next period
mort_rate = 1.0-surv_rate # probability of dying at the end of current period
surv_rate[-1] = 0.0
mort_rate[-1] = 1.0
surv_mat = np.tile(surv_rate.reshape(S,1),(1,J)) # matrix of survival rates
mort_mat = np.tile(mort_rate.reshape(S,1),(1,J)) # matrix of mortality rates
surv_rate1 = np.ones((S,1))# prob start at age S
surv_rate1[1:,0] = np.cumprod(surv_rate[:-1], dtype=float)
omega = np.ones((S,J))*surv_rate1# number of each age alive at any time
lambdas = np.array([0.5, 0.2, 0.2, 0.1])# fraction of each cohort of each type
weights = omega*lambdas/((omega*lambdas).sum()) # weights - dividing so weights sum to 1

# Functions and Definitions

print('checking omega')
omega2 = np.ones((S,1))# prob start at age S
omega2[1:,0] = np.cumprod(surv_rate[:-1], dtype=float)
print((omega[:,0].reshape(S,1)-omega2.reshape(S,1)).max())

def get_Y(K, L):
    '''
    Parameters: Aggregate capital, Aggregate labor

    Returns:    Aggregate output
    '''
    Y = (K ** alpha) * (L ** (1 - alpha))
    return Y


def get_w(Y, L):
    '''
    Parameters: Aggregate output, Aggregate labor

    Returns:    Returns to labor
    '''
    w = (1 - alpha) * Y / L
    return w


def get_r(Y, K):
    '''
    Parameters: Aggregate output, Aggregate capital

    Returns:    Returns to capital
    '''
    r = (alpha * (Y / K)) - delta
    return r


def get_L(n):
    '''
    Parameters: n 

    Returns:    Aggregate labor
    '''
    L = np.sum(weights*n*e)
    return L
    
def get_K(k):
    '''
    Parameters: k 

    Returns:    Aggregate capital
    '''
    K = np.sum(weights*k)
    return K


def MUc(c):
    '''
    Parameters: Consumption

    Returns:    Marginal Utility of Consumption
    '''
    output = c**(-sigma)
    return output


def MUl(n):
    '''
    Parameters: Labor

    Returns:    Marginal Utility of Labor
    '''
    output =  -chi_n * ((ltilde-n) ** (-nu))
    return output

def MUb(bq):
    '''
    Parameters: Intentional bequests

    Returns:    Marginal Utility of Bequest
    '''
    output = chi_b * (bq ** (-sigma))
    return output
    
def get_BQ(r, k):
    '''
    Parameters: Distribution of capital stock (SxJ)

    Returns:    Bequests by ability (Jx1)
    '''
    output = (1 + r) * (k*weights*mort_mat).sum(0)

    return output
    
    
    
def get_dist_bq(BQ):
    '''
    Parameters: Aggregate bequests by ability type

    Returns:    Bequests by age and ability
    '''
    #output = BQ.reshape(1, J)*(weights*(1.0/weights.sum(0)))
    #output = np.tile(BQ.reshape(1,J),(S,1))/np.tile((weights.sum(1)).reshape(S,1),(1,J))
    output = np.tile(BQ.reshape(1, J)/weights.sum(0),(S,1))

    return output
    
def get_cons(w, r, n, k0, k, bq):
    '''
    Parameters: Aggregate bequests by ability type

    Returns:    Bequests by age and ability
    '''
    output = ((1+r)*k0) + w*n*e - k + bq

    return output
    

def foc_k(r, c):
    '''
    Parameters:
        w        = wage rate (scalar)
        r        = rental rate (scalar)
        L_guess  = distribution of labor (SxJ array)
        K_guess  = distribution of capital at the end of period t (S x J array)
        bq       = distribution of bequests (S x J array)

    Returns:
        Value of foc error ((S-1)xJ array)
    '''
    #K_guess0 = np.zeros((S,J))
    #K_guess0[1:,:] = K_guess[:-1,:] # capital start period with
    #c = ((1+r)*K_guess0[:-1,:]) + w*L_guess[:-1,:]*e - K_guess[:-1,:] + bq[:-1,:]
    #cp1 = ((1+r)*K_guess[:-1,:]) + w*L_guess[1:,:]*e - K_guess[1:,:] + bq[1:,:]
    error = MUc(c[:-1,:]) - (1+r)*beta*surv_mat[:-1,:]*MUc(c[1:,:]) 
    return error


def foc_l(w, L_guess, c):
    '''
    Parameters:
        w        = wage rate (scalar)
        r        = rental rate (scalar)
        L_guess  = distribution of labor (SxJ array)
        K_guess  = distribution of capital at the end of period t (S x J array)
        bq       = distribution of bequests (S x J array)

    Returns:
        Value of foc error (SxJ array)
    '''
    
    error = w*MUc(c)*e + MUl(L_guess) 
    return error

def foc_bq(K_guess, c):
    '''
    Parameters:
        w        = wage rate (scalar)
        r        = rental rate (scalar)
        e        = distribution of abilities (SxJ array)
        L_guess  = distribution of labor (SxJ array)
        K_guess  = distribution of capital in period t (S-1 x J array)
        bq       = distribution of bequests (S x J array)

    Returns:
        Value of Euler error.
    '''
    error = MUc(c[-1,:]) -  MUb(K_guess[-1, :])
    return error

def Steady_State(guesses):
    '''
    Parameters: Steady state distribution of capital guess as array
                size SxJ and labor supply array of SxJ
rss
    Returns:    Array of SxJ * 2 Euler equation errors
    '''
    k = guesses[0: S * J].reshape((S, J))
    n = guesses[S * J:].reshape((S, J))
    K = get_K(k)
    L = get_L(n)
    Y = get_Y(K, L)    
    r = get_r(Y,K)
    w = get_w(Y,L)
    BQ = get_BQ(r, k)
    bq = get_dist_bq(BQ)
    k0 = np.zeros((S,J))
    k0[1:,:] = k[:-1,:] # capital start period with
    c = get_cons(w, r, n, k0, k, bq)
    error1 = foc_k(r, c) 
    error2 = foc_l(w, n, c) 
    error3 = foc_bq(k, c) 

    # Check and punish constraing violations
    mask1 = n < 0
    error2[mask1] += 1e9
    mask2 = n > ltilde
    error2[mask2] += 1e9
    if k.sum() <= 0:
        error1 += 1e9
    mask3 = c < 0
    error2[mask3] += 1e9
    # mask4 = np.diff(L_guess) > 0
    # error2[mask4] += 1e9
    #print np.array(list(error1.flatten()) + list(error2.flatten())).max()
    return list(error1.flatten()) + list(error2.flatten()) + list(error3.flatten()) 


# Make initial guesses for capital and labor
K_guess_init = np.ones((S, J)) * 0.05
L_guess_init = np.ones((S, J)) * 0.3
guesses = list(K_guess_init.flatten()) + list(L_guess_init.flatten())

solutions = opt.fsolve(Steady_State, guesses, xtol=1e-9, col_deriv=1)

Kssmat = solutions[0:S * J].reshape(S, J)
Lssmat = solutions[S * J:].reshape(S, J)
Lss = get_L(Lssmat)  
Kss = get_K(Kssmat) 
Yss = get_Y(Kss, Lss) 
rss = get_r(Yss,Kss)
wss = get_w(Yss,Lss)
BQss = get_BQ(rss, Kssmat)
bqss = get_dist_bq(BQss)
Kssmat0 = np.zeros((S,J))
Kssmat0[1:,:] = Kssmat[:-1,:] # capital start period with
Cssmat = get_cons(wss, rss, Lssmat, Kssmat0, Kssmat, bqss)
Css = np.sum(weights*Cssmat)

print 'SS r and w: ', rss, wss
print 'RESOURCE CONSTRAINT DIFFERENCE:', Yss - Css- delta*Kss

# check Euler errors
error1 = foc_k(rss, Cssmat) 
error2 = foc_l(wss, Lssmat, Cssmat) 
error3 = foc_bq(Kssmat, Cssmat) 

print("Euler errors")
print(error1)
print(error2)
print(error3)


