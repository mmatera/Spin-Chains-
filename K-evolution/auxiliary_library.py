# In [1]:

import qutip
import numpy as np
import scipy.optimize as opt 
import pickle
import time as time
import sys
import scipy.linalg as linalg

# In [2]:

### This module checks if the matrix is positive definite ie. if all its eigenvalues are positive

def ev_checks(rho):
    a = bool; ev_list = linalg.eig(rho)[0]
    for i in range(len(ev_list)):
        if (ev_list[i] > 0):
            a = True
        else:
            a = False
            print("Eigenvalues not positive")
    return a

### This module checks if the user-input quantum object, rho, is a density operator or not.
### This is done by checking if it is a hermitian, positive definite, trace-one, matrix.
### Due to numerical instabilities, it may be possible that the trace is not exactly one, even though it is supposed to be,
### Therefore, a cut-off is implemented to determine if rho is, at least trace-wise, a matrix operator. 

def is_density_op(rho):
    return (qutip.isherm(rho) and (abs(1 - rho.tr()) < 10**-10) and ev_checks(rho))

def null_matrix_check(rho):
    return (linalg.norm(rho) < 10**-10)

def commutator(A, B):
    result = 0
    if A.dims[0][0] == B.dims[0][0]: 
        pass
    else:
        raise Exception("Incompatible Qobj dimensions")
    result += A*B-B*A
    return result

def anticommutator(A, B):
    result = 0
    if A.dims[0][0] == B.dims[0][0]: 
        pass
    else:
        raise Exception("Incompatible Qobj dimensions")
    result += A*B+B*A
    return result

def hamiltonian_comm_check(Hamiltonian, basis, labels = None):
    if type(basis) is dict:
        for key in basis: 
            print("[H, ", key, "] = 0?: ", null_matrix_check(commutator(Hamiltonian, basis[key])))
    if type(basis) is list:
        for i in range(len(basis)):
            print("[H, ", labels[i], "] = 0?: ", null_matrix_check(commutator(Hamiltonian, basis[i])))
    return None

# In [3]: 

### Given an N-site spin chain, there are then 3N different, non-trivial, operators acting on the full Hilbert space.
### N sigmax operators, N sigmay operators, N sigmaz operators, and a global identity operator. 
### All these 3N+1-operators are constructed with a tensor product so that they all act on the full Hilbert space. 
### All, but the global identity operator, act non-trivially only on one Hilbert subspace. 

def one_body_spin_ops(N):
    
    ### Basic, one-site spin operators are constructed.
    
    loc_sx_list = []; loc_sy_list = []; loc_sz_list = []; loc_globalid_list = []
    id2 = qutip.qeye(2)
    sx = .5*qutip.sigmax()
    sy = .5*qutip.sigmay()
    sz = .5*qutip.sigmaz()
    
    ### The global identity operator is constructed 
    
    loc_global_id = [qutip.tensor([qutip.qeye(2) for k in range(N)])]
    
    ### Lists of one-body operators are constructed, so that they all act on the full Hilbert space. This is done
    ### via taking tensor products on lists of operators. 
    
    for n in range(N):
        operator_list = []
        for m in range(N):
            operator_list.append(id2)
        loc_globalid_list.append(loc_global_id)
        operator_list[n] = sx
        loc_sx_list.append(qutip.tensor(operator_list))
        
        operator_list[n] = sy
        loc_sy_list.append(qutip.tensor(operator_list))
        
        operator_list[n] = sz
        loc_sz_list.append(qutip.tensor(operator_list))        
    return loc_global_id, loc_sx_list, loc_sy_list, loc_sz_list

### This module is relevant only if a non-unitary Lindblad evolution is chosen, it constructs a list of 
### collapse operators, with its corresponding collapse factors. In particular, sz collapse operators are chosen. 

def spin_dephasing(op_list, N, gamma):
        loc_c_op_list = []; 
        loc_sz_list = op_list[3]
        
        collapse_weights = abs(gamma) * np.ones(N)
        loc_c_op_list = [np.sqrt(collapse_weights[n]) * loc_sz_list[n] for n in range(N)]
    
        return loc_c_op_list

# In [4]: 

### This module constructs all pair-wise combinations (ie. correlators) of non-trivial one-body operators (ie. sx, sy, sz operators only). 
### There are N(N+1)/2 different correlators in an N-site spin chain.

def all_two_body_spin_ops(op_list, N):
    loc_global_id_list, sx_list, sy_list, sz_list = op_list
      
    pauli_four_vec = [loc_global_id_list, sx_list, sy_list, sz_list];
        
    sxsa_list = []; sysa_list = []; szsa_list = []; two_body_s = [];
    
    sxsa_list = [sx_list[n] * pauli_four_vec[a][b] for n in range(N)
                                                   for a in range(len(pauli_four_vec))
                                                   for b in range(len(pauli_four_vec[a]))]
    
    sysa_list = [sy_list[n] * pauli_four_vec[a][b] for n in range(N)
                                                   for a in range(len(pauli_four_vec))
                                                   for b in range(len(pauli_four_vec[a]))]
    
    szsa_list = [sz_list[n] * pauli_four_vec[a][b] for n in range(N)
                                                   for a in range(len(pauli_four_vec))
                                                   for b in range(len(pauli_four_vec[a]))]
    
    two_body_s = [sxsa_list, sysa_list, szsa_list]
    return two_body_s

# In [5]: 

### This module is redundant in its current form. It basically either constructs all two-body correlators 
### or some subset of these. 

def two_body_spin_ops(op_list, N, build_all = False):
    loc_list = []
    if build_all:
        loc_list = all_two_body_spin_ops(op_list, N)
    else: 
        globalid_list, sx_list, sy_list, sz_list = op_list       
        loc_sxsx = []; loc_sysy = []; loc_szsz = [];
        
        loc_sxsx = [sx_list[n] * sx_list[m] for n in range(N)
                                            for m in range(N)]
        loc_sysy = [sy_list[n] * sy_list[m] for n in range(N)
                                            for m in range(N)]
        loc_szsz = [sz_list[n] * sz_list[m] for n in range(N)
                                            for m in range(N)]
        loc_list.append(loc_sxsx)
        loc_list.append(loc_sysy)
        loc_list.append(loc_szsz)
    return loc_list

# In [6]: 

### This module constructs the Heisenberg Hamiltonian for different types of systems, according to some user-inputed parameters. 

def Heisenberg_Hamiltonian(op_list, chain_type, N, visualization, Hamiltonian_paras, closed_bcs = True):
    spin_chain_type = ["XX", "XYZ", "XXZ", "XXX", "Anderson"]
    loc_globalid_list, sx_list, sy_list, sz_list = op_list       
          
    H = 0    
    Jx = Hamiltonian_paras[0] * 2 * np.pi #* np.ones(N)
    h =  Hamiltonian_paras[3] * 2 * np.pi #* np.ones(N)
    H += sum(-.5* h * sz_list[n] for n in range(N-1)) # Zeeman interaction 
    
    if (chain_type in spin_chain_type): 
        if (chain_type == "XX"):
            H += sum(-.5* Jx *(sx_list[n]*sx_list[n+1] 
                                 + sy_list[n]*sy_list[n+1]) for n in range(N-1))
            if closed_bcs: 
                H += .5* Jx *(sx_list[N-1]*sx_list[1] + sy_list[N-1]*sy_list[1])
            
        elif (chain_type == "XXX"):
            H += sum(-.5* Jx * (sx_list[n]*sx_list[n+1] 
                                 + sy_list[n]*sy_list[n+1]
                                 + sz_list[n]*sz_list[n+1]) for n in range(N-1))
            if closed_bcs: 
                H += .5* Jx * (sx_list[N-1]*sx_list[1] 
                                 + sy_list[N-1]*sy_list[1]
                                 + sz_list[N-1]*sz_list[1])
        
        elif (chain_type == "XXZ"):
            Jz =  Hamiltonian_paras[2] * 2 * np.pi #* np.ones(N)
            H += sum(-.5 * Jx * (sx_list[n] * sx_list[n+1] + sy_list[n] * sy_list[n+1]) 
                     -.5 * Jz * (sz_list[n] * sz_list[n+1]) for n in range(N-1))
            if closed_bcs: 
                H += -.5 * Jx * (sx_list[N-1] * sx_list[1] + sy_list[N-1] * sy_list[1]) 
                -.5 * Jz * (sz_list[N-1] * sz_list[1])
        
        elif (chain_type == "XYZ"):
            Jy = Hamiltonian_paras[1] * 2 * np.pi #* np.ones(N)
            Jz = Hamiltonian_paras[2] * 2 * np.pi #* np.ones(N)
            H += sum(-.5 * Jx * (sx_list[n] * sx_list[n+1]) 
                     -.5 * Jy * (sy_list[n] * sy_list[n+1]) 
                     -.5 * Jz * (sz_list[n] * sz_list[n+1]) for n in range(N-1))
            if closed_bcs: 
                H += -.5 * Jx * (sx_list[N-1] * sx_list[1])
                -.5 * Jy * (sy_list[N-1] * sy_list[1]) 
                -.5 * Jz * (sz_list[N-1] * sz_list[1])
                
        elif (chain_type == "Anderson"):
            pass
    else:
        sys.exit("Currently not supported chain type")
              
    if visualization:
        qutip.hinton(H)
        
    if (qutip.isherm(H)): 
        return H
    else:
        sys.exit("Non-Hermitian Hamiltonian obtained")

def Heisenberg_Hamiltonian_tests(spin_ops_list, N):
    
    start_time = time.time()
    Hamiltonian_paras = [.2, .15, .1, 1.]
    spin_chain_type = ["XX", "XYZ", "XXZ", "XXX"]
    all_hamiltonians_are_hermitian = [False for i in range(2* len(spin_chain_type))]
    
    for i in range(len(spin_chain_type)):
        all_hamiltonians_are_hermitian[i] = qutip.isherm(Heisenberg_Hamiltonian(spin_ops_list, spin_chain_type[i],
                                                                              N, False, Hamiltonian_paras, False))
        if (all_hamiltonians_are_hermitian[i] == True):
            pass
        else:
            print(spin_chain_type[i], "Hamiltonian with open bcs non-hermitian")
        
        
    for i in range(len(spin_chain_type)):
        all_hamiltonians_are_hermitian[4+i] = qutip.isherm(Heisenberg_Hamiltonian(spin_ops_list, spin_chain_type[i],
                                                                              N, False, Hamiltonian_paras, True))
        
        if (all_hamiltonians_are_hermitian[i] == True):
            pass
        else:
            print(spin_chain_type[i], "Hamiltonian with closed bcs non-hermitian")
    
    if (Heisenberg_Hamiltonian_tests(spin_ops_list, N) == [True for i in range(2*len(spin_chain_type))]):
        print("All Hamiltonians are correct")
    
    print("--- Test concluded in: %s seconds ---" % (time.time() - start_time))
    
    return all_hamiltonians_are_hermitian

# In [7]: 

natural = tuple('123456789')

def n_body_basis(op_list, gr, N):
    basis = []
    globalid_list, sx_list, sy_list, sz_list = op_list       
        
    if (isinstance(gr,int) and str(gr) in natural):
        try:
            if (gr == 1):
                basis = globalid_list + sx_list + sy_list + sz_list
            elif (gr > 1):
                basis = [op1*op2 for op1 in n_body_basis(op_list, gr-1, N) for op2 in n_body_basis(op_list, 1, N)]
        except Exception as ex:
            basis = None
            print(ex)
    return basis

def max_ent_basis(op_list, op_basis_order_is_two, N, rho0):
    if (op_basis_order_is_two):
        basis = base_orth(n_body_basis(op_list, 2, N), rho0, sc_prod, False)  ## two-body max ent basis
        a = "two"
    else: 
        lista_ampliada = []
        for i in range(len(n_body_basis(op_list, 1, N))):
            lista_ampliada.append(qutip.tensor(n_body_basis(op_list, N,1)[i], qutip.qeye(2)))
        basis = base_orth(lista_ampliada, rho0, sc_prod, False) ## one-body max-ent basis
        a = "one"
    
    print(a + "-body operator chosen")
    return basis

# In [8]:

def n_body_max_ent_state(op_list, gr, N, coeffs = list, build_all = True, visualization = False):
    K = 0; rho_loc = 0;
    
    loc_globalid = qutip.tensor([qutip.qeye(2) for k in range(N)]) 
    
    globalid_list, sx_list, sy_list, sz_list = op_list       
    
    pauli_vec = [sx_list, sy_list, sz_list];
    
    if (gr == 1):
        try:
            K += sum(coeffs[n][m] *  one_body_spin_ops(N)[n][m] 
                                    for n in range(len(one_body_spin_ops(N)))
                                    for m in range(len(one_body_spin_ops(N)[n]))
                   ) 
            K += 10**-6 * loc_globalid
        except Exception as exme1:
            print(exme1, "Max-Ent 1 Failure")
            raise exme1
    elif (gr == 2): 
        try:
            K += sum(coeffs[n][m] * two_body_spin_ops(op_list, N, build_all)[n][m] 
                    for n in range(len(two_body_spin_ops(op_list, N, build_all)))
                    for m in range(len(two_body_spin_ops(op_list, N, build_all)[n]))
                   )
            K += 10**-6 * loc_globalid
        except Exception as exme2:
            print(exme2, "Max-Ent 2 Failure")
            raise exme2
    else:
        print('gr must be either 1 or 2')
    
    rho_loc = K.expm()
    rho_loc = rho_loc/rho_loc.tr()
    
    if is_density_op(rho_loc):
        pass
    else:  
        rho_loc = None 
        raise Exception("The result is not a density operator")
        
    if visualization: 
        qutip.hinton(rho_loc)
        
    return rho_loc 

# In [9]: 

def initial_state(op_list, N = 1, gaussian = True, gr = 1, x = .5, coeffs = list, psi0 = qutip.Qobj,
                  build_all = False, visualization=False):
    
    loc_globalid = qutip.tensor([qutip.qeye(2) for k in range(N)]) 
    if gaussian: 
        rho0 = n_body_max_ent_state(op_list, gr, N, coeffs, build_all, False)
    else:
        if (qutip.isket(psi0)):
            rho0 = psi0 * psi0.dag()
            rho0 = x * rho0 + (1-x)*loc_globalid * x/N
            rho0 = rho0/rho0.tr()
        else:
            print("Psi0 must be a ket")
    
    if is_density_op(rho0):
        pass
    else: 
        rho0 = None
        print("Output is not a density operador")
    
    if visualization:
            qutip.hinton(rho0)
    
    return rho0  

# In [10]: 

def choose_initial_state_type(op_list, N, build_all, x, gaussian, gr):
    
    if (gaussian and gr == 1):
        a = len(op_list)
        b = len(op_list[0])
        coeffs_me1_gr1 = 10**-2.5 * np.full((a,b), 1)
        rho0 = initial_state(op_list, N, True, 1, None, coeffs_me1_gr1, None, build_all, False)
        statement = "One-body Gaussian"
        
    elif(gaussian and gr == 2):
        a = len(all_two_body_spin_ops(op_list, N))
        b = len(all_two_body_spin_ops(op_list, N)[0])

        coeffs_me2_gr2 = 10**-3 * np.full((a,b),1.)
        rho0 = initial_state(op_list, N, True, 2, None, coeffs_me2_gr2, None, build_all, False)
        statement = "Two-body Gaussian"
             
    elif(not gaussian):
        psi1_list = []
        psi1_list.append(qutip.basis(2,0))
        for n in range(N-1):
            psi1_list.append(qutip.basis(2,1))

        psi0 = qutip.tensor(psi1_list)
        rho0 = initial_state(op_list, N, False, None, .5, None, psi0, build_all, False)
        statement = "Non Gaussian"
      
    if gaussian:
         print(statement + " initial state chosen")
            
    return rho0

#In [11]:

def prod_basis(b1, b2):
    return [qutip.tensor(b,s) for b in b1 for s in b2]

def HS_inner_prod_t(op1, op2, rho0 = None): ### previous name: HS_inner_prod(A, B, rho0 = None):
    if (op1.dims[0][0]==op2.dims[0][0]):    ### Formally, this is the correct Hilbert-Schmidt inner product
        pass                                ### It is a complex valued inner product on the space of all endomorphisms 
    else:                                   ### acting on the N-partite Hilbert space 
        raise Exception("Incompatible Qobj dimensions")
    
    if rho0 is None:
        rho0 = qutip.qeye(op1.dims[0])
        rho0 = rho0/rho0.tr()        
    else:
        if (is_density_op(rho0)):
            pass
        else:
            sys.exit("rho0 is not a density op")
        
    result = 0
    result += (rho0 * (op1.dag() * op2)).tr()    
    return result

def HS_inner_prod_r(op1, op2, rho0 = None): ### This inner product is real valued, provided both op1 and op2 are hermitian
    if (op1.dims[0][0]==op2.dims[0][0]):    ### and is easier to compute when dealing with spin chains, as the operator themselves 
        pass                                ### can be written as tensor products of local operators. A global-trace is then a product 
    else:                                   ### of traces over local Hilbert spaces
        raise Exception("Incompatible Qobj dimensions")
    
    if rho0 is None:
        rho0 = qutip.qeye(op1.dims[0])
        rho0 = rho0/rho0.tr()
    else:
        if (is_density_op(rho0)):
            pass
        else:
            sys.exit("rho0 is not a density op")
        
    result = 0
    result += .5 * (rho0 * anticommutator(op1.dag(), op2)).tr()    
    return result

def HS_inner_norm(op, rho0, sc_prod): ### previous name: mod_HS_inner_norm
    return sc_prod(op, op, rho0)

def HS_normalize_op(op, rho0, sc_prod):
    op = op/sc_prod(op, op, rho0)
    return op

def HS_distance(rho, sigma, rho0, sc_prod):
    if rho.dims[0][0]==sigma.dims[0][0]:
        pass
    else:
        raise Exception("Incompatible Qobj dimensions")
    
    return sc_prod(rho, sigma, rho0)

def base_orth(ops, rho0, sc_prod, visualization = False):
    if isinstance(ops[0], list):
        ops = [op for op1l in ops for op in op1l]
    dim = ops[0].dims[0][0]
    basis = []
    for i, op in enumerate(ops): 
        alpha = [sc_prod(op2, op, rho0) for op2 in basis]
        if visualization:
            print(alpha)
        op_mod = op - sum([c*op2 for c, op2, in zip(alpha, basis)])
        op_norm = np.sqrt(sc_prod(op_mod,op_mod,rho0))
        if op_norm<1.e-12:
            #pass
            continue
        op_mod = op_mod/(op_norm)
        basis.append(op_mod)
    return basis

# In [12]: 

def logM(rho):
    if ev_checks(rho):
        pass
    else:
        raise Exception("Singular input matrix")
    eigvals, eigvecs = rho.eigenstates()
    return sum([np.log(vl)*vc*vc.dag() for vl, vc in zip(eigvals, eigvecs)])

def sqrtM(rho):
    if ev_checks(rho):
        pass
    else:
        raise Exception("Singular input matrix")
    eigvals, eigvecs = rho.eigenstates()
    return sum([(vl**.5)*vc*vc.dag() for vl, vc in zip(eigvals, eigvecs)])

def bures(rho, sigma):
    if (is_density_op(rho) and is_density_op(sigma)):
        val1 = abs((sqrtM(rho)*sqrtM(sigma)).tr())
        val1 = max(min(val1,1.),-1.)
        val1 = np.arccos(val1)/np.pi
    else: 
        sys.exit("Singular input matrix")
    return val1

# In [13]: 

def proj_op(K, basis, rho0, sc_prod):
    return sum([sc_prod(b, K,rho0) * b for b in basis])

def rel_entropy(rho, sigma):
    if (ev_checks(rho) and ev_checks(sigma)):
        pass
    else:
        raise Exception("Either rho or sigma non positive")
    
    val = (rho*(logM(rho)-logM(sigma))).tr()
                    
    if (abs(val.imag - 0)>1.e-6):
        val = None
        raise Exception("Either rho or sigma not positive")
    return val.real
                
# In [14]:
        
def maxent_rho(rho, basis):   
    def test(x, rho, basis):
        k = sum([-u*b for u,b in zip(x, basis)])        
        sigma = (.5*(k+k.dag())).expm()
        sigma = sigma/sigma.tr()
        return rel_entropy(rho, sigma)    
    res = opt.minimize(test,zeros(len(basis)),args=(rho,basis))
    k = sum([-u*b for u,b in zip(res.x, basis)])        
    sigma = (.5*(k+k.dag())).expm()
    sigma = sigma/sigma.tr()
    return sigma
 
def error_maxent_state(rho, basis, distance=bures):
    try:
        sigma = maxent_rho(rho, basis)
        return distance(rho,sigma)
    except:
        print("fail error max-ent state")
        return None
       
def error_proj_state(rho, rho0, basis, distance=bures):
    try:
        basis = base_orth(basis, rho0, sc_prod, False)
    except:
        print("orth error")
        raise
    try:
        sigma = proj_op(logM(rho), basis, rho0, sc_prod).expm()
        sigma = (sigma+sigma.dag())/(2.*sigma.tr())
    except:
        print("gram error")
    try:
        return distance(rho, sigma)
    except:
        print("fail error proj state")
        return None
    
# In [15]:

def legacy_classical_ops(n, Hamiltonian):
    id_loc = qutip.qeye(2)
    sz_loc = .5*qutip.sigmaz()
    sx_loc = .5*qutip.sigmax()
    sy_loc = .5*qutip.sigmay()

    n_oc =  sum(qutip.tensor([id_loc for i in range(k)]+ 
                     [(sz_loc + .5*id_loc)]+ 
                     [id_loc for i in range(n-k-1)]
                    ) for k in range(n-1))
    x = sum(qutip.tensor([id_loc for i in range(k)]+ 
                     [(k-n/2)*(sz_loc + .5*id_loc)]+ 
                     [id_loc for i in range(n-k-1)]
                    ) for k in range(n-1))
    Mauricio_noc = sum([qutip.tensor([id_loc for i in range(k)]+ 
                     [(sz_loc + .5*id_loc)]+ 
                     [id_loc for i in range(n-k-1)]) for k in range(n-1)])
    Tom_noc = sum([spin_ops_list[3][k] + .5 * spin_ops_list[0][0] for k in range(n-1)])
    Mauriciox = sum(qutip.tensor([id_loc for i in range(k)]+ 
                     [(k-n/2)*(sz_loc + .5*id_loc)]+ 
                     [id_loc for i in range(n-k-1)]
                    ) for k in range(n-1))
    Tomix = sum((k-n/2)*(spin_ops_list[3][k] + .5 * spin_ops_list[0][0]) for k in range(n-1))
    return None

def classical_ops(Hamiltonian, N, op_list, centered_x_op = False):
    
    identity_op = op_list[0][0]; sz_list = op_list[3]    
    labels = ["x_op", "p_op", "n_oc_op", "comm_xp", "corr_xp", "p_dot"]
    
    cl_ops = {}
    
    if centered_x_op:
        cl_ops["x_op"] = sum((.5 + sz_list[k])*(k+1) for k in range(len(sz_list)))
    else:
        cl_ops["x_op"] = sum((k-N/2)*(sz_list[k] + .5 * identity_op) for k in range(len(sz_list)-1)) 
        
    cl_ops["p_op"] = 1j * commutator(cl_ops["x_op"], Hamiltonian)
    cl_ops["n_oc_op"] = sum([sz_list[k] + .5 * identity_op for k in range(len(sz_list)-1)])
    cl_ops["comm_xp"] = .5 * anticommutator(cl_ops["x_op"], cl_ops["p_op"])
    cl_ops["corr_xp"] = -1j * commutator(cl_ops["x_op"], cl_ops["p_op"])
    cl_ops["p_dot"] = 1j * commutator(Hamiltonian, cl_ops["p_op"])
    
    
    for i in range(len(labels)):
        if qutip.isherm(cl_ops[labels[i]]):
            pass
        else:
            print(labels[i], "not hermitian")
    return cl_ops, labels
    
HS_modified = True

class Result(object):
      def __init__(self, ts=None, states=None):
        self.ts = ts
        self.states = states
        self.projrho0_app = None   
        self.projrho_inst_app = None 

rhos = []
def callback(t, rhot):
    global rhos
    rhos.append(rhot)

def spin_chain_ev(size, init_state, chain_type, Hamiltonian_paras, omega_1=3., omega_2=3., temp=1, tmax = 250, deltat = 10, 
                  two_body_basis = True, unitary_ev = False, gamma = 1*np.e**-2,
                  gaussian = True, gr = 2, xng = .5, sc_prod = HS_inner_prod_r, obs_basis = None, do_project = True):
    
    global rho
    build_all = True
    
    ### The algorithm starts by constructing all one-body spin operators, acting on the full N-particle Hilbert space
    ### This means, it constructs the 3N + 1 one_body spins ops (N sigmax operators, N sigmay operators, N sigmaz operators
    ### an the global identity operator
    
    spin_big_list = one_body_spin_ops(size)
    loc_globalid = one_body_spin_ops(size)[0][0]
    
    #Jx = Hamiltonian_paras[0]; Jy = Hamiltonian_paras[1]
    #Jz = Hamiltonian_paras[2]; h = Hamiltonian_paras[3] 
    
    ### Then, the algorithm either takes a user-input initial density matrix or it constructs a default one.
    
    if init_state is None:
        print("Processing default initial state")
        rho0 = choose_initial_state_type(spin_big_list, size, build_all, xng, gaussian, gr)
    else: 
        print("Processing custom initial state")
        if (is_density_op(init_state)):
            rho0 = init_state
        else:
            raise Exception("User input initial state not a density matrix")
    
    ### Then, the algorithm either takes a user-input choice for observables or it constructs a default one. 
    
    if obs_basis is None: 
        print("Processing default observable basis")
        x_op, p_op, comm_xp, corr_xp, p_dot = classical_ops(spin_big_list, chain_type, size, Hamiltonian_paras)
        obs = [x_op, p_op, comm_xp, corr_xp, p_dot] #, x_op**2,p_op**2, corr_op, p_dot]
    else:
        print("Processing custom observable basis")
        obs = obs_basis
        
    sampling = max(int(10*max(1,omega_1, omega_2)*deltat), 10)
    print("sampling:", sampling)
    
    ### If a unitary evolution is chosen, no colapse operators nor colapse factors are taken into account. 
    ### Otherwise, a default sz-colapse operator list is chosen. 
    
    if unitary_ev: 
        print("Closed evolution chosen")
        c_op_list = None
    else:
        print("Open evolution chosen")
        c_op_list = spin_dephasing(spin_big_list, size, gamma)
        
    rho = init_state                                                               
    approx_exp_vals = [[qutip.expect(op, rho) for op in obs]]
    ts= [0]
    
    ### If a projected evolution is desired, then a two-body spin operator basis is chosen. Otherwise, if the exact ev,
    ### is desired, this step will be skipped. 
    
    if do_project:    
        print("Processing two-body for proj ev")
        basis = max_ent_basis(spin_big_list, two_body_basis, size, rho0)
    
    for i in range(int(tmax/deltat)):
        ### Heisenberg Hamiltonian is constructed 
        qutip.mesolve(H=Heisenberg_Hamiltonian(spin_big_list, chain_type, size, False, Hamiltonian_paras), 
                               rho0=rho, 
                               tlist=np.linspace(0,deltat, sampling), 
                               c_ops=c_op_list, 
                               e_ops=callback,
                               args={'gamma': gamma,'omega_1': omega_1, 'omega_2': omega_2}
                               )
        ts.append(deltat*i)
        if do_project:
            rho = proj_op(logM(rho), basis, rho0, sc_prod)
            #rho = proj_op(logM(rho), basis, loc_globalid, sc_prod)
            e0 = max(rho.eigenenergies())
            rho = rho - loc_globalid * e0
            rho = rho.expm()
            trrho = (2.*rho.tr())
            rho = (rho+rho.dag())/trrho

        #print(qutip.entropy.entropy_vn(rho))
        newobs = [qutip.expect(rho, op) for op in obs]
        approx_exp_vals.append(newobs)
        
    #print(f"type rho={type(rho)}")
    result = {}
    result["ts"] = ts
    result["averages"] = np.array(approx_exp_vals)
    result["State ev"] = rhos
    
    if unitary_ev:
        title = f"{chain_type}-chain closed ev/Proj ev for N={size} spins" 
    else:
        title = f"{chain_type}-chain open ev/Proj ev for N={size} spins" 
    
    #with open(title+".pkl","wb") as f:
    #    pickle.dump(result, f)
    
    #print("type rho=", type(result["State ev"]))
    
    ev_parameters = {"no. spins": size, "chain type": chain_type, "Model parameters": Hamiltonian_paras, "Sampling": sampling, 
                     "Two body basis": two_body_basis, "Closed ev": unitary_ev, "Colapse parameters": gamma, 
                     "Gaussian ev": gaussian, "Gaussian order": gr, "Non-gaussian para": xng, "Type of inner product": sc_prod,
                     "no. observables returned": len(obs), "Proj. ev": do_project}
    
    return title, ev_parameters, result

# In [16]: 

def recursive_basis(N, depth, H, seed_op, rho0): 
    
    null_matrix = np.zeros([(2**N), (2**N)]) 
    null_matrix = qutip.Qobj(null_matrix.reshape((2**N, 2**N)), dims= [H.dims[0], H.dims[1]])
    basis = []
    i = 0
    
    if (type(depth) == int):
        while (i != depth):
            if (i == 0):
                loc_op = seed_op
            else:
                loc_op = -1j * commutator(H, loc_op)
                if (loc_op == null_matrix):
                    print("Null operator obtained at the", i, "-th level")
            loc_op = (rho0 * loc_op).tr() - loc_op
            basis.append(loc_op)
            i += 1
    else:
        basis = None 
        raise Exception("Incursive depth parameter must be integer")
        
    return basis

def Hamiltonian_and_basis_obs(N, op_list, chain_type, Hamiltonian_paras, default_basis = True):
    
    H_H = Heisenberg_Hamiltonian(op_list, chain_type, N, False, Hamiltonian_paras)
    
    sx_list = op_list[1]
    sz_list = op_list[3]
    basis = []
    
    if default_basis:
        Mz = sum(sz_list[i] for i in range(N))
        loc_magnetization = [op_list[3][i] for i in range(len(op_list[3]))]
        NN_interactions_on_x = [sx_list[i]*sx_list[i+1] + sx_list[i+1]*sx_list[i]  for i in range(3)] + [sx_list[3]*sx_list[0]+sx_list[0]*sx_list[3]]
            
        basis.append(Mz)
        for i in range(len(loc_magnetization)):
            basis.append(loc_magnetization[i])
        for j in range(len(NN_interactions_on_x)):
            basis.append(NN_interactions_on_x[j])
        #basis.append([["1"]])
    else:
        basis = None
    
    for i in range(len(basis)):
        if (type(basis[i]) != list):
            continue
        else:
            sys.exit("Error: basis is a list of lists")
    
    return H_H, basis

def initial_conditions(basis):
    coeff_list_t0 = [np.random.rand() for i in range(len(basis))]
    rho0 = (sum(np.pi * coeff_list_t0[i] * basis[i] for i in range(len(basis)))).expm()
    rho0 = rho0/rho0.tr()

    if is_density_op(rho0):
        pass
    else:
        pass
        #sys.exit("Not a density operator")
    
    return coeff_list_t0, rho0

# In [17]:

def H_ij_matrix(HH, basis, rho0, sc_prod):
    
    coeffs_list = []
    ith_oprator_coeff_list = []
    for i in range(len(basis)):
        ith_operator_coeff_list = [sc_prod(basis[i], commutator(HH, op2), rho0) for op2 in basis]
        coeffs_list.append(ith_operator_coeff_list)
        ith_operator_coeff_list = []
    
    #coeffs_list = [[sc_prod(op1, commutator(HH, op2), rho0) for op1 in basis] for op2 in basis]
    coeffs_matrix = np.array(coeffs_list) # convert list to numpy array
    
    return coeffs_list, coeffs_matrix

def basis_orthonormality_check(basis, rho0, sc_prod):

    ### No es del todo eficiente pero es O(N), siendo N el tamaño de la base
    
    all_herm = False
    gram_diagonals_are_one = False
    all_ops_orth = False
    gram_matrix = []
    
    for i in range(len(basis)):
        gram_matrix.append([sc_prod(basis[i], op, rho0) for op in basis])
        if (qutip.isherm(basis[i])):
            all_herm = True
        else:
            all_herm = False
            print("The", i,"-th operator is non-hermitian \n")
    
    identity_matrix = np.full((len(basis), len(basis)), 1)
    
    for i in range(len(basis)): 
        if (abs((rho0 * basis[i]).tr() - 0) > 10**-10):
            print("Not mean-normalized operator at", i, "-th level")
            print((rho0 * basis[i]).tr())
        if (abs(gram_matrix[i][i] - 1) < 10**-10):
            all_gram_diagonals_are_one = True
        else:
            all_gram_diagonals_are_one = False
            print("The", i,"-th operator is not normalized \n")
        
    if (linalg.norm((np.identity(len(basis)) - gram_matrix) < 10**-10)):
        all_ops_orth = True
    else:
        all_ops_orth = False
        print("Not all operators are pair-wise orthogonal")
    
    if (all_herm and all_gram_diagonals_are_one and all_ops_orth):
        print("The basis is orthonormal")
    
    return qutip.Qobj(gram_matrix)

# Un pequeño test: si meto un operador no hermítico de prepo, saltan las alarmas correctamente
# notsx0sx1 = 1j * spin_ops_list[1][0] * spin_ops_list[1][1]
# mk_basis.popend()
