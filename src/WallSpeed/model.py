import numpy as np
import math
import warnings
import DRwizard
import FiniteT


class Model:
    '''
    Class that generates the model given external model file
    '''
    def __init__(self,mu3D,mu4D):
        '''
        Initialise class
        '''
        self.num_boson_dof = 29
        self.num_fermion_dof = 90

        '''
        3D and 4D RG scale of EFT as fraction of temperature
        '''
        self.mu3D = mu3D
        self.mu4D = mu4D
        '''
        Z,W,t mass, strong gauge coupling and fermion generations
        '''
        self.MW = 80.379
        self.MZ = 91.1876
        self.Mt = 172.76
        #self.couplings = {}

    def Run4Dparams(self,T):
        '''
        Runs 4D couplings at matching scale mu4D
        Takes list of all parameters and beta functions from DRwizard and runs them
        '''
        pars, beta = np.loadtxt('BetaFunctions4D.dat',delimiter=',',unpack=True,dtype=str)
        #data, pars= np.array_split(np.loadtxt('BetaFunctions4D.dat', dtype=str), [-1], axis=1)
        print(pars)
        print(beta)
        #print(pars.flatten().tolist())
        muBar = self.mu4D
        #ListofAllparams = BetaFunctions(self.ListofAllparams ).solveBetaFuncs(muBar)[1]
        return


    def J3(self,m):
        '''
        Log integral for 1loop 3d Veff
        '''
        return -m**3/(12*np.pi)



    def Vtree(self,X,show_V=True):
#        X = np.asanyarray(X)
#        phi1,s1 = X[...,0],X[...,1]
        with open('Veff3dLO.dat','r') as file:
            vtree = file.read()
        #vtree = vtree.replace("lambdaH","lambdaH.self")
        #vtree = eval(vtree)

#        vtree = (
#            +self.muh2*h**2/2
#            +self.mus2*s**2/2
#            +self.lambdaH*h**4/4
#            +self.lambdaS*s**4/4
#            +self.lambdaHS*(h*s)**2/4
#            +self.CTs[0]
#            +self.CTs[1]*h**2
#            +self.CTs[2]*s**2
#            +self.CTs[3]*h**4)
        if show_V:
            print(vtree)
        return vtree


    def Veff4d(self):
        '''
        Thermal effective potential at 1 loop in 4d
        '''

    def Veff3d(self):
        '''
        Thermal effective potential at 1 loop at the supersoft scale
        '''

    def dVdT(self,X,T,include_radiation=True):
        '''
        1st T-derivative of the effective potential
        '''

    def d2VdT2(self,X,T,include_radiation=True):
        '''
        2nd T-derivative of the effective potential
        '''

    def d3VdT3(self,X,T,include_radiation=True):
        '''
        3rd T-derivative of the effective potential
        '''

    def Vefftot(self):
        '''
        Function that generates the effective potential given a pre-defined model
        '''


#def main():
pot = Model(1,1)
#pot.Run4Dparams(1)
pot.Vtree(1)

print("hello")

# if __name__ == '__main__':
#     main()
