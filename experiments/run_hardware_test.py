# file: main_sampler_test.py

import numpy as np
import matplotlib.pyplot as plt
from qiskit.circuit.library import real_amplitudes as RealAmplitudes
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector
from scipy.sparse import diags

# 사용자 모듈
from create_b_state import get_b_statevector, create_b_vector_gaussian
from vqe_runner_sampler_v2 import run_vqe_fully_hardware_v2

def align_phase(target_vec, ref_vec):
    """
    VQE 결과(target)의 전역 위상(Global Phase)을 
    정답(ref)과 일치하도록 회전시킵니다.
    """
    # 내적 계산: <ref | target>
    overlap = np.dot(ref_vec.conj(), target_vec)
    
    # 위상 차이 추출 (overlap이 0이면 보정 불가)
    if np.abs(overlap) < 1e-10:
        return target_vec
        
    phase_factor = overlap / np.abs(overlap)
    
    # 위상 역보정: target * (1 / phase)
    # 즉, ref 방향으로 target을 회전
    aligned_vec = target_vec / phase_factor
    return aligned_vec

def get_classical_poisson_solution(n_qubits, b_vec_data):
    """고전적 해 계산 (이전과 동일)"""
    N = 2**n_qubits
    diagonals = [2 * np.ones(N), -1 * np.ones(N-1), -1 * np.ones(N-1)]
    A_mat = diags(diagonals, [0, 1, -1]).toarray()
    x_solution = np.linalg.solve(A_mat, b_vec_data)
    norm = np.linalg.norm(x_solution)
    return x_solution / norm if norm > 0 else x_solution

def plot_comparison(m_qubits, exact_sol, vqe_state_data, fidelity):
    """결과 비교 그래프 (위상 보정 적용)"""
    n = 2**m_qubits
    x_grid = np.linspace(0, 1, n + 2)[1:-1]
    
    # [핵심 수정] 위상 정렬 수행
    # VQE 결과가 복소수 위상을 가질 수 있으므로, 정답 벡터 기준으로 정렬
    aligned_vqe = align_phase(vqe_state_data, exact_sol)
    
    # 이제 실수부만 취해도 안전함
    vqe_probs = aligned_vqe.real 
    
    plt.figure(figsize=(10, 6))
    plt.plot(x_grid, exact_sol, 'k-', linewidth=2, label='Exact Solution (Classical)')
    plt.plot(x_grid, vqe_probs, 'ro--', markersize=8, label=f'VQE Solution (Fidelity={fidelity:.4f})')
    
    plt.title(f"Poisson Solver Result (Qubits={m_qubits})\nAligned Phase Plot", fontsize=14)
    plt.xlabel("Position x")
    plt.ylabel("Amplitude u(x)")
    plt.legend()
    plt.grid(True, linestyle=':')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # === 1. 실험 설정 (디버깅을 위해 3큐비트로 낮춰서 먼저 확인 추천) ===
    m_qubits = 3  # [제안] 6 -> 3으로 낮춰서 먼저 로직 검증 후 6으로 올리세요.
    print(f"=== Starting Test for {m_qubits} Qubits ===")
    
    # Ansatz: reps를 늘려 표현력을 확보
    ansatz = RealAmplitudes(m_qubits, entanglement='linear', reps=3)
    
    b_vec, _ = get_b_statevector(m_qubits, create_b_vector_gaussian)
    
    from qiskit import QuantumCircuit
    b_circuit = QuantumCircuit(m_qubits)
    b_circuit.append(StatePreparation(b_vec), range(m_qubits))
    
    # === 2. VQE 실행 ===
    # 주의: vqe_runner_sampler_v2.py 내부의 minimize options={'maxiter': 100}을
    # 직접 수정하거나, runner 함수가 maxiter를 인자로 받도록 수정해야 합니다.
    # 여기서는 runner가 실행된다고 가정합니다.
    
    print("[INFO] Running VQE... (This may take time)")
    vqe_result = run_vqe_fully_hardware_v2(
        m_qubits=m_qubits, 
        ansatz=ansatz, 
        b_circuit=b_circuit, 
        backend_mode='noisy_sim' 
    )
    
    print("\nOptimization Complete.")
    print(f"Final Cost: {vqe_result.fun:.6f}")
    
    # === 3. 결과 분석 ===
    optimal_params = vqe_result.x
    final_state = Statevector(ansatz.assign_parameters(optimal_params))
    
    # 고전적 정답
    exact_solution = get_classical_poisson_solution(m_qubits, b_vec.data.real)
    
    # Fidelity 계산
    overlap = np.dot(final_state.data.conj(), exact_solution)
    fidelity = np.abs(overlap)**2
    
    print(f"\n>>> Final Fidelity: {fidelity:.6f} <<<")
    
    # === 4. 시각화 (위상 보정 포함) ===
    plot_comparison(m_qubits, exact_solution, final_state.data, fidelity)