# Quality summary - phase1_phase2_t0

Rows graded: 700 (warm-up excluded). Failed outputs score 0.

## Track A - note processing (field accuracy)

| enforcement | max_retries | temperature | n | valid | field_score | field_score_valid_only | note_type | tags | actions_f1 | due_acc | entities_f1 | invented_tasks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| json_object | 1 | 0.0 | 75 | 80% | 54% | 68% | 56% | 36% | 64% | 61% | 54% | 4% |
| json_schema | 1 | 0.0 | 75 | 100% | 65% | 65% | 64% | 47% | 78% | 70% | 63% | 8% |
| prompt_only | 0 | 0.0 | 125 | 48% | 34% | 70% | 36% | 22% | 39% | 38% | 34% | 4% |
| prompt_only | 1 | 0.0 | 75 | 80% | 54% | 68% | 56% | 36% | 64% | 61% | 54% | 4% |

Diagnostics - precision = share of the model's items that are right, recall = share of gold found:

| enforcement | max_retries | temperature | tags_precision | tags_recall | entities_precision | entities_recall |
|---|---|---|---|---|---|---|
| json_object | 1 | 0.0 | 39% | 69% | 44% | 79% |
| json_schema | 1 | 0.0 | 51% | 88% | 51% | 99% |
| prompt_only | 0 | 0.0 | 23% | 41% | 28% | 48% |
| prompt_only | 1 | 0.0 | 39% | 69% | 44% | 79% |

## Track B - ask my notes

| enforcement | max_retries | temperature | n | valid | qa_score | answered_correctly | abstain_ok | hallucination_rate | grounded |
|---|---|---|---|---|---|---|---|---|---|
| json_object | 1 | 0.0 | 75 | 100% | 96% | 95% | 100% | 0% | 100% |
| json_schema | 1 | 0.0 | 75 | 100% | 96% | 95% | 100% | 0% | 100% |
| prompt_only | 0 | 0.0 | 125 | 100% | 96% | 95% | 100% | 0% | 100% |
| prompt_only | 1 | 0.0 | 75 | 100% | 96% | 95% | 100% | 0% | 100% |

## Score by difficulty (all settings pooled)

```
track  difficulty
A      easy          0.61
       hard          0.44
       medium        0.47
B      easy          1.00
       hard          0.83
       medium        1.00
```

## Hardest items (all settings pooled)

```
track  item_id
B      b019       0.00
A      a022       0.07
       a024       0.09
       a007       0.09
       a005       0.10
       a013       0.13
       a010       0.19
       a025       0.34
       a018       0.40
       a017       0.43
       a014       0.44
       a015       0.44
```
