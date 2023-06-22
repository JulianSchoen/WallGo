import numpy as np
from scipy.optimize import fsolve
from scipy.optimize import root_scalar
from scipy.optimize import root
from scipy.integrate import odeint
from TestModel import *


def findJouguetVelocity(model,Tnucl):
    r"""
    Finds the Jouguet velocity for a thermal effective potential, defined by Model,
    using that the derivative of :math:`v_+` with respect to :math:`T_-` is zero at the Jouguet velocity
    """
    pSym = model.pSym(Tnucl)
    eSym = model.eSym(Tnucl)
    def vpDerivNum(tm): #the numerator of the derivative of v+^2
        pBrok = model.pBrok(tm)
        eBrok = model.eBrok(tm)
        num1 = pSym - pBrok #first factor in the numerator of v+^2
        num2 = pSym + eBrok
        den1 = eSym - eBrok #first factor in the denominator of v+^2
        den2 = eSym + pBrok 
        dnum1 = - model.dpBrok(tm) #T-derivative of first factor wrt tm
        dnum2 = model.deBrok(tm)
        dden1 = - dnum2 #T-derivative of second factor wrt tm
        dden2 = - dnum1
        return(dnum1*num2*den1*den2 + num1*dnum2*den1*den2 - num1*num2*dden1*den2 - num1*num2*den1*dden2)
    
    # For detonations, Tm has a lower bound of Tn, but no upper bound.
    # We increase Tmax until we find a value that brackets our root.
    Tmin,Tmax = Tnucl,1.5*Tnucl
    bracket1,bracket2 = vpDerivNum(Tmin),vpDerivNum(Tmax)
    while bracket1*bracket2 > 0 and Tmax < 10*Tnucl:
        Tmin = Tmax
        bracket1 = bracket2
        Tmax *= 1.5
        bracket2 = vpDerivNum(Tmax)
    
    tmSol = None
    if bracket1*bracket2 <= 0: #If Tmin and Tmax bracket our root, use the 'brentq' method.
        tmSol = root_scalar(vpDerivNum,bracket =[Tmin, Tmax], method='brentq').root 
    else: #If we cannot bracket the root, use the 'secant' method instead.
        tmSol = root_scalar(vpDerivNum, method='secant', x0=Tnucl, x1=1.5*Tmax).root 
    vp = np.sqrt((model.pSym(Tnucl) - model.pBrok(tmSol))*(model.pSym(Tnucl) + model.eBrok(tmSol))/(model.eSym(Tnucl) - model.eBrok(tmSol))/(model.eSym(Tnucl) + model.pBrok(tmSol)))
    return(vp)


def vpovm(model, Tp, Tm):
    r"""
    Returns the ratio :math:`v_+/v_-` as a function of :math:`T_+, T_-`
    """
    return (model.eBrok(Tm) + model.pSym(Tp))/(model.eSym(Tp)+model.pBrok(Tm))

def vpvm(model, Tp, Tm):
    r"""
    Returns the product :math:`v_+v_-` as a function of :math:`T_+, T_-`
    """
    return (model.pSym(Tp)-model.pBrok(Tm))/(model.eSym(Tp)-model.eBrok(Tm))


def matchDeton(model,vw,Tnucl):
    r"""
    Returns :math:`v_+, v_-, T_+, T_-` for a detonation as a function of the wall velocity and `T_n`.
    """
    vp = vw
    Tp = Tnucl
    pSym,wSym = model.pSym(Tp),model.wSym(Tp)
    eSym = wSym - pSym
    def tmFromvpsq(tm): #determine Tm in the detonation branch from the expression for r = w_+/w_-
        pBrok,wBrok = model.pBrok(tm),model.wBrok(tm)
        eBrok = wBrok - pBrok
        
        alpha = (eSym-eBrok-3*(pSym-pBrok))/(3*wSym)
        X = 1-3*alpha+3*vp**2*(1+alpha)
        lhs = wSym/wBrok
        rhs = (1-vp**2)*(X+2*np.sqrt(X**2-12*vp**2))/(16*vp**2-X**2)
        return lhs - rhs
    
    # For detonations, Tm has a lower bound of Tn, but no upper bound.
    # We increase Tmax until we find a value that brackets our root.
    Tmin,Tmax = Tnucl,1.5*Tnucl
    bracket1,bracket2 = tmFromvpsq(Tmin),tmFromvpsq(Tmax)
    while bracket1*bracket2 > 0 and Tmax < 10*Tnucl:
        Tmin = Tmax
        bracket1 = bracket2
        Tmax *= 1.5
        bracket2 = tmFromvpsq(Tmax)
    
    Tm = None
    if bracket1*bracket2 <= 0: #If Tmin and Tmax bracket our root, use the 'brentq' method.
        Tm = root_scalar(tmFromvpsq,bracket =[Tmin, Tmax], method='brentq').root 
        
    else: #If we cannot bracket the root, use the 'secant' method instead.
        Tm = root_scalar(tmFromvpsq, method='secant', x0=Tnucl, x1=1.5*Tmax).root     
    vm = np.sqrt(vpvm(model,Tp,Tm)/vpovm(model,Tp,Tm))
    return (vp, vm, Tp, Tm)

def matchDeflagOrHyb(model,vw,vp,Tnucl):
    r"""
    Returns :math:`v_+, v_-, T_+, T_-` for a deflagrtion or hybrid when the wall velocity and :math:`v_+` are given
    """
    def match(XpXm):
        Tpm = __inverseMappingT(XpXm, Tnucl)
        _vpvm = vpvm(model,Tpm[0],Tpm[1])
        _vpovm = vpovm(model,Tpm[0],Tpm[1])
        eq1 = _vpvm*_vpovm-vp**2
        eq2 = _vpvm/_vpovm-min(vw**2,model.csqBrok(Tpm[1]))
        
        # We multiply the equations by c to make sure the solver
        # do not explore arbitrarly small or large values of Tm and Tp.
        c = ((2*Tnucl)**2+Tpm[0]**2+Tpm[1]**2)*((2/Tnucl)**2+1/Tpm[0]**2+1/Tpm[1]**2)
        return (eq1*c,eq2*c)

    # We map Tm and Tp, which satisfy 0<Tm<Tp, to the interval (-inf,inf) which is used by the solver.
    sol = root(match,__mappingT([1.1*Tnucl,0.9*Tnucl], Tnucl),method='hybr')
    [Tp,Tm] = __inverseMappingT(sol.x,Tnucl)
    if vw < np.sqrt(model.csqBrok(Tm)):
        vm = vw
    else:
        vm = np.sqrt(model.csqBrok(Tm))
    return vp, vm, Tp, Tm

def gammasq(v):
    r"""
    Lorentz factor :math:`\gamma^2` corresponding to velocity :math:`v`
    """
    return 1./(1. - v*v)

def mu(xi,v):
    """
    Lorentz-transformed velocity
    """
    return (xi - v)/(1. - xi*v)

def shockDE(xiAndT,v,model):
    r"""
    Hydrodynamic equations for the self-similar coordinate :math:`\xi` and the fluid temperature :math:`T` in terms of the fluid velocity :math:`v`
    """
    xi, T = xiAndT
    dxiAndTdv = [gammasq(v) * (1. - v*xi)*(mu(xi,v)*mu(xi,v)/model.csqSym(T)-1.)*xi/2./v,model.wSym(T)/model.dpSym(T)*gammasq(v)*mu(xi,v)]
    return dxiAndTdv
    
def solveHydroShock(model,vw,vp,Tp):
    r"""
    Solves the hydrodynamic equations in the shock for a given wall velocity and `v_+, T_+` and determines the position of the shock. Returns the nucleation temperature.
    """
    xi0T0 = [vw,Tp]
    vpcent = mu(vw,vp)
    maxindex = 1024
    vs = np.linspace(vpcent,0,maxindex)
    solshock = odeint(shockDE,xi0T0,vs,args=(model,)) #solve differential equation all the way from v = v+ to v = 0
    xisol = solshock[:,0]
    Tsol = solshock[:,1]
    #now need to determine the position of the shock, which is set by mu(xi,v)^2 xi = cs^2
    index = 0
    while mu(xisol[index],vs[index])*xisol[index] < model.csqSym(Tsol[index]) and index<maxindex-1:
        index +=1
    def TiiShock(tn): #continuity of Tii
        return model.wSym(tn)*xisol[index]/(1-xisol[index]**2) - model.wSym(Tsol[index])*mu(xisol[index],vs[index])*gammasq(mu(xisol[index],vs[index]))
    Tn = fsolve(TiiShock,Tp*0.9)[0]
    return Tn

def strongestShock(model, vw):
    r"""
    Returns the minimum temperature for which a shock can exist.
    For the strongest shock, :math:`v_+=0`, which yields `T_+,T_-`.
    The fluid equations in the shock are then solved to determine the strongest shock.
    """
    def vpnum(Tpm):
        return (model.eBrok(Tpm[1])+model.pSym(Tpm[0]),model.pSym(Tpm[0])-model.pBrok(Tpm[1]))

    Tp,Tm = np.abs(fsolve(vpnum,[0.2,0.2]))
    return solveHydroShock(model,vw,0,Tp)

def findMatching(model,vwTry,Tnucl):
    r"""
    Returns :math:`v_+, v_-, T_+, T_-` as a function of the wall velocity and the nucleation temperature. For detonations, these follow directly from the function
    matchDeton, for deflagrations and hybrids, the code varies `v_+' until the temperature in front of the shock equals the nucleation temperature
    """
    vJouguet = findJouguetVelocity(model,Tnucl)
    if vwTry > vJouguet: #Detonation
        vp,vm,Tp,Tm = matchDeton(model,vwTry,Tnucl)
            
    else: #Hybrid or deflagration
        #loop over v+ until the temperature in front of the shock matches the nucleation temperature
        vpmax = min(vwTry,np.sqrt(model.csqSym(model.Tc())))
        vpmin = 0.01 #minimum value of vpmin
        vptry = (vpmax + vpmin)/2.
        TnTry = 0
        error = 10**-3 #adjust error here
        count = 0
        _,_,Tp1,_ = matchDeflagOrHyb(model,vwTry,vpmin,Tnucl)
        _,_,Tp2,_ = matchDeflagOrHyb(model,vwTry,vpmax,Tnucl)
        print(Tnucl,Tp1,Tp2,solveHydroShock(model,vwTry,vpmin,Tp1)-Tnucl,solveHydroShock(model,vwTry,vpmax,Tp2)-Tnucl)
        while np.abs(TnTry - Tnucl)/Tnucl > error and count <100: #get rid of this hard-coded thing
            vp,vm,Tp,Tm = matchDeflagOrHyb(model,vwTry,vptry,Tnucl)
            Tntry = solveHydroShock(model,vwTry,vptry,Tp)

            if Tntry > Tnucl:
                vpmax = vptry
                vptry = (vpmax + vpmin)/2.
            else:
                vpmin = vptry
                vptry = (vpmax + vpmin)/2.
            count += 1
                    
    return (vp,vm,Tp,Tm)

def findHydroBoundaries(model, vwTry, Tnucl):
    r"""
    Returns :math:`c_1, c_2, T_+, T_-` for a given wall velocity and nucleation temperature
    """
    vp,vm,Tp,Tm = findMatching(model, vwTry, Tnucl)
    c1 = model.wSym(Tp)*gammasq(vp)*vp
    c2 = model.pSym(Tp)+model.wSym(Tp)*gammasq(vp)*vp**2
    return (c1, c2, Tp, Tm)

def findvwLTE(model, Tnucl):
    r"""
    Returns the wall velocity in local thermal equilibrium for a given nucleation temperature.
    The wall velocity is determined by solving the matching condition :math:`T_+ \gamma_+= T_-\gamma_-` via a binary search. 
    For small wall velocity :math:`T_+ \gamma_+> T_-\gamma_-`, and -- if a solution exists -- :math:`T_+ \gamma_+< T_-\gamma_-` for large wall velocity.
    If no solution can be found (because the phase transition is too strong or too weak), the search algorithm asymptotes towards the
    Jouguet velocity and the function returns zero.
    The solution is always a deflagration or hybrid.
    """
    vmin = 0.01
    vj = findJouguetVelocity(model,Tnucl)
    vmax = vj
    counter = 0
    errmatch = 1.
    errjouguet = 1. 
    while counter<30 and min(errmatch,errjouguet)>10**-5: #probably also get rid of this hard-coded thing
        vmid = (vmin+vmax)/2.
        vp,vm,Tp,Tm = findMatching(model,vmid, Tnucl)
        if Tp*np.sqrt(gammasq(vp)) > Tm*np.sqrt(gammasq(vm)):
            vmin = vmid
        else:
            vmax = vmid
        errmatch = np.abs((Tp*np.sqrt(gammasq(vp)) - Tm*np.sqrt(gammasq(vm))))/(Tp*np.sqrt(gammasq(vp))) #Checks error in matching condition
        errjouguet = np.abs(vmid-vj)/vmid #Checks distance to Jouguet velocity
        counter+=1

    if errmatch < 10**-4:
        return vmid
    else:
        return 0
    
def __mappingT(TpTm,Tscale):
    """
    Maps the variables Tp and Tm, which are constrained by 0<Tm<Tp for deflagration/hybrid walls. 
    They are mapped to the interval (-inf,inf) to allow root finding algorithms to explore different values of (Tp,Tm),
    without going outside of the bound above.

    Parameters
    ----------
    TpTm : array_like, shape (2,)
        List containing Tp and Tm.
    Tscale : double
        Typical temperature scale. Should be of order Tnucl.
    """
    
    Tp,Tm = TpTm
    Xm = 0.5*(2*Tm-Tp)/np.sqrt(Tm*(Tp-Tm))
    Xp = Tp/Tscale-1 if Tp > Tscale else 1-Tscale/Tp
    return [Xp,Xm]

def __inverseMappingT(XpXm,Tscale):
    """
    Inverse of __mappingT.
    """
    
    Xp,Xm = XpXm
    Tp = Tscale*(1+Xp) if Xp > 0 else Tscale/(1-Xp)
    Tm = 0.5*Tp*(1+Xm/np.sqrt(1+Xm**2))
    return [Tp,Tm]















