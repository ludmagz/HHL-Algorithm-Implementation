# HHL Algorithm Implementation

This repository contains an implementation of the Harrow-Hassidim-Lloyd (HHL) quantum algorithm using the Qiskit library. The code was developed to solve linear systems of equations of the form $Ax = b$ generically, without relying on hardcoded matrices.

## Main Features
- **Dynamic Register Sizing:** The number of target qubits (`nB`) is automatically allocated based on the dimension of the input vector $b$.
- **Universal State Preparation:** The classical vector $b$ is dynamically mapped to the amplitudes of the quantum register using the `StatePreparation` class.
- **Dynamic Phase Scaling:** The evolution time parameter $t$ is dynamically computed as $t = \pi / \lambda_{max}$ prior to execution to prevent phase overflow within the clock register.
- **Hamiltonian Simulation (Trotterization):** The matrix $A$ is automatically decomposed into Pauli operators. The time evolution $e^{iAt}$ applied in the Quantum Phase Estimation (QPE) step is synthesized through the Suzuki-Trotter approximation, enabling the use of any sparse Hermitian matrix.
- **Dynamic Ancilla Rotation:** The circuit reads the eigenvalue spectrum in superposition from the clock register and applies multiplexed rotation gates (Multi-Controlled Y Rotations), isolating specific basis states using X-gates to compute the inverse eigenvalues.
- **Dynamic Measurement Pipeline:** The classical measurement loop automatically scales to read variable-sized target registers, ensuring correct positional mapping of the success-flagged ancilla bit.

## Algorithm Structure
The code follows the standard theoretical HHL pipeline, adapted for complete generalization:
1. **State Preparation:** Encoding the vector $b$ into the target register.
2. **QPE (Quantum Phase Estimation):** Using a controlled `PauliEvolutionGate` and QFT to estimate the phases of the eigenvalues.
3. **Ancilla Rotation:** Iterating over the clock states to apply $\theta_k = 2 \arcsin(C/k)$ conditioned on each basis state.
4. **IQPE (Inverse QPE):** Uncomputation via reversed time evolution (negative $t$) and inverse QFT to disentangle the clock register from the final result.
5. **Measurement:** Collapsing the ancilla to filter for successful rotations (state $|1\rangle$) and reading the target register to observe the proportional solution $|x\rangle$.

## Current Limitations & Trade-offs
- **Clock Register Size (`nC`):** Currently set to `nC = 2`. While this perfectly solves matrices whose eigenvalues form exact binary proportions (e.g., 1:2 or 1:4), applying it to matrices with continuous eigenvalues causes phase leakage and rounding errors. Dynamically deriving `nC = ceil(log2(kappa / epsilon))` is mathematically ideal but heavily increases circuit depth and multi-controlled gate complexity, bottlenecking standard local simulators.

## Technologies Used
- Python 3
- Qiskit
- NumPy
- Matplotlib (for quantum circuit rendering)
