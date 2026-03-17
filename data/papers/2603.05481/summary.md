# High-performance syndrome extraction circuits for quantum codes

- arXiv: `2603.05481v1`
- Categories: quant-ph
- Relevance: **maybe** (confidence 0.70)

## Decoder approach
- Name: Left-right circuits (LRCs)
- Family: other
- Description: A framework for constructing low-depth, single-ancilla syndrome extraction circuits for arbitrary CSS codes by partitioning data qubits into left/right sets and optimizing non-interleaved CNOT schedules. This is a circuit-construction method rather than a decoding algorithm.
- Key ideas:
  - Generalize left-right syndrome-extraction circuits from specific code families to arbitrary CSS codes.
  - Define residual errors, residual distance `Delta(E)`, and extended-code distance `d_ext(R)` as lightweight surrogates for circuit-level hook-error analysis.
  - Rank candidate circuits by minimum residual distance, ancilla idle count, and residual-distance profile, with optional re-ranking by extended-code distance.
  - Use the framework both to synthesize practical circuits and to prove impossibility / upper-bound results for the gross code.

## Performance claims
- Across the benchmarked code families, the optimized LRCs reduce circuit depth and logical failure rates relative to existing single-ancilla SEC constructions, with improvements in logical error rate of up to an order of magnitude.
- For the gross code, the paper proves that no non-interleaving SEC can achieve circuit distance 12, rules out uniformly tiled non-interleaved distance-11 constructions, and presents an explicit depth-8 circuit conjectured to achieve circuit distance 11.
- Compared against LDPC / QUITS constructors and representative AlphaSyndrome / PropHunt circuits, the proposed schedules typically trade less depth and idling for better practical logical performance under the paper's noise model.

### Thresholds
- Unknown / not specified

## Simulations
- level=circuit_level; noise=Standard circuit noise with independent failures on idle locations, CNOTs, preparations, and measurements; codes=HGP625 [[625,25,8]], Tanner200 [[200,10,10]], Haah128 [[128,14,8]], FB126 [[126,8,9]], gross [[144,12,12]]; results=Optimized LRCs outperform baseline single-ancilla SECs on the main benchmark set, while the gross-code search/proof pipeline narrows the best non-interleaved construction to a depth-8 circuit conjectured to reach distance 11.

## Missing fields
- performance_claims.thresholds
- links.code_repo_urls

## Links
- Abstract: https://arxiv.org/abs/2603.05481v1
- PDF: https://arxiv.org/pdf/2603.05481v1
- DOI: https://doi.org/10.48550/arXiv.2603.05481
