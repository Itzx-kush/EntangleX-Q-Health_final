export type PreviewKind = 'hybrid-vqc' | 'classical-baseline' | 'quantum-kernel';
export type RegisterWidth = 2 | 4;

export const previewTabs: {id: PreviewKind; label: string}[] = [
  {id: 'hybrid-vqc', label: 'Hybrid VQC'},
  {id: 'classical-baseline', label: 'Classical baseline'},
  {id: 'quantum-kernel', label: 'Quantum kernel'},
];
const angles = [Math.PI / 3, Math.PI / 4, Math.PI / 6, Math.PI / 5];

// Independent RY input amplitudes followed by a ring of CNOT permutations.
// PennyLane basis labels put wire zero at the left. The sample weights are zero.
export function exampleProbabilities(width: RegisterWidth) {
  const size = 2 ** width;
  const values = Array<number>(size).fill(0);
  for (let basis = 0; basis < size; basis++) {
    const bits = basis.toString(2).padStart(width, '0').split('').map(Number);
    let probability = 1;
    for (let q = 0; q < width; q++) {
      const angle = angles[q] / 2;
      probability *= (bits[q] ? Math.sin(angle) : Math.cos(angle)) ** 2;
    }
    for (let layer = 0; layer < 2; layer++)
      for (let q = 0; q < width; q++) bits[(q + 1) % width] ^= bits[q];
    values[parseInt(bits.join(''), 2)] = probability;
  }
  return values.map((value, i) => ({label: '|' + i.toString(2).padStart(width, '0') + '⟩', value}));
}

export function previewPreset(kind: PreviewKind, width: RegisterWidth) {
  if (kind === 'classical-baseline') return {
    summary: 'Classical baseline', detail: 'A scikit-learn estimator and an example validation protocol for tabular biomedical features.',
    stats: [['Estimator', 'Gradient boosting'], ['Comparison', 'Random forest']],
    chart: 'Illustrative feature weights', values: [
      {label: 'Polyuria', value: .38}, {label: 'Polydipsia', value: .29}, {label: 'Age', value: .19}, {label: 'Alopecia', value: .14},
    ], code: `from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

# Illustrative protocol for early-stage-diabetes.
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
gb_model = GradientBoostingClassifier(random_state=42)
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
# Fit and score both on the same training and evaluation partitions.`,
  };
  const x = angles.slice(0, width);
  const wires = Array.from({length: width}, (_, i) => 'q[' + i + ']').join(' · ');
  if (kind === 'quantum-kernel') return {
    summary: 'Fidelity kernel', detail: 'Compare a fixed input with four scaled copies. The overlap is the probability of measuring the all-zero state after uncomputing the second feature map.',
    stats: [['Register', width + ' qubits'], ['Basis states', String(2 ** width)]],
    chart: 'Calculated example overlaps', values: [1, .75, .5, 0].map(scale => ({
      label: '×' + scale, value: x.reduce((p, angle) => p * Math.cos(angle * (1 - scale)) ** 2, 1),
    })), code: `import pennylane as qml
import numpy as np

width = ${width}
dev = qml.device("default.qubit", wires=width)
x = np.array([${x.join(', ')}])

@qml.qnode(dev)
def kernel_circuit(x, z):
    for i in range(width):
        qml.Hadamard(wires=i)
        qml.RZ(2 * x[i], wires=i)
    for i in range(width):
        qml.RZ(-2 * z[i], wires=i)
        qml.Hadamard(wires=i)
    return qml.probs(wires=range(width))

print([kernel_circuit(x, scale * x)[0] for scale in (1, .75, .5, 0)])`,
  };
  return {
    summary: 'Variational quantum classifier', detail: 'Fixed input angles and zero example weights make this circuit reproducible. Two variational layers each apply a ring of controlled-X gates.',
    stats: [['Register', width + ' qubits'], ['Wires', wires]],
    chart: 'Calculated basis probabilities', values: exampleProbabilities(width),
    code: `import pennylane as qml
import torch

width = ${width}
dev = qml.device("default.qubit", wires=width)

def ansatz(inputs, weights):
    for i in range(width):
        qml.RY(inputs[i], wires=i)
    for layer in range(2):
        for i in range(width):
            qml.Rot(*weights[layer, i], wires=i)
        for i in range(width):
            qml.CNOT(wires=[i, (i + 1) % width])

@qml.qnode(dev, interface="torch")
def classifier(inputs, weights):
    ansatz(inputs, weights)
    return [qml.expval(qml.PauliZ(i)) for i in range(width)]

model = qml.qnn.TorchLayer(classifier, {"weights": (2, width, 3)})

@qml.qnode(dev, interface="torch")
def distribution(inputs, weights):
    ansatz(inputs, weights)
    return qml.probs(wires=range(width))

x = torch.tensor([${x.join(', ')}], dtype=torch.float64)
print(distribution(x, torch.zeros(2, width, 3)))`,
  };
}
