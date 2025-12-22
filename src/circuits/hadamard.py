from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

def create_overlap_circuit(
    b_circuit: QuantumCircuit,
    psi_ansatz: QuantumCircuit,
    pauli_op = None,
    is_imaginary: bool = False
) -> QuantumCircuit:
    """
    SamplerV2용 Hadamard Test 회로를 생성
    """
    num_qubits = psi_ansatz.num_qubits
    
    # 레지스터 설정
    qr_anc = QuantumRegister(1, 'anc')
    qr_sys = QuantumRegister(num_qubits, 'sys')
    cr = ClassicalRegister(1, 'meas') 
    
    qc = QuantumCircuit(qr_anc, qr_sys, cr) # 회로 초기화
    
    # 1. Ancilla 초기화 (Hadamard)
    qc.h(qr_anc[0])
    
    # 허수부 측정 시 위상 조정 (S_dagger)
    if is_imaginary:
        qc.sdg(qr_anc[0])

    # 2. 제어된 |b> 상태 준비 (Branch 0: Control state 0)
    if b_circuit is not None:
        try:
            # 일단 직접 게이트 변환
            c_b = b_circuit.to_gate().control(1, ctrl_state=0)
        except:
            # 실패 시: decompose 후 변환
            c_b = b_circuit.decompose().to_gate().control(1, ctrl_state=0)
            
        qc.append(c_b, [qr_anc[0]] + list(qr_sys))

    # 3. 제어된 P|ψ> 상태 준비 (Branch 1: Control state 1)
    
    # 3-1. |ψ> 부분 
    try:
        c_psi = psi_ansatz.to_gate().control(1, ctrl_state=1)
    except:
        # 파라미터 벡터 매칭 오류 발생 시 decompose()로 해결
        c_psi = psi_ansatz.decompose().to_gate().control(1, ctrl_state=1)
        
    qc.append(c_psi, [qr_anc[0]] + list(qr_sys))
    
    # 3-2. Pauli P 부분 (Control-state 1)
    if pauli_op is not None:
        pauli_str = str(pauli_op)
        for i, p_char in enumerate(reversed(pauli_str)):
            target_qubit = qr_sys[i]
            if p_char == 'X':
                qc.cx(qr_anc[0], target_qubit)
            elif p_char == 'Y':
                qc.cy(qr_anc[0], target_qubit)
            elif p_char == 'Z':
                qc.cz(qr_anc[0], target_qubit)

    # 4. Ancilla 닫기 (Hadamard)
    qc.h(qr_anc[0])
    
    # 5. 측정
    qc.measure(qr_anc[0], cr[0])
    
    return qc