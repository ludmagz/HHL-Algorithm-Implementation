import numpy as np
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import StatePreparation, PauliEvolutionGate, QFTGate, RYGate
from qiskit.quantum_info import SparsePauliOp
from qiskit.synthesis import SuzukiTrotter
from qiskit_aer import AerSimulator
from qiskit import transpile

# Classical definition of the matrix A and vector b
#A = np.array([[1, -1/3], 
              #[-1/3, 1]])
#b = np.array([0, 1])

A = np.array([[2, 0, 0, 0],
              [0, 2, 0, 0],
              [0, 0, 1, 0],
              [0, 0, 0, 1]])
b = np.array([1, 0, 0, 1])

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

# Extract the eigenvalues of A 
eigenvalues = np.linalg.eigvals(A)

# Defines the maximum eigenvalue to scale the evolution time t, ensuring that the phase encoded in the clock qubits is within [0, 2π]
lambda_max = np.max(np.abs(eigenvalues))
t = np.pi / lambda_max

# Dynamically apply the controlled evolution gates based on the number of clock qubits
for i in range(nC):

    # The time for evolution is scaled by 2^i for each clock qubit
    '''This happens because the parameter t determines de amount of phase that will be encoded in the clock qubits. 
    The first clock qubit (LSB) will encode the phase for U^1, the second clock qubit (MSB) will encode the phase for U^2, and so on.
    Coding the phase in this way allows us to extract the eigenvalues of A in binary form, which is essential for the HHL algorithm.'''
    evolution_time = t * (2 ** i)
    
    # Create the PauliEvolutionGate for the matrix A and the scaled time
    evol_gate = PauliEvolutionGate(pauli_op, time=-evolution_time)
    
    '''
    Synthesizes continuous quantum time evolution into a discrete, executable circuit.
    Since Hamiltonian terms (Pauli operators) often do not commute, e^{i(X+Z)t} != e^{iXt}e^{iZt}.
    Suzuki-Trotter solves this by slicing the total evolution time into smaller steps ('reps').
    It applies the operators sequentially in small fractions of time. The 'order' parameter 
    symmetrically arranges these slices to minimize commutation errors, translating the abstract 
    PauliEvolutionGate into concrete, native quantum gates (Rx, Rz, CNOTs).
    '''
    # For more complex matrices, the order and reps can be adjusted for better accuracy
    trotter_circuit = SuzukiTrotter(order=1, reps=1).synthesize(evol_gate)
    
    # Convert the synthesized circuit into a controlled gate
    # The clock qubit c_reg[i] will control the evolution of the b register 
    controled_gate = trotter_circuit.to_gate(label=f'U^{2**i}').control(1)
    
    # Add our controlled gate to the circuit
    qc.append(controled_gate, [c_reg[i]] + b_reg[:])

# =============== IQFT ===============

'''
OBJECTIVE OF IQFT: 
Transforms the phases encoded in the superposition of the clock qubits into a 
readable binary representation of the eigenvalues. Through constructive and 
destructive interference, it extracts the hidden phase information and writes 
it explicitly into the computational basis states of the clock register.
'''

# Construct the IQFT for the clock qubits and applies it to the circuit
iqft_gate = QFTGate(num_qubits=nC).inverse()
qc.append(iqft_gate, c_reg)


# =============== Ancilla Rotation ===============

'''
ANCILLA ROTATION THEORY + OBJECTIVE:
Objective: Transfer the inverse of the eigenvalues (1/λ) into the probability 
amplitude of the ancilla's |1> state. 
Theory: By applying a targeted rotation of θ = 2 * arcsin(C/λ), we condition 
the amplitudes. If the ancilla is later measured as |1>, the system collapses 
into a state proportional to A^-1|b>, effectively solving the linear system.
'''

# Constant C ensures the probability amplitude remains valid (C/k <= 1)
C = 1.0
num_clock_states = 2 ** nC

# For each possible clock state, we calculate the corresponding rotation angle for the ancilla
for k in range(1, num_clock_states):

    '''
    A multi-controlled RY gate natively triggers only when all control qubits are |1>. 
    To apply the specific rotation for a clock state containing |0> bits (e.g., |01>), we temporarily 
    flip those '0' bits to '1' using X gates. This forces our target state to match  the |11...1> 
    activation condition of the controlled gate, isolating the rotation to only that specific state. 
    After the RY rotation is applied to the ancilla, the X gates are applied a second time to 
    uncompute the bit flips. This perfectly restores the original clock state, preserving the 
    quantum superposition necessary for the upcoming Inverse Quantum Phase Estimation (IQPE).
    '''

    theta_k = 2 * np.arcsin(C / k)
    bin_state = format(k, f'0{nC}b')
    
    # Isolate the specific clock state using X gates
    for idx, bit in enumerate(reversed(bin_state)):
        if bit == '0':
            qc.x(c_reg[idx])
            
    # Apply multi-controlled RY gate to the ancilla
    cry_gate = RYGate(theta_k).control(nC)
    qc.append(cry_gate, c_reg[:] + [ancilla[0]])
    
    # Uncompute the X gates
    for idx, bit in enumerate(reversed(bin_state)):
        if bit == '0':
            qc.x(c_reg[idx])

# =============== IQPE (Uncomputation) ===============

'''
The clock register and the target b register become deeply entangled during 
the QPE and rotation phases. If we do not uncompute (using Inverse QPE), 
the solution state cannot be separated from the clock states. Uncomputation 
disentangles the registers, safely clearing the clock qubits and isolating 
the final solution |x> entirely within the b register.
'''

# Step 1: Apply QFT 
qft_gate = QFTGate(num_qubits=nC)
qc.append(qft_gate, c_reg)

# Step 2: Apply inverse controlled time evolution
# We reverse the loop and use negative time to perfectly uncompute the QPE phase
for i in reversed(range(nC)):
    evolution_time = t * (2 ** i)

    # Negative time for the inverse exponential
    evol_gate_inv = PauliEvolutionGate(pauli_op, time=evolution_time)
    trotter_circuit_inv = SuzukiTrotter(order=1, reps=1).synthesize(evol_gate_inv)
    
    controlled_gate_inv = trotter_circuit_inv.to_gate(label=f'U^-{2**i}').control(1)
    qc.append(controlled_gate_inv, [c_reg[i]] + b_reg[:])

# Step 3: Apply final Hadamard gates to the clock register
qc.h(c_reg)

# =============== Measurement ===============

'''
MEASUREMENT MECHANICS:
Measurement collapses the quantum superposition into classical bits, allowing 
us to extract tangible data. In HHL, we measure the ancilla to filter for successful 
rotations (keeping only |1> states) and the b_register to observe the solution |x>.

MEASUREMENT BOTTLENECK & SOLUTIONS:
Problem: The solution |x> is encoded as probability amplitudes. Reading every 
single vector component of |x> (Full State Tomography) requires O(N) operations, 
which destroys the algorithm's exponential speedup.
Solution: Instead of extracting the full vector, we should use HHL to compute 
global properties or expectation values of a specific operator M (e.g., <x|M|x>), 
which preserves the quantum advantage.
'''

# Measure the b register dynamically based on its size
for i in range(nB):
    qc.measure(b_reg[i], x_classic[i])

# Measure the ancilla qubit to check if the solution was successfully encoded
qc.measure(ancilla[0], x_classic[nB])

# Simulation only for validating purposes 
simulator = AerSimulator()
circuito_transpilado = transpile(qc, simulator)
result = simulator.run(circuito_transpilado, shots=10000).result()
count = result.get_counts()

print("\nMeasurement Results (Ancilla + B Register : counts):")
print(count)

print("Quantum Circuit for the HHL Algorithm:")
qc.draw('mpl')
plt.show()