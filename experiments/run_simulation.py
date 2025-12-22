import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.linalg as la
from qiskit import QuantumCircuit
from qiskit.circuit.library import RealAmplitudes, StatePreparation
from qiskit.quantum_info import Statevector

# 1. 경로 설정 (notebooks 폴더에서 상위 폴더인 루트를 path에 추가)
current_dir = os.getcwd()
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# 2. src 모듈 임포트
from src.ansatz import create_qaoa_ansatz
from src.problem_setup import (
    get_b_statevector,
    create_b_vector_gaussian,
    create_b_vector_sine,
    create_b_vector_uniform,
    create_b_vector_random,
    create_b_vector_linear
)
from src.decomposition import decompose_A_matrix, dict_to_operator
from src.solvers.exact import run_vqe_for_poisson as run_exact
from src.solvers.hybrid import run_vqe_hybrid_v2 as run_hybrid
from src.solvers.hardware import run_vqe_fully_hardware_v2 as run_hardware

print("✅ 라이브러리 임포트 완료")

# -----------------------------------------------------------------------------
# [유틸리티 함수]
# -----------------------------------------------------------------------------
def get_classical_solution(m: int, b_creation_func) -> np.ndarray:
    """고전적 방법(NumPy/SciPy)으로 정확한 해를 계산합니다."""
    n = 2**m
    # A 행렬 생성
    A_op = dict_to_operator(decompose_A_matrix(m), m)
    A_matrix = A_op.data 

    # b 벡터 생성 (함수 이름에 따라 파라미터 처리 단순화)
    x_grid = np.linspace(0, 1, n + 2)[1:-1]
    
    if "gaussian" in b_creation_func.__name__:
        sigma, delta = 0.2, 0.5
        b_vec = np.exp(-(x_grid - delta)**2 / (2 * sigma**2))
    elif "sine" in b_creation_func.__name__:
        b_vec = np.sin(2 * np.pi * x_grid)
    elif "uniform" in b_creation_func.__name__:
        b_vec = np.ones(n)
    elif "linear" in b_creation_func.__name__:
        b_vec = x_grid
    else:
        b_vec = b_creation_func(n)

    # Ax = b 풀기
    try:
        x_exact = la.solve(A_matrix, b_vec)
    except la.LinAlgError:
        print("[Warning] 행렬 A가 특이행렬(Singular)일 수 있습니다. Pseudo-inverse를 사용합니다.")
        x_exact = la.pinv(A_matrix) @ b_vec

    # 정규화
    norm = np.linalg.norm(x_exact)
    return x_exact / norm if norm > 0 else x_exact

def align_phase(target_vec, ref_vec):
    """
    VQE 결과(target)의 전역 위상(Global Phase)을 정답(ref)과 일치시킵니다.
    """
    overlap = np.dot(ref_vec.conj(), target_vec)
    if np.abs(overlap) < 1e-10:
        return target_vec
    phase_factor = overlap / np.abs(overlap)
    return target_vec / phase_factor

def plot_results(m, x_exact, x_vqe, fidelity, title_suffix):
    """결과 비교 그래프 출력"""
    n = 2**m
    grid = np.linspace(0, 1, n + 2)[1:-1]
    
    # 위상 정렬
    x_vqe_aligned = align_phase(x_vqe, x_exact)
    
    plt.figure(figsize=(10, 6))
    plt.plot(grid, x_exact.real, 'k-', linewidth=2, label='Exact Solution')
    plt.plot(grid, x_vqe_aligned.real, 'ro--', alpha=0.8, label=f'VQE Solution (F={fidelity:.4f})')
    
    plt.title(f"Poisson Equation Solver Results\n{title_suffix}")
    plt.xlabel("Position x")
    plt.ylabel("Normalized Amplitude u(x)")
    plt.legend()
    plt.grid(True, linestyle=':')
    plt.tight_layout()
    plt.show()

# -----------------------------------------------------------------------------
# [메인 실행 로직]
# -----------------------------------------------------------------------------
def main():
    print("="*60)
    print("       VQE Poisson Solver - Integrated Simulation Runner")
    print("="*60)
    
    # 1. 기본 설정 입력
    try:
        m_qubits = int(input("1. 큐비트 수 입력 (예: 3): "))
        layers = int(input("2. Ansatz 레이어 수 입력 (예: 4): "))
    except ValueError:
        print("잘못된 입력입니다. 숫자를 입력하세요.")
        return

    # b 함수 선택
    b_funcs = {
        '1': ('Gaussian', create_b_vector_gaussian),
        '2': ('Sine', create_b_vector_sine),
        '3': ('Uniform', create_b_vector_uniform),
        '4': ('Random', create_b_vector_random),
        '5': ('Linear', create_b_vector_linear)
    }
    print("\n3. 소스 벡터 b(x)의 형태 선택:")
    for k, v in b_funcs.items():
        print(f"  {k}: {v[0]}")
    b_choice = input("선택 (기본값 1): ")
    b_name, b_func = b_funcs.get(b_choice, b_funcs['1'])

    # Ansatz 선택
    print("\n4. Ansatz 회로 선택:")
    print("  1: RealAmplitudes (Hardware Efficient - 추천)")
    print("  2: QAOA (논문 구현)")
    ansatz_choice = input("선택 (기본값 1): ")
    
    if ansatz_choice == '2':
        ansatz = create_qaoa_ansatz(m_qubits, layers=layers)
        ansatz_name = "QAOA"
    else:
        ansatz = RealAmplitudes(m_qubits, entanglement='linear', reps=layers)
        ansatz_name = "RealAmplitudes"

    # Optimizer 선택
    print("\n5. Optimizer 선택:")
    print("  1: COBYLA (Gradient-free, 기본값)")
    print("  2: L-BFGS-B (Gradient-based, 시뮬레이션용)")
    print("  3: SLSQP (Gradient-based)")
    print("  4: Powell (Gradient-free)")
    
    opt_map = {'1': 'COBYLA', '2': 'L-BFGS-B', '3': 'SLSQP', '4': 'Powell'}
    opt_choice = input("선택 (기본값 1): ")
    optimizer_method = opt_map.get(opt_choice, 'COBYLA')
    
    try:
        max_iter = int(input(f"   -> 최대 반복 횟수 (기본값 1000): ") or 1000)
    except ValueError:
        max_iter = 1000
    
    optimizer_options = {'maxiter': max_iter, 'disp': True}

    # Solver 선택
    print("\n6. 실행 모드 (Solver) 선택:")
    print("  1: Exact Solver (행렬 연산)")
    print("  2: Hybrid Solver (EstimatorV2)")
    print("  3: Hardware Solver (SamplerV2 + Hadamard Test)")
    solver_choice = input("선택 (기본값 1): ")

    # 2. 문제 준비
    print(f"\n[INFO] Initializing Problem (n={m_qubits}, {b_name})...")
    b_vec, b_data = get_b_statevector(m_qubits, b_func)
    
    # 3. VQE 실행
    result = None
    solver_used = ""
    
    if solver_choice == '2':
        # Hybrid Solver
        print(f"[INFO] Running Hybrid Solver ({optimizer_method})...")
        result = run_hybrid(
            m_qubits, ansatz, b_vec, 
            backend_mode='noiseless',
            optimizer=optimizer_method,
            options=optimizer_options
        )
        solver_used = f"Hybrid ({optimizer_method})"
        
    elif solver_choice == '3':
        # Hardware Solver
        print(f"[INFO] Running Hardware Solver ({optimizer_method})...")
        # Hardware Solver는 b_circuit (StatePreparation) 필요
        b_circuit = QuantumCircuit(m_qubits)
        b_circuit.append(StatePreparation(b_data), range(m_qubits))
        
        result = run_hardware(
            m_qubits, ansatz, b_circuit, 
            backend_mode='noiseless',
            optimizer=optimizer_method,
            options=optimizer_options
        )
        solver_used = f"Hardware ({optimizer_method})"
        
    else: 
        # Exact Solver (Default)
        print(f"[INFO] Running Exact Solver ({optimizer_method})...")
        res_tuple = run_exact(
            m_qubits, ansatz, b_creation_func=b_func,
            optimizer=optimizer_method,
            options=optimizer_options
        )
        # Exact solver 반환값 처리 (result, norm)
        if isinstance(res_tuple, tuple):
            result = res_tuple[0]
        else:
            result = res_tuple
        solver_used = f"Exact ({optimizer_method})"

    # 4. 결과 분석
    print("\n" + "-"*40)
    print("Optimization Complete")
    print("-"*40)
    
    opt_params = result.x
    print(f"Final Cost: {result.fun:.6f}")
    
    # 결과 상태 벡터 재구성
    final_state = Statevector(ansatz.assign_parameters(opt_params))
    
    # 고전적 정답 및 Fidelity 계산
    exact_sol = get_classical_solution(m_qubits, b_func)
    fidelity = np.abs(final_state.inner(Statevector(exact_sol)))**2
    print(f"Final Fidelity: {fidelity:.6f}")
    
    # 5. 시각화
    plot_results(m_qubits, exact_sol, final_state.data, fidelity, 
                 title_suffix=f"{ansatz_name}, {solver_used}")

if __name__ == "__main__":
    main()