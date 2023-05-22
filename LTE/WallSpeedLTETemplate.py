import numpy as np
from scipy.integrate import odeint
from scipy.integrate import simps
import matplotlib.pyplot as plt 

def mu(a,b):
  return (a-b)/(1.-a*b)

# If the wall velocity is smaller than the sos, solution is deflagration, so vm = vw
# Compare eq. 19 of bag eos paper: disc is the argument of the sqrt appearing in the expression
# for vm in terms of vp
# If the solution would be a detonation, vp=vw. Whenever the sqrt becomes imaginary for vp=vw
# is the transition to hybrid.
def getvm(al,vw,cs2b):
  if vw**2<cs2b:
    return (vw,0)
  cc = 1.-3.*al+vw**2*(1./cs2b+3.*al)
  disc = -4.*vw**2/cs2b+cc**2
  if (disc<0.)|(cc<0.):
    return (np.sqrt(cs2b), 1)
  return ((cc+np.sqrt(disc))/2.*cs2b/vw, 2)

def jouguet(al,cs2b):
  n = 8*1024  # change accuracy here
  vs = np.linspace(np.sqrt(cs2b), 0.99, n)
  cc = 1.-3.*al+vs**2*(1./cs2b+3.*al)
  disc = -4.*vs**2/cs2b+cc**2
  return vs[int(sum(np.heaviside(-disc,0.0)))]

#This is al+
def getal(vp,vm,cs2b):
  return (vp/vm-1.)*(vp*vm/cs2b - 1.)/(1-vp**2)/3.

#similar reasoning as above for vm
def getvp(al,vm,cs2b):
  cc = 0.5*(vm/cs2b + 1./vm)
  disc = (1./cs2b+3.*al)*(3.*al-1.)+cc**2
  if (disc<0.):
    print("neg disc in vp: ",al,vm,cs2b,cc)
    return 0.
  return (cc-np.sqrt(disc))/(1./cs2b+3.*al)

#Differential equations for v, xi and w.
def dfdv(xiw, v, cs2):
  xi, w = xiw
  dxidv = (mu(xi,v)**2/cs2-1.)
  dxidv *= (1.-v*xi)*xi/2./v/(1.-v**2) 
  dwdv = (1.+1./cs2)*mu(xi,v)*w/(1.-v**2)
  return [dxidv,dwdv]

def getwow(a,b):
  return a/(1.-a**2)/b*(1.-b**2)

def getKandWow(vw,v0,cs2):
   
  
  if v0==0:
    return 0,1

  n = 8*1024  # change accuracy here
  vs = np.linspace(v0, 0, n)
#solution of differential equation for xi and wow in terms of v
#initial conditions corresponds to v=v0, xi = vw and w = 1 (which is random)
  sol = odeint(dfdv, [vw,1.], vs, args=(cs2,))
  xis, wows = (sol[:,0],sol[:,1])

  ll=-1
  if mu(vw,v0)*vw<=cs2:
    #find position of the shock
    ll=max(int(sum(np.heaviside(cs2-(mu(xis,vs)*xis),0.0))),1)
    vs = vs[:ll]
    xis = xis[:ll]
    wows = wows[:ll]/wows[ll-1]*getwow(xis[-1], mu(xis[-1],vs[-1]))

  Kint = simps(wows*(xis*vs)**2/(1.-vs**2), xis)

  return (Kint*4./vw**3, wows[0])

def alN(al,wow,cs2b,cs2s):
  da = (1./cs2b - 1./cs2s)/(1./cs2s + 1.)/3.
  return (al+da)*wow -da

def getalNwow(vp,vm,vw,cs2b,cs2s):
  Ksh,wow = getKandWow(vw,mu(vw,vp),cs2s) 
  #print (Ksh,wow)
  return (alN(getal(vp,vm,cs2b),wow,cs2b,cs2s), wow) 

def kappaNuMuModel(cs2b,cs2s,al,vw):
  #print (cs2b,cs2s,al,vw)
  vm, mode = getvm(al,vw,cs2b)
  #print (vm**2, mode)
  if mode<2:
    almax,wow = getalNwow(0,vm,vw,cs2b,cs2s)
    if almax<al:
      print ("alpha too large for shock")
      return 0;

    vp = min(cs2s/vw,vw) #check here
    almin,wow = getalNwow(vp,vm,vw,cs2b,cs2s)
    if almin>al: #minimum??
      print ("alpha too small for shock")
      return 0;

    iv = [[vp,almin],[0,almax]]
    while (abs(iv[1][0]-iv[0][0])>1e-7):
      vpm = (iv[1][0]+iv[0][0])/2.
      alm = getalNwow(vpm,vm,vw,cs2b,cs2s)[0]
      if alm>al:
        iv = [iv[0],[vpm,alm]]
      else:
        iv = [[vpm,alm],iv[1]]
      #print iv
    vp = (iv[1][0]+iv[0][0])/2.
    Ksh,wow = getKandWow(vw,mu(vw,vp),cs2s)
  
  else:
    vp = vw 
    Ksh,wow = (0,1)
  
  if mode>0:
    Krf,wow3 = getKandWow(vw,mu(vw,vm),cs2b)
    Krf*= -wow*getwow(vp,vm)
  else:
    Krf = 0

  return (Ksh + Krf)/al

def matchingrelofvw(cs2b,cs2s,al,rn):
  nvw = 99
  vwmin = 0.01
  vwmax = 0.99
  matchlist = np.empty((nvw,2))
  alphalist = np.empty((nvw,2))
  dalphalist = np.empty((nvw,2))
  for i in range(nvw):
    vw = vwmin + i*0.01
    vm, mode = getvm(al,vw,cs2b)
      
    if mode<2:
      almax,wow = getalNwow(0,vm,vw,cs2b,cs2s)
      if almax<al:
        print ("alpha too large for shock")
        return 0;

      vp = min(cs2s/vw,vw) #check here
      almin,wow = getalNwow(vp,vm,vw,cs2b,cs2s)
      if almin>al: #minimum??
        print ("alpha too small for shock")
        return 0;

      iv = [[vp,almin],[0,almax]]
      while (abs(iv[1][0]-iv[0][0])>1e-7):
        vpm = (iv[1][0]+iv[0][0])/2.
        alm = getalNwow(vpm,vm,vw,cs2b,cs2s)[0]
        if alm>al:
          iv = [iv[0],[vpm,alm]]
        else:
          iv = [[vpm,alm],iv[1]]
      #print iv
      vp = (iv[1][0]+iv[0][0])/2.

    else:
      vp = vw

    matchlist[i,0]=vw
    alphalist[i,0]=vw
    alplus = getal(vp,vm,cs2b)
    alphalist[i,1]=alplus
    rp=rn*((3*al*(1+1/cs2s)+1/cs2b-1/cs2s)/((3*alplus*(1+1/cs2s)+1/cs2b-1/cs2s)))**((-1/cs2s+1/cs2b)/(1/cs2s+1))
#    print(vw,rp)
    matchlist[i,1] = (rp*(np.sqrt(1-vm*vm)/np.sqrt(1-vp*vp))**(1+1/cs2b)-1)*(-1 + vm*vp*(1/cs2b))/3/(1+vm*vp)
    dalphalist[i,1] = (rp*(np.sqrt(1-vm*vm)/np.sqrt(1-vp*vp))**(1+1/cs2b)-1)*(-1 + vm*vp*(1/cs2b))/3/(1+vm*vp) - alplus
    

  plt.plot(matchlist[:,0],matchlist[:,1],color = 'blue')
#  plt.plot(matchlist[:,0],-matchlist[:,1],color = 'red')
  plt.plot(matchlist[:,0],alphalist[:,1],color = 'red')
#  plt.plot(matchlist[:,0],dalphalist[:,1],color = 'blue')
  plt.xlabel(r'$v_w$')
  plt.ylabel(r'$a_{\bar \theta}$ according to matching relation')
#  plt.yscale('log')
  plt.show()

def findvwsubj(cs2b,cs2s,al,rn):
  vmin = 0.01
  vmax = jouguet(al,cs2b)
  vmidprev = 0.5
  vmid = 0.5
  error = 10**(-6)
  maxsteps = 30
  steps = 0
  alplus = 200
  almatch = 100
  while(abs(alplus-almatch)>error and steps<maxsteps and abs(vmid-jouguet(al,cs2b))>error and abs(vmid-0.99)>error):
    vm, mode = getvm(al,vmid,cs2b)
      
    if mode<2:
      almax,wow = getalNwow(0,vm,vmid,cs2b,cs2s)
      if almax<al:
        print ("alpha too large for shock")
        return 0;

      vp = min(cs2s/vmid,vmid) #check here
      almin,wow = getalNwow(vp,vm,vmid,cs2b,cs2s)
      if almin>al: #minimum??
        print ("alpha too small for shock")
        return 0;

      iv = [[vp,almin],[0,almax]]
      while (abs(iv[1][0]-iv[0][0])>1e-7):
        vpm = (iv[1][0]+iv[0][0])/2.
        alm = getalNwow(vpm,vm,vmid,cs2b,cs2s)[0]
        if alm>al:
          iv = [iv[0],[vpm,alm]]
        else:
          iv = [[vpm,alm],iv[1]]
      #print iv
      vp = (iv[1][0]+iv[0][0])/2.

    else:
      vp = vmid

    alplus = getal(vp,vm,cs2b)

    rp=rn*((3*al*(1+1/cs2s)+1/cs2b-1/cs2s)/((3*alplus*(1+1/cs2s)+1/cs2b-1/cs2s)))**((-1/cs2s+1/cs2b)/(1/cs2s+1))
    almatch = (rp*(np.sqrt(1-vm*vm)/np.sqrt(1-vp*vp))**(1+1/cs2b)-1)*(-1 + vm*vp*(1/cs2b))/3/(1+vm*vp)
    vmidprev =vmid
    if(almatch<alplus):
      vmin = vmid
      vmid = (vmin+vmax)/2

    else:
      vmax = vmid
      vmid = (vmin+vmax)/2

    steps = steps+1

#  print(vmid, almatch, alplus)
  if(abs(vmid-jouguet(al,cs2b))<10**(-4) or abs(vmid-0.01)<10**(-4)):
    return(0)

  else:
    return(vmidprev)

def checkLTEshock(cs2b,cs2s,al,rn):
  vw = findvwsubj(cs2b,cs2s,al,rn)
  

def findvwdet(cs2b,cs2s,al,rn):
  vmin = jouguet(al,cs2b)
  vmax = 0.99
  vmid = (vmin+vmax)/2.
  error = 10**(-6)
  maxsteps = 30
  steps = 0
  almatch = 100
  while(abs(al-almatch)>error and steps<maxsteps and abs(vmid-jouguet(al,cs2b))>10**(-5) and abs(vmid-0.01)>10**(-5)):
    vm, mode = getvm(al,vmid,cs2b)
    vp = vmid

    almatch = (rn*(np.sqrt(1-vm*vm)/np.sqrt(1-vp*vp))**(1+1/cs2b)-1)*(-1 + vm*vp*(1/cs2b))/3/(1+vm*vp)
    if(almatch<al):
      vmin = vmid
      vmid = (vmin+vmax)/2

    else:
      vmax = vmid
      vmid = (vmin+vmax)/2
    steps = steps+1

  if(abs(vmid-jouguet(al,cs2b))<10**(-4) or abs(vmid-0.99)<10**(-4)):
    return(0)

  else:
    return(vmid) 

def plotvw(cs2b,cs2s,rn):
  try1 = np.logspace(-3,0,10) #alphas
  vwtry1 = np.empty(10)
  vwdettry1 = np.empty(10)
  for i in range(10):
    vwtry1[i] = findvwsubj(cs2b,cs2s,try1[i],rn)
    vwdettry1[i] = findvwdet(cs2b,cs2s,try1[i],rn)
  solsfound = np.nonzero(vwtry1)
  solsfounddet = np.nonzero(vwdettry1)

  try2 = np.logspace(np.log10(try1[solsfound[0][0]-1]),np.log10(try1[solsfound[0][-1]+1]),50)
  try2det = np.logspace(np.log10(try1[solsfounddet[0][0]-1]),np.log10(try1[solsfounddet[0][-1]+1]),50)
  vwtry2 = np.empty(50)
  vwdettry2 = np.empty(50)
  if len(solsfound[0]) != 0:
    for i in range(50):
      vwtry2[i] = findvwsubj(cs2b,cs2s,try2[i],rn)

  if len(solsfounddet[0]) != 0:
    for i in range(50):
      vwdettry2[i] = findvwdet(cs2b,cs2s,try2[i],rn)

  
  plt.plot(try2[:],vwtry2[:],color = 'blue')
  plt.plot(try2det[:],vwdettry2[:],color = 'red')
  plt.xlabel(r'$\alpha$')
  plt.ylabel(r'$v_w$')
  plt.xscale('log')
  plt.show()
  return
