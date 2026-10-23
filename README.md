# HHL Algorithm Implementation

This repository contains an implementation of the Harrow-Hassidim-Lloyd (HHL) quantum algorithm using the Qiskit library. The code was developed to solve linear systems of equations of the form $Ax = b$ generically, without relying on hardcoded matrices.

## Main Features
* **Universal State Preparation:** The classical vector $b$ is dynamically mapped to the amplitudes of the quantum register using the `StatePreparation` class.
* **Hamiltonian Simulation (Trotterization):** The matrix $A$ is automatically decomposed into Pauli operators. The time evolution $e^{iAt}$ applied in the Quantum Phase Estimation (QPE) step is synthesized through the Suzuki-Trotter approximation, enabling the use of any sparse Hermitian matrix.
* **Dynamic Ancilla Rotation:** The circuit reads the eigenvalue spectrum in superposition from the clock register and applies multiplexed rotation gates (Multi-Controlled Y Rotations), ensuring the automatic computation of the inverse eigenvalues.

## Algorithm Structure
The code follows the standard theoretical HHL pipeline, adapted for generalization:
1. **State Preparation:** Encoding the vector $b$ into the target register.
2. **QPE (Quantum Phase Estimation):** Using a controlled `PauliEvolutionGate` to estimate the phases of the eigenvalues.
3. **Ancilla Rotation:** Iterating over the clock states to apply $\theta_k = 2 \arcsin(C/k)$ conditioned on each basis state.
4. **IQPE (Inverse QPE):** Uncomputation to disentangle the clock register from the final result.

## Technologies Used
* Python 3
* Qiskit
* NumPy
* Matplotlib (for quantum circuit rendering)
