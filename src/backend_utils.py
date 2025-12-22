# file: src/backend_utils.py

import os
import json
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService

try:
    from qiskit_ibm_runtime.fake_provider import FakeSherbrooke, FakeTorino, FakeBrisbane
except ImportError:
    from qiskit.providers.fake_provider import FakeSherbrooke

def load_ibm_token(filename='apikey.json'):
    """
    프로젝트 루트나 현재 폴더에서 apikey.json을 찾아 토큰을 반환합니다.
    """
    # 탐색할 경로 후보 (현재 폴더, 상위 폴더, 프로젝트 루트 등)
    search_paths = [
        filename, 
        os.path.join('..', filename),
        os.path.join(os.path.dirname(__file__), '..', '..', filename) # src/backend_utils.py 기준 루트
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    return data.get('apikey')
            except Exception as e:
                print(f"[Warning] {path} 파일을 읽는 중 오류 발생: {e}")
                return None
                
    print("[Warning] apikey.json 파일을 찾을 수 없습니다.")
    return None

def get_backend_config(mode: str, hub_info=None):
    """
    mode: 'noiseless', 'noisy_torino', 'noisy_sherbrooke', 'real'
    """
    target_backend = None
    
    if mode == 'noiseless':
        # 이상적인 시뮬레이터
        return AerSimulator(), None
        
    elif mode.startswith('noisy_'):
        # 노이즈 시뮬레이션 모드
        fake_backend = None
        
        if 'torino' in mode:
            try: fake_backend = FakeTorino()
            except: fake_backend = FakeSherbrooke()
        elif 'brisbane' in mode:
            try: fake_backend = FakeBrisbane()
            except: fake_backend = FakeSherbrooke()
        else:
            fake_backend = FakeSherbrooke()
            
        # AerSimulator로 래핑 (속도 향상)
        sim_backend = AerSimulator.from_backend(fake_backend)
        return sim_backend, fake_backend
        
    elif mode == 'real':
        token = None
        
        # 1. 인자로 직접 토큰이 넘어왔다면 사용
        if hub_info and 'token' in hub_info:
            token = hub_info['token']
        # 2. 없다면 apikey.json에서 로드
        else:
            token = load_ibm_token()
            
        if not token:
            raise ValueError("IBM Quantum Token이 필요합니다. 'apikey.json'을 생성하거나 hub_info에 토큰을 제공하세요.")

        # 서비스 연결
        try:
            # channel은 보통 'ibm_quantum' 입니다.
            service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        except Exception:
            # 이미 계정이 저장(save_account)되어 있는 경우
            service = QiskitRuntimeService(channel="ibm_quantum_platform")

        print("[INFO] Searching for the least busy real backend...")
        try:
            # 시뮬레이터가 아니고(simulator=False), 현재 작동 중인(operational=True) 기기 중 
            # 큐비트 수가 m_qubits 이상인 것(여기선 127큐비트급 권장)을 찾음
            backend = service.least_busy(operational=True, simulator=False, min_num_qubits=10)
        except Exception as e:
            # 만약 least_busy가 실패하면 계정에서 보이는 첫 번째 기기라도 잡음
            available_backends = service.backends(simulator=False, operational=True)
            if not available_backends:
                raise RuntimeError("사용 가능한 실제 양자 컴퓨터(Real Backend)가 없습니다.")
            backend = available_backends[0]
            
        print(f"[INFO] Connected to real backend: {backend.name}")
        
        # 실제 백엔드는 target과 backend 객체가 동일
        return backend, backend
        
    else:
        raise ValueError(f"Unknown mode: {mode}")