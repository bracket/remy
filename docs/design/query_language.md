## Summary: Pair-Based Operations for Remy Query Language (Chains / `previous`)

### Core idea
Remy stores metadata as **two-column relations** (tables) of the form:

- `field_name`: rows are `(primary_label, value)`

Examples:
- `tags`: `(label, tag)`
- `previous`: `(label, previous_label)` where `previous_label` is itself a `primary_label`

Many queries can be expressed as ordinary set algebra over:
- **Label sets**: sets of `primary_label`
- **Pair sets**: sets of `(primary_label, value)` pairs

### Why pair-aware operators are needed
Some important operations are not just “set intersection of labels.” With pair sets, we frequently want to:
- keep/remove pairs based on **matching labels** (first component), ignoring values
- keep/remove pairs based on **matching values** (second component), ignoring labels
- **join/compose** relations where the **value** of one relation matches the **label** of another (e.g., navigating `previous` chains)

This is especially relevant for `previous`, because we often want to compare:
- the **set of cards** we’re considering (labels)
vs.
- the **set of labels referenced by other cards as `previous`** (values of the `previous` relation)

### Operator set (five pair-aware operators)
We will implement the following five operators as first-class query operators:

1) `intersect_by_label(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: keep pairs in `A` whose **label** appears in `B` (match on first component)

2) `intersect_by_value(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: keep pairs in `A` whose **value** appears in `B` (match on second component)

3) `difference_by_label(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: remove pairs from `A` whose **label** appears in `B`

4) `difference_by_value(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: remove pairs from `A` whose **value** appears in `B`

5) `join_by_value_to_label(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: relational join / composition where:
  - `(l1, v)` in `A` and `(v, x)` in `B` produce `(l1, x)`
- This is the “second-of-left matches first-of-right” operation (value → label).

### Common derived primitives (recommended wrappers)
These operators are easiest to use with a few simple standard functions:

- `rows(field)` → PairSet of `(label, value)` for that metadata table
- `labels(PairSet)` → LabelSet (domain projection)
- `values(PairSet)` → ValueSet (range projection)
- `refs(field)` → LabelSet shorthand for `values(rows(field))`, interpreted as labels (optionally filtered to existing labels)

(Exact names can vary, but these are useful for ergonomics.)

---

## Example: Selecting cards at the end of chains (“tails”)

**Goal:** select cards that are *not referenced as `previous` by any other card*.
Equivalently: from some candidate set of cards `C`, subtract the set of labels that appear as `previous` values.

### In label-set notation (high level)
```remy
C - refs("previous")
