# ⚛️ VQE Poisson Solver (Qiskit V2 Primitives)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.0%2B-purple)](https://qiskit.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

이 프로젝트는 **1차원 푸아송 방정식(1D Poisson Equation)**, $Ax=b$를 양자 컴퓨터를 사용하여 풀기 위한 **변분 양자 알고리즘(VQE)** 구현체입니다.

최신 **IBM Qiskit Runtime Primitives V2 (EstimatorV2, SamplerV2)**를 기반으로 작성되었으며, 단순한 상태 벡터(Statevector) 시뮬레이션에 그치지 않고 **Hadamard Test** 회로를 직접 구현하여 실제 양자 하드웨어(QPU)에서도 실행 가능한 **하드웨어 호환(Hardware Compatible)** 구조를 갖추고 있습니다.

---

## 📌 주요 특징 (Key Features)

* **하드웨어 호환성 (Hardware Compatible):** `SamplerV2`와 **Hadamard Test** 회로를 통해 비용 함수(Cost Function)의 Overlap 항($|\langle b | \psi(\theta) \rangle|^2$)을 계산합니다. 이를 통해 시뮬레이터뿐만 아니라 실제 양자 컴퓨터에서도 실행이 가능합니다.
* **최신 Qiskit 기술 스택:** IBM Quantum의 최신 인터페이스인 `EstimatorV2`와 `SamplerV2`를 활용하여 실행 속도와 에러 완화(Error Mitigation) 효율을 최적화했습니다.
* **단계별 솔버 (Modular Solvers):** 연구 및 검증 목적에 따라 세 가지 모드를 지원합니다.
    1.  **Exact Solver:** 행렬 연산을 통한 이론적 정답 검증 (Ground Truth)
    2.  **Hybrid Solver:** `EstimatorV2` + Statevector 연산을 결합한 고속 시뮬레이션
    3.  **Hardware Solver:** `SamplerV2` + Hadamard Test 회로를 이용한 완전한 하드웨어 방식
* **유연한 실험 환경:**
    * **Ansatz:** 논문 기반의 **QAOA** 및 하드웨어 효율적인 **RealAmplitudes** 지원
    * **Optimizer:** COBYLA, Powell, L-BFGS-B, SPSA 등 다양한 최적화 알고리즘 비교 가능
    * **Scalability:** 2~6 큐비트 규모 및 레이어 깊이에 따른 Fidelity 변화 벤치마킹

---

## 🛠️ 환경 및 의존성 (Environment & Dependencies)

이 프로젝트는 **Qiskit 2.0** 및 **Numpy 2.0** 기반의 최신 환경에서 테스트되었습니다. 주요 라이브러리 버전은 다음과 같습니다.

| Package | Version | Description |
| :--- | :--- | :--- |
| **Python** | `3.10+` | 권장 실행 환경 |
| **Qiskit** | `2.2.3` | Core SDK (V2 Primitives 지원) |
| **Qiskit IBM Runtime** | `0.43.1` | Cloud execution services |
| **Numpy** | `2.3.4` | 수치 해석 및 행렬 연산 |
| **Scipy** | `1.16.3` | 최적화(Optimizer) 알고리즘 |

전체 의존성 목록은 `requirements.txt`에 포함되어 있습니다.

---

## 📂 디렉토리 구조 (Directory Structure)

```bash
VQE-Poisson-Solver/
├── src/
│   ├── circuits/        # 양자 회로 모듈 (Hadamard Test 등)
│   ├── solvers/         # VQE 솔버 구현 (Exact, Hybrid, Hardware)
│   ├── ansatz.py        # QAOA 및 RealAmplitudes 생성
│   ├── decomposition.py # 파울리 연산자(Pauli Operator) 분해
│   ├── problem_setup.py # 문제 정의 (b 벡터 생성 등)
│   └── backend_utils.py # IBM Quantum 백엔드 연결 유틸리티
├── experiments/
│   └── run_simulation.py # 터미널 기반 통합 실행 스크립트 (CLI)
├── notebooks/           # 분석 및 시각화를 위한 주피터 노트북
│   ├── backend_check.ipynb       # IBM Quantum 백엔드 상태 확인
│   ├── noise_simulation.ipynb    # 노이즈 환경(FakeBackend)에서의 성능 테스트
│   ├── noiseless_simulation.ipynb # 이상적(Noiseless) 환경에서의 성능 테스트
│   ├── playground.ipynb          # 기능 단위 테스트 및 자유 실험 공간
│   └── scalability_benchmark.ipynb # 큐비트/레이어 확장에 따른 벤치마크
├── requirements.txt     # 패키지 설치 목록
├── apikey.json          # IBM Quantum API Token (GitIgnored)
└── README.md

```

---

## 🚀 설치 및 시작하기 (Getting Started)

### 1. 환경 설정

저장소를 클론하고 필요한 라이브러리를 설치합니다.

```bash
git clone [https://github.com/YourID/VQE-Poisson-Solver.git](https://github.com/YourID/VQE-Poisson-Solver.git)
cd VQE-Poisson-Solver
pip install -r requirements.txt

```

### 2. IBM Quantum API 설정 (선택 사항)

실제 양자 컴퓨터(Real Backend)를 사용하려면 루트 디렉토리에 `apikey.json` 파일을 생성해야 합니다.

```json
{
    "apikey": "YOUR_IBM_QUANTUM_TOKEN_HERE"
}

```

*(주의: 이 파일은 보안을 위해 절대 GitHub에 업로드하지 마세요. .gitignore에 포함되어 있습니다.)*

---

## 💻 사용 방법 (Usage)

### 1. 대화형 시뮬레이션 실행 (CLI)

터미널에서 통합 스크립트를 실행하여 큐비트 수, Ansatz, Optimizer 등을 선택해 시뮬레이션을 진행할 수 있습니다.

```bash
python experiments/run_simulation.py

```

### 2. 주피터 노트북 활용 (Jupyter Notebooks)

`notebooks/` 폴더에서 다양한 시나리오의 실험을 수행할 수 있습니다.

* **`playground.ipynb`**: 솔버, Ansatz, Optimizer 조합을 자유롭게 변경하며 테스트하고 결과를 시각화합니다.
* **`scalability_benchmark.ipynb`**: 큐비트 수(2~6)와 레이어 깊이 증가에 따른 Fidelity와 실행 시간을 분석합니다.
* **`noiseless_simulation.ipynb`**: 노이즈가 없는 이상적인 환경에서 알고리즘의 이론적 성능을 검증합니다.
* **`noise_simulation.ipynb`**: 실제 하드웨어와 유사한 노이즈 환경(FakeBackend)에서 알고리즘의 견고성(Robustness)을 테스트합니다.
* **`backend_check.ipynb`**: 사용 가능한 IBM Quantum 백엔드 리스트와 대기열 상태를 확인합니다.

---

## 📊 실험 결과 (Results)

본 프로젝트를 통해 2~6 큐비트 규모에서 VQE가 1차원 푸아송 방정식의 해를 높은 정확도(Fidelity > 0.99, Noiseless 기준)로 찾아냄을 확인했습니다.

* **정확도 (Accuracy):** 적절한 깊이의 회로를 사용할 경우, 이상적인 환경에서 99% 이상의 Fidelity를 달성했습니다.
* **확장성 (Scalability):** 큐비트 수가 증가하여 탐색 공간()이 커지더라도, QAOA 레이어()를 증가시킴으로써 해의 표현력(Expressibility)을 회복하고 높은 정확도를 유지할 수 있음을 확인했습니다.

---

## 👤 Author

**Jongseok**

* Undergraduate Research Student at Institute for Quantum Information Processing and Systems
* Dual Major in Physics & Artificial Intelligence
* **GitHub:** [YourProfile](https://www.google.com/search?q=https://github.com/Jongseok103)



---
