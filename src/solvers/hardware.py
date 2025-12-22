import numpy as np
from scipy.optimize import minimize

# Qiskit Primitives (V2 & Statevector)
from qiskit.primitives import StatevectorEstimator, StatevectorSampler
from qiskit_ibm_runtime import EstimatorV2, SamplerV2
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

# 사용자 정의 모듈
from src.decomposition import decompose_B_matrix, decompose_C_matrix, dict_to_sparse_pauli, decompose_A_matrix
from src.circuits.hadamard import create_overlap_circuit
from src.backend_utils import get_backend_config

def run_vqe_fully_hardware_v2(m_qubits, ansatz, b_circuit, backend_mode='noiseless', hub_info=None, optimizer='COBYLA', options=None):
    """
    SamplerV2와 EstimatorV2를 사용하여, 논문의 두 항을 모두 하드웨어 호환 방식으로 계산합니다.
    backend_mode에 따라 시뮬레이터 또는 실제 하드웨어를 선택하고, 회로를 트랜스파일합니다.
    """
    
    # 1. Backend 및 Primitives 설정
    print(f"[INFO] Setting up backend for mode: {backend_mode}")
    backend, target_backend = get_backend_config(backend_mode, hub_info)
    
    pass_manager = None
    
    if backend_mode == 'noiseless':
        # 이상적인 시뮬레이션
        estimator = StatevectorEstimator()
        sampler = StatevectorSampler()
    else:
        # 노이즈 시뮬레이션 또는 리얼 하드웨어 (V2 Primitives 사용)
        print(f"[INFO] Using V2 Primitives on backend: {backend.name}")
        estimator = EstimatorV2(mode=backend)
        sampler = SamplerV2(mode=backend)
        
        # 샷 수 설정 (필요시 조정)
        estimator.options.default_shots = 16384 * 2
        sampler.options.default_shots = 16384 * 2
        
        # Transpilation을 위한 PassManager 생성
        if target_backend is not None:
            pass_manager = generate_preset_pass_manager(target=target_backend.target, optimization_level=3)

    # 2. 연산자 생성 (SparsePauliOp)
    # Term 1용: A^2 = B - C
    B_dict = decompose_B_matrix(m_qubits)
    C_dict = decompose_C_matrix(m_qubits)
    A2_dict = {**B_dict}
    for k, v in C_dict.items():
        A2_dict[k] = A2_dict.get(k, 0) - v
    A2_op = dict_to_sparse_pauli(A2_dict, m_qubits)
    
    # Term 2용: A (Pauli 분해)
    A_dict = decompose_A_matrix(m_qubits)
    A_op = dict_to_sparse_pauli(A_dict, m_qubits)
    
    # 3. 회로 Transpilation (ISA Circuit 변환)
    # Term 1용 Ansatz 변환
    if pass_manager is not None:
        ansatz_isa = pass_manager.run(ansatz)
        # Observable도 ISA 회로의 레이아웃에 맞춰 변환해야 함
        try:
            A2_op_isa = A2_op.apply_layout(ansatz_isa.layout)
        except Exception:
            # 레이아웃 적용이 불가능하거나 이미 적용된 경우 원본 사용
            A2_op_isa = A2_op
    else:
        ansatz_isa = ansatz
        A2_op_isa = A2_op

    # 4. [최적화] Hadamard Test 회로 미리 생성 및 캐싱
    # Term 2 계산을 위한 회로들을 미리 만들고, 필요하면 Transpile까지 수행해 둡니다.
    print("[INFO] Generating and transpiling Hadamard test circuits...")
    ht_circuits_cache = [] # list of (coeff, circuit_real, circuit_imag)
    
    for i, pauli in enumerate(A_op.paulis):
        coeff = A_op.coeffs[i]
        
        # 회로 생성
        qc_r = create_overlap_circuit(b_circuit, ansatz, pauli, is_imaginary=False)
        qc_i = create_overlap_circuit(b_circuit, ansatz, pauli, is_imaginary=True)
        
        # 하드웨어 모드일 경우 Transpilation 수행
        if pass_manager is not None:
            qc_r = pass_manager.run(qc_r)
            qc_i = pass_manager.run(qc_i)
            
        ht_circuits_cache.append({'coeff': coeff, 'real': qc_r, 'imag': qc_i})
        
    iteration_log = []

    def cost_func(params):
        # === [Term 1] <ψ|A^2|ψ> (Estimator) ===
        # PUB: (circuit, observable, params)
        pub_est = (ansatz_isa, A2_op_isa, params)
        job_est = estimator.run([pub_est])
        # V2 결과 처리: result[0].data.evs (배열 형태일 수 있으므로 float 변환)
        term1 = float(job_est.result()[0].data.evs)
        
        # === [Term 2] |<b|A|ψ>|^2 (Sampler Batch Execution) ===
        # 모든 Pauli 항에 대한 회로를 하나의 배치로 묶어서 실행
        sampler_pubs = []
        
        # 순서대로 PUB 생성: [(qc_real, params), (qc_imag, params), ...]
        for item in ht_circuits_cache:
            sampler_pubs.append((item['real'], params))
            sampler_pubs.append((item['imag'], params))
            
        # 일괄 실행 (Batch Run)
        job_sam = sampler.run(sampler_pubs)
        results = job_sam.result()
        
        # 결과 취합 및 Overlap 계산
        total_overlap = 0.0 + 0.0j
        
        # 결과 리스트 인덱싱 (2개씩 짝지음)
        for i, item in enumerate(ht_circuits_cache):
            coeff = item['coeff']
            
            # Real Part 결과 처리
            # V2 Result: data.meas.get_counts() 사용
            # (레지스터 이름이 'meas'라고 가정 - hadamard.py에서 설정함)
            
            # Real part
            counts_r = results[2*i].data.meas.get_counts()
            shots_r = sum(counts_r.values())
            # P(0) - P(1)
            val_r = (counts_r.get('0', 0) - counts_r.get('1', 0)) / shots_r
            
            # Imag Part
            counts_i = results[2*i + 1].data.meas.get_counts()
            shots_i = sum(counts_i.values())
            val_i = (counts_i.get('0', 0) - counts_i.get('1', 0)) / shots_i
            
            # 복소수 합산: coeff * (Re + i*Im)
            # Hadamard Test의 결과값(val_r, val_i)은 그 자체로 실수부/허수부 측정값임
            total_overlap += coeff * (val_r + 1j * val_i)
            
        term2 = abs(total_overlap)**2
        
        cost = term1 - term2
        
        iteration_log.append(cost)
        print(f"Iter {len(iteration_log)}: Cost={cost:.6f} (<A^2>={term1:.4f}, Overlap={term2:.4f})", end='\r')
        
        return cost

    # 최적화 실행
    print(f"[INFO] Starting VQE Optimization ({optimizer}, Backend: {backend_mode})...")
    initial_params = np.random.uniform(0, 2*np.pi, ansatz.num_parameters)
    
    if options is None:
        options = {'maxiter': 3000 if backend_mode == 'noiseless' else 1000, 'tol': 1e-4}
    
    res = minimize(cost_func, initial_params, method=optimizer, options=options)
    
    return res