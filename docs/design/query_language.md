## Summary: Pair-Based Operations for Remy Query Language (Chains / `previous`)

### Core idea
Remy stores metadata as **two-column relations** (tables) of the form:

- `field_name`: rows are `(primary_label, value)`

Examples:
- `tags`: `(label, tag)`
- `previous`: `(label, previous_label)` where `previous_label` is itself a `primary_label`

Many queries can be expressed as ordinary set algebra over:
- Note: Sets are considered sorted and deduplicated using the same
  SortedSet logic we use for indices, which includes a little extra complexity
  to make sure we can have non-homogeneous incomparable types in the value position.
  Semantically the user should be unaware of this.
- **Label sets**: sets of `primary_label`
- **Value sets**: sets of `value`
    - Note: There is not a huge semantic difference between a LabelSet and a
      ValueSet, but we know that a LabelSet will only contain strings.
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
- Inputs: PairSet `A`, PairSet or LabelSet `B`
- Output: PairSet
- Semantics: remove pairs from `A` whose **label** appears in `B`
- Note: If `B` is a PairSet, labels are extracted before comparison; if `B` is a LabelSet, it is used directly

4) `difference_by_value(A, B)`
- Inputs: PairSet `A`, PairSet or ValueSet `B`
- Output: PairSet
- Semantics: remove pairs from `A` whose **value** appears in `B`
- Note: If `B` is a PairSet, values are extracted before comparison; if `B` is a ValueSet, it is used directly

5) `join_by_value_to_label(A, B)`
- Inputs: PairSet `A`, PairSet `B`
- Output: PairSet
- Semantics: relational join / composition where:
  - `(l1, v)` in `A` and `(v, x)` in `B` produce `(l1, x)`
- This is the “second-of-left matches first-of-right” operation (value → label).
- Note: We coerce the value type of `A` to match the label type of `B` as
  needed, in general this is used for indices that are referencing other cards
  by their label, so they *should* be a string type anyway.

### Pair Unaware Operators

1) `union(A, B)`
- Inputs: PairSet `A`, PairSet `B` | LabelSet `A`, LabelSet `B` | ValueSet `A`, ValueSet `B`
- Output: PairSet | LabelSet | ValueSet
- Semantics: set union of all pairs, labels, or values in `A` and `B`
- Note: This may produce weird results if `A` and `B` come from indices with different value types, but we allow it.

2) `intersect(A, B)`
- Inputs: PairSet `A`, PairSet `B` | LabelSet `A`, LabelSet `B` | ValueSet `A`, ValueSet `B`
- Output: PairSet | LabelSet | ValueSet
- Semantics: set intersection of all pairs, labels, or values in `A` and `B`
- Note: If `A` and `B` have different value types that's fine, but it will just be the empty set.

3) `difference(A, B)`
- Inputs: PairSet `A`, PairSet `B` | LabelSet `A`, LabelSet `B` | ValueSet `A`, ValueSet `B`
- Output: PairSet | LabelSet | ValueSet
- Semantics: standard set difference (elements in `A` but not in `B`)
- Note: Both arguments must be the same type (PairSet, LabelSet, or ValueSet)

### Pair Transformation Operators

1) `flip(PairSet)` → PairSet
- Inputs: PairSet where all values are strings (labels)
- Output: PairSet with labels and values swapped
- Semantics: For each pair `(value, label)` in the input, produces `(label, value)` in the output
- Note: Raises an error if any value is not a string, as only string labels can become valid labels after flipping
- Use case: Invert relationships like `previous`/`next` mappings where values reference other card labels

### Projection Operators
These operators are easiest to use with a few simple standard functions:

1) `labels(PairSet)` → LabelSet (domain projection)
    - Note: This a *set* operation, so duplicates are removed
2) `values(PairSet)` → ValueSet (range projection)
    - Note: This a *set* operation, so duplicates are removed

### Current Queries

The current query expressions denote a filter operation, that should be considered as returning a pairset with the
appropriate filtering applied. Note that it is not necessarily possible to express this filtering directly in terms of
the set operations yet.

Examples:
- `tags='foo'` is the PairSet: `{(l, v) in tags | v = 'foo'}`
- `created > '2026-01-01 00:00'::timestamp` is the PairSet: `{(l, v) in created | v > '2026-01-01 00:00'::timestamp}`

The AND operator becomes an intersect_by_label operation on the resulting pairsets, e.g.:
- "tags='foo' AND created > '2026-01-01 00:00'::timestamp" is the PairSet:
  `intersect_by_label({(l, v) in tags | v = 'foo'}, {(l, v) in created | v > '2026-01-01 00:00'::timestamp})`
- Note: This keeps the same asymmetric semantics as before, where we keep pairs from the
  first operand whose labels appear in the second operand.

The OR operator becomes a union operation on the resulting pairsets, e.g.:
- "tags='foo' OR created > '2026-01-01 00:00'::timestamp" is the PairSet:
  `union({(l, v) in tags | v = 'foo'}, {(l, v) in created | v > '2026-01-01 00:00'::timestamp})`
- Note: This has symmetric semantics, but may include duplicate labels before projection.

These expressions should be allowed to appear inside the new function call expressions wherever PairSets are expected.

Example:
- `tags ="foo" and created > '2026-01-01 00:00'::timestamp` can be written as `intersect_by_label(tags="foo", created > '2026-01-01 00:00'::timestamp)`

### `remy query <where-expression>`

The result of the `--where` expression in `remy query` must be a `LabelSet` or
`PairSet`.  If it is a `PairSet`, it will be projected to a `LabelSet` using
the `labels()` function, before filtering the final output.  All ordering
semantics remain the same, as carried forward from the SortedSet semantics.
`--order-by` and `--limit` operate as usual, *after* the final projection to
`LabelSet` (with `--limit` being applied last).
