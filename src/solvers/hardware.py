import numpy as np
from scipy.optimize import OptimizeResult
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import EstimatorV2, SamplerV2, Session # [추가] Session 임포트
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit_algorithms.optimizers import SPSA, COBYLA, POWELL

from src.backend_utils import get_backend_config
from src.decomposition import decompose_B_matrix, decompose_C_matrix, decompose_A_matrix, dict_to_sparse_pauli
from src.circuits.hadamard import create_overlap_circuit

def run_vqe_fully_hardware_v2(m_qubits, ansatz, b_circuit, backend_mode='noiseless', hub_info=None, optimizer='SPSA', options=None):
    """
    SamplerV2와 EstimatorV2를 사용하며, 'real' 모드일 경우 Qiskit Runtime Session을 적용하여
    대기열 문제를 해결하고 실행 속도를 최적화합니다.
    """
    
    # 1. Backend 설정
    print(f"[INFO] Setting up backend for mode: {backend_mode}")
    backend, target_backend = get_backend_config(backend_mode, hub_info)
    
    pass_manager = None
    
    # Transpilation을 위한 PassManager (공통 사용)
    if target_backend is not None:
        pass_manager = generate_preset_pass_manager(target=target_backend.target, optimization_level=3)

    # 2. 연산자 및 회로 준비 (최적화 루프 진입 전 1회 수행)
    # Term 1용: A^2
    B_dict = decompose_B_matrix(m_qubits)
    C_dict = decompose_C_matrix(m_qubits)
    A2_dict = {**B_dict}
    for k, v in C_dict.items():
        A2_dict[k] = A2_dict.get(k, 0) - v
    A2_op = dict_to_sparse_pauli(A2_dict, m_qubits)
    
    # Term 2용: A
    A_dict = decompose_A_matrix(m_qubits)
    A_op = dict_to_sparse_pauli(A_dict, m_qubits)
    
    # 3. Transpilation (ISA 변환)
    if pass_manager is not None:
        print("[INFO] Transpiling Ansatz and Observables...")
        ansatz_isa = pass_manager.run(ansatz)
        try:
            A2_op_isa = A2_op.apply_layout(ansatz_isa.layout)
        except Exception:
            A2_op_isa = A2_op
    else:
        ansatz_isa = ansatz
        A2_op_isa = A2_op

    # 4. Hadamard Test 회로 캐싱
    print("[INFO] Generating Hadamard test circuits...")
    ht_circuits_cache = []
    
    for i, pauli in enumerate(A_op.paulis):
        coeff = A_op.coeffs[i]
        qc_r = create_overlap_circuit(b_circuit, ansatz, pauli, is_imaginary=False)
        qc_i = create_overlap_circuit(b_circuit, ansatz, pauli, is_imaginary=True)
        
        if pass_manager is not None:
            qc_r = pass_manager.run(qc_r)
            qc_i = pass_manager.run(qc_i)
            
        ht_circuits_cache.append({'coeff': coeff, 'real': qc_r, 'imag': qc_i})

    # 5. Cost Function 정의 (Primitives는 내부에서 바인딩됨)
    iteration_log = []

    def create_cost_func(estimator, sampler):
        """Primitives를 Closure로 받는 Cost Function 생성"""
        def cost_func(params):
            params = np.array(params)

            # --- Term 1 (Estimator) ---
            pub_est = (ansatz_isa, A2_op_isa, params)
            job_est = estimator.run([pub_est])
            try:
                term1 = float(job_est.result()[0].data.evs)
            except TypeError:
                term1 = float(job_est.result()[0].data.evs[0])
            
            # --- Term 2 (Sampler) ---
            sampler_pubs = []
            for item in ht_circuits_cache:
                sampler_pubs.append((item['real'], params))
                sampler_pubs.append((item['imag'], params))
                
            job_sam = sampler.run(sampler_pubs)
            results = job_sam.result()
            
            total_overlap = 0.0 + 0.0j
            for i, item in enumerate(ht_circuits_cache):
                coeff = item['coeff']
                # Real Part
                data_r = results[2*i].data.meas
                val_r = (data_r.get_counts().get('0', 0) - data_r.get_counts().get('1', 0)) / data_r.num_shots
                # Imag Part
                data_i = results[2*i + 1].data.meas
                val_i = (data_i.get_counts().get('0', 0) - data_i.get_counts().get('1', 0)) / data_i.num_shots
                
                total_overlap += coeff * (val_r + 1j * val_i)
                
            term2 = abs(total_overlap)**2
            cost = term1 - term2
            
            iteration_log.append(cost)
            if len(iteration_log) % 1 == 0:
                print(f"Iter {len(iteration_log)}: Cost={cost:.6f}", end='\r')
            return cost
        return cost_func

    # 6. 최적화 실행 (Session 적용)
    if options is None: options = {}
    maxiter = options.get('maxiter', 300)
    shots = options.get('shots', 16384)
    
    # 옵티마이저 선택
    if optimizer == 'SPSA': opt_alg = SPSA(maxiter=maxiter)
    elif optimizer == 'COBYLA': opt_alg = COBYLA(maxiter=maxiter)
    else: opt_alg = COBYLA(maxiter=maxiter)

    initial_params = np.random.uniform(0, 2*np.pi, ansatz.num_parameters)
    result_qiskit = None

    # === [핵심 변경] Session 분기 처리 ===
    if backend_mode == 'real':
        print(f"\n[INFO] Opening Qiskit Runtime Session on {backend.name}...")
        # Session을 열고 그 안에서 모든 최적화 과정을 수행
        with Session(backend=backend) as session:
            # Session 모드로 Primitives 생성
            estimator = EstimatorV2(mode=session)
            sampler = SamplerV2(mode=session)
            
            estimator.options.default_shots = shots
            sampler.options.default_shots = shots
            
            # Cost Function에 세션이 연결된 Primitives 주입
            bound_cost_func = create_cost_func(estimator, sampler)
            
            # 최적화 수행 (Session이 유지되는 동안 계속 실행됨)
            result_qiskit = opt_alg.minimize(bound_cost_func, initial_params)
            
    else:
        # Local / Noiseless 모드 (Session 불필요)
        print(f"\n[INFO] Running in Local/Simulation mode (No Session)...")
        if backend_mode == 'noiseless':
            estimator = StatevectorEstimator()
            sampler = StatevectorSampler()
        else:
            # noisy_sim 등 (로컬 Aer 사용 시)
            estimator = EstimatorV2(mode=backend)
            sampler = SamplerV2(mode=backend)
            
        # 옵션 설정 (StatevectorSampler 등은 옵션 구조가 다를 수 있어 try-except)
        try:
            estimator.options.default_shots = shots
            sampler.options.default_shots = shots
        except: pass

        bound_cost_func = create_cost_func(estimator, sampler)
        result_qiskit = opt_alg.minimize(bound_cost_func, initial_params)

    print(f"\n[INFO] Optimization Finished. Final Cost: {result_qiskit.fun:.6f}")
    
    return OptimizeResult(
        x=result_qiskit.x,
        fun=result_qiskit.fun,
        nfev=result_qiskit.nfev,
        nit=result_qiskit.nit if hasattr(result_qiskit, 'nit') else maxiter
    )