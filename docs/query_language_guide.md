# Query Language Usage Guide

This guide provides a comprehensive reference for Remy's query language, which allows you to filter, search, and manipulate notecard collections using a powerful set-based query system.

## Table of Contents

1. [Introduction](#introduction)
2. [Set Types](#set-types)
3. [Basic Queries](#basic-queries)
4. [Comparison Operators](#comparison-operators)
5. [Logical Operators](#logical-operators)
6. [Function-Based Operators](#function-based-operators)
7. [Slice Operators](#slice-operators)
8. [Macros](#macros)
9. [Practical Examples](#practical-examples)

---

## Introduction

Remy stores notecard metadata as **two-column relations** (tables) where each row is a `(label, value)` pair. For example:
- The `tags` field contains pairs like `(card1, 'work')`, `(card2, 'personal')`
- The `status` field contains pairs like `(card1, 'active')`, `(card2, 'completed')`

Queries in Remy operate on three fundamental set types and return sets of matching notecards.

---

## Set Types

The query language works with three types of sets:

### 1. LabelSet
A **LabelSet** is a set of notecard labels (strings). This is what most queries ultimately return—a set of notecard identifiers.

**Example**: `{'card1', 'card2', 'card3'}`

### 2. ValueSet
A **ValueSet** is a set of field values. Values can be strings, numbers, dates, or other types.

**Example**: `{'work', 'personal', 'urgent'}` (tags) or `{1, 2, 3, 4}` (priorities)

### 3. PairSet
A **PairSet** is a set of `(value, label)` tuples representing the two-column relation. PairSets are always sorted and deduplicated.

**Example**: `{('work', 'card1'), ('work', 'card2'), ('personal', 'card3')}`

**Key Insight**: Most filter expressions (like `tags='work'`) return PairSets, which are then projected to LabelSets for final output.

---

## Basic Queries

### Field Equality
Match notecards where a field has a specific value:

```
tags='work'
status='active'
priority=1
```

Each equality expression returns a PairSet of matching `(value, label)` pairs.

### Field Access
Reference an entire field index to get all its pairs:

```
tags          # All (tag, label) pairs
status        # All (status, label) pairs
```

### Null Values
Check for or exclude null values:

```
status=null       # Notecards with no status
status!=null      # Notecards with any status
```

---

## Comparison Operators

Use comparison operators to create range queries:

| Operator | Meaning | Example |
|----------|---------|---------|
| `=` | Equal to | `priority=1` |
| `!=` | Not equal to | `status!='completed'` |
| `<` | Less than | `priority<3` |
| `<=` | Less than or equal | `priority<=2` |
| `>` | Greater than | `created>'2024-01-01'::date` |
| `>=` | Greater than or equal | `modified>='2024-01-01 00:00:00'::timestamp` |

### Date and Time Literals

Use type casts for date and datetime values:

```
created>'2024-01-01'::date
modified>='2024-01-01 15:30:00'::timestamp
```

### Date Arithmetic

Add or subtract time intervals from dates:

```
created > '2024-01-01'::date - '30 days'::timedelta
modified < '2024-12-31 23:59:59'::timestamp + '1 month'::timedelta
```

Supported units: `days`, `hours`, `minutes`, `seconds`, `weeks`, `months`, `years`

---

## Logical Operators

Combine queries using logical operators:

### AND Operator
The AND operator performs an `intersect_by_label` operation—it keeps pairs from the left operand whose labels appear in the right operand.

```
tags='work' AND status='active'
```

This returns notecards that have both `tags='work'` AND `status='active'`.

### OR Operator
The OR operator performs a `union` operation—it combines all pairs from both operands.

```
tags='work' OR tags='personal'
```

This returns notecards that have either tag.

### NOT Operator
Negate a query expression:

```
NOT status='completed'
tags='work' AND NOT status='completed'
```

### Operator Precedence
- `NOT` (highest precedence)
- `AND`
- `OR` (lowest precedence)

Use parentheses to control precedence:

```
(tags='work' OR tags='urgent') AND status='active'
```

---

## Function-Based Operators

Function-based operators provide powerful set manipulation capabilities beyond basic filtering.

### Pair-Aware Operators

These operators work with PairSets and perform operations based on matching labels or values.

#### `intersect_by_label(A, B)`
Keep pairs in A whose **label** appears in B (match on first component).

```
intersect_by_label(tags='work', status='active')
```

Returns pairs from `tags='work'` whose labels also appear in `status='active'`.

#### `intersect_by_value(A, B)`
Keep pairs in A whose **value** appears in B (match on second component).

```
intersect_by_value(tags='work', categories='work')
```

Returns pairs from `tags='work'` whose values also appear in `categories`.

#### `difference_by_label(A, B)`
Remove pairs from A whose **label** appears in B.

```
difference_by_label(tags='work', status='completed')
```

Returns work-tagged notecards that are NOT completed.

#### `difference_by_value(A, B)`
Remove pairs from A whose **value** appears in B.

```
difference_by_value(tags, excluded_tags)
```

Returns tag pairs whose values are not in the excluded list.

#### `join_by_value_to_label(A, B)`
Relational join where the value of A matches the label of B.

```
join_by_value_to_label(previous, tags='work')
```

For each pair `(label1, value)` in A and `(value, label2)` in B where value matches label2 (as a string), produces `(label1, label2)`.

### Pair-Unaware Operators

These operators work with any set type (PairSet, LabelSet, or ValueSet) but both arguments must be the same type.

#### `union(A, B)`
Set union of A and B.

```
union(tags='work', tags='personal')
union(labels(status='active'), labels(priority=1))
```

#### `intersect(A, B)`
Set intersection of A and B.

```
intersect(tags='work', tags='urgent')
```

#### `difference(A, B)`
Set difference (elements in A but not in B).

```
difference(tags, tags='archived')
```

### Projection Operators

Convert between set types.

#### `labels(PairSet)` → LabelSet
Extract labels from a PairSet (domain projection).

```
labels(tags='work')
labels(union(tags='work', tags='personal'))
```

#### `values(PairSet)` → ValueSet
Extract values from a PairSet (range projection).

```
values(tags)           # All unique tag values
values(priority<3)     # All priority values less than 3
```

### Transformation Operators

#### `flip(PairSet)` → PairSet
Swap labels and values in a PairSet. All values must be strings (labels).

```
flip(previous)
```

Transforms `(value, label)` pairs into `(label, value)` pairs. Useful for inverting relationships like `previous`/`next` chains.

**Error**: Raises an error if any value is not a string.

---

## Slice Operators

Slice operators allow you to select contiguous ranges from sorted pair sets using Python-style slicing semantics.

### `slice_by_label(PairSet, start, end)` → PairSet
Returns pairs from index `start` (inclusive) to index `end` (exclusive) when the PairSet is sorted by **label**.

```
slice_by_label(tags, 0, 10)      # First 10 cards by label
slice_by_label(tags, 5, 15)      # Cards at positions 5-14
slice_by_label(tags, -3, -1)     # Third and second to last cards
```

### `slice_by_value(PairSet, start, end)` → PairSet
Returns pairs from index `start` (inclusive) to index `end` (exclusive) when the PairSet is sorted by **value**.

```
slice_by_value(priority, 0, 5)   # First 5 cards by priority value
slice_by_value(tags, 0, 10)      # First 10 cards by tag value (alphabetically)
```

### `slice_by_label_from(PairSet, start)` → PairSet
Returns pairs from index `start` to the end when sorted by **label**.

```
slice_by_label_from(tags, 10)    # All cards starting from position 10
slice_by_label_from(tags, -5)    # Last 5 cards by label
```

### `slice_by_value_from(PairSet, start)` → PairSet
Returns pairs from index `start` to the end when sorted by **value**.

```
slice_by_value_from(priority, 0) # All cards sorted by priority value
slice_by_value_from(tags, -10)   # Last 10 cards by tag value
```

### Slicing Semantics

- **0-based indexing**: First element is at index 0
- **Negative indices**: Count from the end (-1 is the last element, -2 is second-to-last, etc.)
- **Python-style ranges**: Start is inclusive, end is exclusive
- **Invalid ranges**: If start >= end after normalization, returns an empty PairSet
- **Out of bounds**: Indices are automatically clamped to valid ranges

**Examples**:

```
# Get first 3 cards by label
slice_by_label(tags='work', 0, 3)

# Get last 5 cards by priority value
slice_by_value(priority, -5, 100)

# Get middle portion
slice_by_label(status='active', 10, 20)

# Chaining with other operators
intersect_by_label(
    slice_by_label(tags, 0, 50),
    status='active'
)
```

---

## Macros

Macros allow you to define reusable query patterns and create parameterized queries.

### Zero-Arity Macros

Define simple macros without parameters:

```
@work := tags='work' OR tags='urgent'
@active := status='active' OR status='in_progress'

@work AND @active
```

### Parametric Macros

Define macros with parameters (parameters must start with uppercase letters):

```
@with_tag(Tag) := tags=Tag
@with_status_and_tag(Status, Tag) := status=Status AND @with_tag(Tag)

@with_status_and_tag('active', 'work')
```

### The @main Macro

The final result of a query is called `@main`. You can define it explicitly or leave it implicit:

```
# Explicit @main
@work := tags='work';
@active := status='active';
@main := @work AND @active

# Implicit @main (last unnamed expression)
@work := tags='work';
@work AND status='active'
```

### Config Macros

Define global macros in `.remy/config.py` that are available in all queries:

```python
# In .remy/config.py
MACROS = {
    'WORK': '@work := tags="work" OR tags="urgent"',
    'ACTIVE': '@active := status="active"',
    'PROJECT': '@project(Tag) := tags=Tag AND @active',
}
```

Use them in any query:

```
@work AND @active
@project('alpha')
```

**Constraints**:
- Config macros cannot define `@main` (reserved for queries)
- Query macros cannot override config macros
- Macros can reference other macros (forward references supported)

---

## Practical Examples

### Example 1: Find Active Work Items

```
tags='work' AND status='active'
```

Or using macros:

```
@work := tags='work';
@active := status='active';
@work AND @active
```

### Example 2: Find High Priority Items Due Soon

```
priority<=2 AND due<'2024-02-01'::date
```

### Example 3: Find Items Modified in the Last 30 Days

```
modified > '2024-01-01'::timestamp - '30 days'::timedelta
```

### Example 4: Find Work or Personal Items That Are Not Completed

```
(tags='work' OR tags='personal') AND NOT status='completed'
```

Using functions:

```
difference_by_label(
    union(tags='work', tags='personal'),
    status='completed'
)
```

### Example 5: Find Cards That Reference Other Work Cards

```
intersect_by_value(
    previous,
    tags='work'
)
```

This finds cards whose `previous` value matches labels of cards tagged 'work'.

### Example 6: Find Next Cards in a Chain

```
flip(previous)
```

This inverts the `previous` relationship to find all "next" cards.

### Example 7: Complex Chain Navigation

```
@work_cards := tags='work';
@prev_of_work := intersect_by_value(previous, @work_cards);
@next_of_work := flip(intersect_by_label(previous, @work_cards));

union(@prev_of_work, @next_of_work)
```

This finds all cards immediately before or after work-tagged cards in a chain.

### Example 8: Top 10 Cards by Priority

```
slice_by_value(priority, 0, 10)
```

### Example 9: Last 5 Modified Cards

```
slice_by_value(modified, -5, 100)
```

### Example 10: Paginated Results

Get second page of 20 cards (sorted by label):

```
slice_by_label(tags='work', 20, 40)
```

### Example 11: Middle Range of Active Cards

```
intersect_by_label(
    slice_by_label(status='active', 10, 30),
    tags='work'
)
```

### Example 12: Chaining Multiple Operators

```
@high_priority := priority<=2;
@work_items := tags='work';
@recent := modified > '2024-01-01'::timestamp;

# Get first 20 high-priority work items modified recently
slice_by_label(
    intersect_by_label(
        intersect_by_label(@high_priority, @work_items),
        @recent
    ),
    0, 20
)
```

### Example 13: Find Orphaned Cards (No Previous Reference)

```
difference_by_label(tags, flip(previous))
```

This finds all cards that are not referenced as `previous` by any other card.

### Example 14: Using ValueSets

```
@excluded_tags := values(tags='archived' OR tags='deleted');

difference_by_value(tags, @excluded_tags)
```

### Example 15: Complex Date Range Query

```
@start := '2024-01-01'::date;
@end := @start + '3 months'::timedelta;

created >= @start AND created < @end AND status='active'
```

---

## Query Execution Flow

1. **Parse**: The query string is parsed into an Abstract Syntax Tree (AST)
2. **Macro Expansion**: All macro references are expanded into their definitions
3. **Evaluation**: The AST is evaluated against field indices, producing PairSets
4. **Projection**: If the result is a PairSet, it's projected to a LabelSet using `labels()`
5. **Output**: The final LabelSet identifies matching notecards

---

## Tips and Best Practices

### Performance

- **Use specific filters first**: `tags='work' AND status='active'` is more efficient than `status='active' AND tags='work'` if `tags='work'` is more selective
- **Leverage indices**: All field comparisons use indexed lookups, which are very fast
- **Slice early**: Use slice operators before complex operations to reduce dataset size

### Readability

- **Use macros**: Break complex queries into reusable, named components
- **Use explicit @main**: When using multiple macros, explicitly define `@main` for clarity
- **Add whitespace**: Use parentheses and line breaks for complex nested queries

### Common Patterns

- **Filter by multiple tags**: `union(tags='tag1', tags='tag2')` or `tags='tag1' OR tags='tag2'`
- **Exclude completed**: `difference_by_label(my_query, status='completed')`
- **Find chains**: Use `previous` with `flip()` and `join_by_value_to_label()`
- **Top N results**: Use `slice_by_value()` or `slice_by_label()` with appropriate range

---

## Error Handling

Common errors and their meanings:

- **"Unknown function"**: Function name misspelled or doesn't exist
- **"expects N arguments"**: Wrong number of arguments passed to function
- **"must be a PairSet"**: Operator requires PairSet but got LabelSet or ValueSet
- **"cannot be a ValueSet/LabelSet"**: Operator doesn't support that set type
- **"both arguments must be the same type"**: Type mismatch in pair-unaware operators
- **"Duplicate macro definition"**: Same macro name defined twice
- **"Circular macro dependency"**: Macro references itself directly or indirectly
- **"start index must be an integer"**: Slice indices must be integer literals

---

## Summary

The Remy query language provides:

1. **Three set types**: LabelSet, ValueSet, and PairSet
2. **Basic filtering**: Equality, comparison, and range queries
3. **Logical operators**: AND, OR, NOT with proper precedence
4. **Set operators**: Union, intersection, difference (pair-aware and pair-unaware)
5. **Projection operators**: Convert between set types
6. **Transformation operators**: Flip pairs, join relations
7. **Slice operators**: Extract ranges from sorted pair sets
8. **Macros**: Reusable query patterns with parameters

This combination of features makes the query language both powerful and flexible, allowing you to express complex notecard queries concisely.

---

For more details on the design and implementation, see:
- [Query Language Design Document](design/query_language.md)
- [Remy Configuration Guide](remy_config.md)
