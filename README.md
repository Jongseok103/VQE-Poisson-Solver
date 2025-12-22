# ⚛️ VQE Poisson Solver (Qiskit V2 Primitives)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![Qiskit](https://img.shields.io/badge/Qiskit-2.0%2B-purple)](https://qiskit.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2012.07014-B31B1B?style=flat&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2012.07014)

This project implements a **Variational Quantum Eigensolver (VQE)** to solve the **1D Poisson Equation** ($Ax=b$) using quantum computers.

Built upon the latest **IBM Qiskit Runtime Primitives V2 (EstimatorV2, SamplerV2)**, this solver is designed for **hardware compatibility**. It implements the **Hadamard Test** circuit to calculate the overlap term ($|\langle b | \psi(\theta) \rangle|^2$) of the cost function, enabling execution on real quantum processing units (QPUs) rather than relying solely on statevector simulations.

---

## 📌 Key Features

* **Hardware Compatible:** Unlike traditional statevector simulations, this project calculates the cost function using the **Hadamard Test** via `SamplerV2`, making it deployable on real quantum hardware.
* **Modern Qiskit Stack:** Utilizes IBM's latest `EstimatorV2` and `SamplerV2` primitives for optimized execution speed and error mitigation.
* **Modular Solvers:** Three distinct solvers are provided for step-by-step verification:
    1.  **Exact Solver:** Matrix-based validation for theoretical ground truth.
    2.  **Hybrid Solver:** Fast simulation using `EstimatorV2` combined with statevector logic.
    3.  **Hardware Solver:** Fully circuit-based approach using `SamplerV2` and Hadamard Tests.
* **Flexible Experimentation:**
    * **Ansatz:** Supports **QAOA** and Hardware-efficient **RealAmplitudes**.
    * **Optimizers:** Compatible with COBYLA, Powell, L-BFGS-B, and SPSA.
    * **Scalability:** Benchmarking tools for analyzing Fidelity across different qubit counts (2-6 qubits) and circuit depths.

---

## 🛠️ Environment & Dependencies

This project is built and tested on **Qiskit 2.0** and **Numpy 2.0**. Key dependencies include:

| Package | Version | Description |
| :--- | :--- | :--- |
| **Python** | `3.10+` | Recommended environment |
| **Qiskit** | `2.2.3` | Core SDK (V2 Primitives) |
| **Qiskit IBM Runtime** | `0.43.1` | Cloud execution services |
| **Numpy** | `2.3.4` | Numerical computing |
| **Scipy** | `1.16.3` | Optimization algorithms |

A complete list of dependencies is provided in `requirements.txt`.

---

## 📂 Directory Structure

```bash
VQE-Poisson-Solver/
├── src/
│   ├── circuits/        # Quantum circuits (e.g., Hadamard Test)
│   ├── solvers/         # VQE Implementations (Exact, Hybrid, Hardware)
│   ├── ansatz.py        # QAOA and RealAmplitudes generation
│   ├── decomposition.py # Pauli Operator decomposition
│   ├── problem_setup.py # Problem definition (Vector b generation)
│   └── backend_utils.py # IBM Quantum backend connection utilities
├── experiments/
│   └── run_simulation.py # CLI-based integrated simulation runner
├── notebooks/           # Jupyter Notebooks for analysis
│   ├── backend_check.ipynb
│   ├── noise_simulation.ipynb
│   ├── noiseless_simulation.ipynb
│   ├── playground.ipynb
│   └── scalability_benchmark.ipynb
├── requirements.txt     # Python dependencies
├── apikey.json          # IBM Quantum API Token (GitIgnored)
└── README.md

```

---

## 🚀 Getting Started

### 1. Installation

Clone the repository and install the required packages.

```bash
git clone [https://github.com/YourID/VQE-Poisson-Solver.git](https://github.com/YourID/VQE-Poisson-Solver.git)
cd VQE-Poisson-Solver
pip install -r requirements.txt

```

### 2. IBM Quantum Setup (Optional)

To run experiments on real quantum hardware, create an `apikey.json` file in the root directory:

```json
{
    "apikey": "YOUR_IBM_QUANTUM_TOKEN_HERE"
}

```

*(Note: Ensure this file is added to .gitignore for security.)*

---

## 💻 Usage

### 1. Interactive Simulation (CLI)

Run the integrated simulation script to select solvers, ansatz, and optimizers interactively:

```bash
python experiments/run_simulation.py

```

### 2. Jupyter Notebooks

Detailed analysis and benchmarking can be found in the `notebooks/` directory:

* **`playground.ipynb`**: General testing area for verifying different solvers and visualizing results.
* **`scalability_benchmark.ipynb`**: Analyzes Fidelity and execution time as qubit counts (2-6) and layer depths increase.
* **`noiseless_simulation.ipynb`**: Ideal VQE performance tests without noise models.
* **`noise_simulation.ipynb`**: VQE performance tests under noisy conditions (using FakeBackends or Noisy Simulators).
* **`backend_check.ipynb`**: Utility to check available IBM Quantum backends and account status.

---

## 📊 Results

The VQE solver demonstrates high accuracy in solving the Poisson equation for small-scale systems (2-6 qubits).

* **Accuracy:** Achieves Fidelity > 0.99 in noiseless environments with appropriate circuit depth.
* **Scalability:** As the system size () increases, increasing the QAOA layer depth () effectively recovers Fidelity, demonstrating the expressibility of the ansatz.

| **Qubit Scalability** | **Layer Depth Analysis** |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/06d40068-00f3-4641-8907-06ce7412a491" width="100%"> | <img src="https://github.com/user-attachments/assets/819c360b-1a94-4bcf-89cc-eb3b8a55319f" width="100%"> |
| Fidelity changes with increasing number of qubits | Improve performance with layer (p) depth |


## 📜 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).

---

## 👤 Author

**Jongseok**

* Undergraduate Researcher in Institute of Quantum Information Processing and Systems (University of Seoul)
* Dual Major in Physics & Artificial Intelligence
* Email: sjs981212@naver.com
* **GitHub:** [YourProfile](https://www.google.com/search?q=https://github.com/Jongsek103)

