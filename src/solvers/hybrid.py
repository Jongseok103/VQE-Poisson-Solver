import numpy as np
from scipy.optimize import minimize
from qiskit.primitives import StatevectorEstimator
from qiskit_ibm_runtime import EstimatorV2, EstimatorOptions
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.quantum_info import Statevector

# [수정된 부분] src 패키지 경로로 변경
from src.decomposition import decompose_A_matrix, decompose_B_matrix, decompose_C_matrix, dict_to_sparse_pauli
# backend_manager -> backend_utils로 변경
from src.backend_utils import get_backend_config

def run_vqe_hybrid_v2(m_qubits, ansatz, b_vec, backend_mode='noiseless', hub_info=None, optimizer='COBYLA', options=None):
    """
    EstimatorV2를 사용하여 하드웨어 친화적으로 VQE를 실행합니다.
    """
    # 1. Backend 설정
    backend, target_backend = get_backend_config(backend_mode, hub_info)
    
    print(f"[INFO] Running on backend: {backend.name} (Mode: {backend_mode})")

    # 2. 연산자 생성 (SparsePauliOp)
    # A^2 = B - C
    B_dict = decompose_B_matrix(m_qubits)
    C_dict = decompose_C_matrix(m_qubits)
    A2_dict = {**B_dict}
    for k, v in C_dict.items():
        A2_dict[k] = A2_dict.get(k, 0) - v
    
    A2_op = dict_to_sparse_pauli(A2_dict, m_qubits)
    A_op = dict_to_sparse_pauli(decompose_A_matrix(m_qubits), m_qubits)

    # 3. Transpilation (ISA Circuit 변환)
    # V2 Primitives는 타겟 백엔드의 ISA(Instruction Set Architecture)를 준수하는 회로만 받습니다.
    if target_backend is not None:
        pm = generate_preset_pass_manager(target=target_backend.target, optimization_level=3)
        ansatz_isa = pm.run(ansatz)
        A2_op_isa = A2_op.apply_layout(ansatz_isa.layout) # Observable도 레이아웃 적용 필요
    else:
        ansatz_isa = ansatz
        A2_op_isa = A2_op

    # 4. Estimator 초기화
    if backend_mode == 'noiseless':
        estimator = StatevectorEstimator()
    else:
        # AerSimulator 또는 Real Backend 사용 시 EstimatorV2
        estimator = EstimatorV2(mode=backend)
        # 샷 수 설정 (precision control)
        estimator.options.default_shots = 4096

    # 5. 비용 함수 정의
    iteration_log = []

    def cost_func(params):
        # [Term 1] <ψ|A^2|ψ> via EstimatorV2
        # PUBs 형식: (circuit, observable, parameter_values)
        pub = (ansatz_isa, A2_op_isa, params)
        job = estimator.run([pub])
        result = job.result()[0]
        term1 = float(result.data.evs) # 기댓값
        
        # [Term 2] |<b|A|ψ>|^2
        # 하드웨어에서 Hadamard Test를 수행하는 것은 깊이가 깊어지므로,
        # 여기서는 '하이브리드' 방식으로 Statevector 계산을 수행합니다.
        # (노이즈 시뮬레이션 시에는 이 부분도 노이즈 없이 계산됨에 유의 - Semi-simulation)
        
        # *주의*: ansatz_isa는 레이아웃이 적용되어 있어 Statevector 계산 시 주의 필요
        # 순수 시뮬레이션용 원본 ansatz 사용
        sv = Statevector(ansatz.assign_parameters(params))
        evolved_sv = sv.evolve(A_op) # A|ψ>
        term2 = np.abs(b_vec.inner(evolved_sv))**2
        
        cost = term1 - term2
        
        # 로깅
        iteration_log.append(cost)
        print(f"Iter {len(iteration_log)}: Cost={cost:.6f} (<A^2>={term1:.4f}, Overlap={term2:.4f})", end='\r')
        
        return cost

    # 6. 최적화 실행
    print(f"\n[INFO] Starting Optimization with {optimizer}...")
    initial_params = np.random.uniform(0, 2*np.pi, ansatz.num_parameters)

    if options is None:
        options = {'maxiter': 3000}

    res = minimize(cost_func, initial_params, method=optimizer, options=options) 
       
    return res