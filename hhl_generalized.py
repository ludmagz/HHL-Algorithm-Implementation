import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import StatePreparation, PauliEvolutionGate, QFTGate
from qiskit.quantum_info import SparsePauliOp
from qiskit.synthesis import SuzukiTrotter

# Classical definition of the matrix A and vector b
A = np.array([[1, -1/3], 
              [-1/3, 1]])
b = np.array([0, 1])

# Normalization of the vector b so that it can be used in the quantum circuit
b_norm = np.linalg.norm(b)
b_normalized = b / b_norm

# Dinamically determine the number of qubits needed for the registers based on the size of b
nB = int(np.ceil(np.log2(len(b))))
nC = 2  # Futurely scalable, but for now I'll keep it fixed
nA = 1

ancilla = QuantumRegister(nA, name='Ancilla')
c_reg = QuantumRegister(nC, name='Clock Qubits')
b_reg = QuantumRegister(nB, name='B Register')
# It should be able do handle the number of qubits in b and ancilla, so nB + nA
x_classic = ClassicalRegister(nB + nA, name='Classical Register')

qc = QuantumCircuit(ancilla, c_reg, b_reg, x_classic)

# Generically prepare the state |b> in the b register using StatePreparation
prep_estado = StatePreparation(b_normalized)
qc.append(prep_estado, b_reg)



# =============== Quantum Phase Estimation ===============

# Generaalizing the QPE step using PauliEvolutionGate and SuzukiTrotter for the matrix A

# Applying Hadamard gates to the clock qubits
qc.h(c_reg)

# Decomposition of the matrix A into Pauli operators
pauli_op = SparsePauliOp.from_operator(A)

# Base time for the evolution defined on the article
# It can be adjusted based on the problem
t = 3 * np.pi / 4

# Dynamically apply the controlled evolution gates based on the number of clock qubits
for i in range(nC):

    # The time for evolution is scaled by 2^i for each clock qubit
    '''This happens because the parameter t determines de amount of phase that will be encoded in the clock qubits. 
    The first clock qubit (LSB) will encode the phase for U^1, the second clock qubit (MSB) will encode the phase for U^2, and so on.
    Coding the phase in this way allows us to extract the eigenvalues of A in binary form, which is essential for the HHL algorithm.'''
    evolution_time = t * (2 ** i)
    
    # Create the PauliEvolutionGate for the matrix A and the scaled time
    evol_gate = PauliEvolutionGate(pauli_op, time=evolution_time)
    
    # Sinthesize the evolution gate using Suzuki-Trotter decomposition
    # For more complex matrices, the order and reps can be adjusted for better accuracy
    trotter_circuit = SuzukiTrotter(order=1, reps=1).synthesize(evol_gate)
    
    # Convert the synthesized circuit into a controlled gate
    # The clock qubit c_reg[i] will control the evolution of the b register 
    controled_gate = trotter_circuit.to_gate(label=f'U^{2**i}').control(1)
    
    # Add our controlled gate to the circuit
    qc.append(controled_gate, [c_reg[i]] + b_reg[:])

# =============== IQFT ===============

# Construct the IQFT for the clock qubits and applies it to the circuit
iqft_gate = QFTGate(num_qubits=nC).inverse()
qc.append(iqft_gate, c_reg)




print("Quantum Circuit for HHL Algorithm:")
qc.draw('mpl')
plt.show()