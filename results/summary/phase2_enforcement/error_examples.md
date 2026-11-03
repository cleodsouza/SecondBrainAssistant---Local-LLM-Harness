# Attempt-1 error examples

## json_object / temp 0.0 / Track A  (39 failures)
- 18 x `note_type: Input should be 'idea', 'meeting', 'journal', 'reading', 'todo' or 'reference'`
- 9 x `tags.3: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `tags.2: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `summary: Value error, summary must be at most 2 sentences`
- 3 x `tags.1: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `action_items.1.due: Input should be a valid date or datetime, input is too short`

<details><summary>a013 r1 - failed</summary>

```
{
  "title": "Physio Follow-up: IT Band Syndrome",
  "note_type": "health",
  "tags": ["health", "fitness"],
  "summary": "Diagnosed with IT band syndrome affecting the left knee. Treatment includes daily foam rolling and specific exercises with a cap on long runs.",
  "action_items": [
    {
      "description": "Perform daily foam rolling",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Do glute bridges and clamshells 3x15 daily",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Cap long runs at 12 km for two weeks",
      "due": "2026-10-02",
      "priority": "medium"
    },
    {
      "description": "Attend follow-up appointment with Dr. Neha Shah",
      "due": "2026-09-29",
      "priority": "high"
    }
  ],
  "entities
```
</details>

<details><summary>a024 r1 - failed</summary>

```
{
  "title": "Vitamin D deficiency and doctor's prescription",
  "note_type": "health",
  "tags": ["health", "fitness", "learning"],
  "summary": "Annual checkup shows low Vitamin D levels at 14 ng/mL. Doctor prescribed weekly supplementation for 8 weeks with a recheck scheduled for November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "8 weeks",
    "November"
  ]
}
```
</details>

<details><summary>a025 r1 - ok_retry</summary>

```
{
  "title": "Follow up with Kabir on analytics dashboard",
  "note_type": "meeting",
  "tags": ["work", "team", "productivity"],
  "summary": "Schedule a catch-up with Kabir to discuss post-launch analytics dashboard progress and consider Q1 OKRs.",
  "action_items": [
    {
      "description": "Catch up with Kabir on post-launch analytics dashboard",
      "due": "2026-11-02",
      "priority": "medium"
    },
    {
      "description": "Review and define Q1 OKRs",
      "due": null,
      "priority": "medium"
    }
  ],
  "entities": [
    "Kabir",
    "post-launch analytics dashboard",
    "Q1 OKRs"
  ]
}
```
</details>

## json_object / temp 0.7 / Track A  (42 failures)
- 18 x `note_type: Input should be 'idea', 'meeting', 'journal', 'reading', 'todo' or 'reference'`
- 18 x `tags.2: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `summary: Value error, summary must be at most 2 sentences`
- 3 x `tags.1: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `tags.3: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `tags.0: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`

<details><summary>a013 r1 - failed</summary>

```
{
  "title": "Physio Follow-up: IT Band Syndrome",
  "note_type": "health",
  "tags": ["health", "fitness"],
  "summary": "Diagnosed with IT band syndrome affecting the left knee. Treatment includes daily foam rolling and specific exercises, with a cap on long runs at 12 km for two weeks.",
  "action_items": [
    {
      "description": "Perform daily foam rolling",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Do glute bridges and clamshells 3x15 daily",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Cap long runs at 12 km for two weeks",
      "due": "2026-10-02",
      "priority": "medium"
    },
    {
      "description": "Attend follow-up appointment with Dr. Neha Shah",
      "due": "2026-09-29",
      "priority": "high
```
</details>

<details><summary>a024 r1 - failed</summary>

```
{
  "title": "Vitamin D deficiency and treatment plan",
  "note_type": "health",
  "tags": ["health", "fitness", "wellness"],
  "summary": "Annual checkup shows low Vitamin D levels at 14 ng/mL. Doctor recommends a 60,000 IU weekly supplement for 8 weeks with a blood test recheck in November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "8 weeks",
    "blood test",
    "November"
  ]
}
```
</details>

<details><summary>a025 r1 - ok_retry</summary>

```
{
  "title": "Follow up with Kabir on analytics dashboard",
  "note_type": "meeting",
  "tags": ["work", "team", "communication"],
  "summary": "Schedule a catch-up with Kabir to discuss post-launch analytics dashboard progress and review Q1 OKRs.",
  "action_items": [
    {
      "description": "Schedule a meeting with Kabir to discuss post-launch analytics dashboard",
      "due": "2026-11-02",
      "priority": "medium"
    },
    {
      "description": "Review and formulate Q1 OKRs",
      "due": null,
      "priority": "medium"
    }
  ],
  "entities": [
    "Kabir",
    "post-launch analytics dashboard",
    "Q1 OKRs"
  ]
}
```
</details>

## json_schema / temp 0.0 / Track A  (6 failures)
- 3 x `tags: Value error, tags must be unique`
- 3 x `summary: Value error, summary must be at most 2 sentences`

<details><summary>a024 r1 - ok_retry</summary>

```
{
  "title": "Vitamin D deficiency and doctor's prescription",
  "note_type": "journal",
  "tags": ["health", "fitness", "health"],
  "summary": "Annual checkup shows low Vitamin D levels at 14 ng/mL. Doctor prescribed weekly supplementation for 8 weeks with a recheck scheduled for November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "8 weeks",
    "November"
  ]
}
```
</details>

<details><summary>a008 r1 - ok_retry</summary>

```
{
  "title": "Bday Gift & Home Repairs",
  "note_type": "todo",
  "tags": ["home", "fitness", "work", "admin"],
  "summary": "Purchase a foam roller for fitness and prepare a birthday gift for Ishita. Address a leaking bathroom tap by calling a plumber. Return Amazon parcel before the window closes on Sunday.",
  "action_items": [
    {
      "description": "Buy foam roller",
      "due": null,
      "priority": "medium"
    },
    {
      "description": "Prepare bday gift for Ishita",
      "due": "2026-08-20",
      "priority": "high"
    },
    {
      "description": "Call plumber to fix leaking bathroom tap",
      "due": "2026-08-15",
      "priority": "high"
    },
    {
      "description": "Return Amazon parcel before Sunday window closes",
      "due": "2026-08-16",
      "priorit
```
</details>

<details><summary>a008 r2 - ok_retry</summary>

```
{
  "title": "Bday Gift & Home Repairs",
  "note_type": "todo",
  "tags": ["home", "fitness", "work", "admin"],
  "summary": "Purchase a foam roller for fitness and prepare a birthday gift for Ishita. Address a leaking bathroom tap by calling a plumber. Return Amazon parcel before the window closes on Sunday.",
  "action_items": [
    {
      "description": "Buy foam roller",
      "due": null,
      "priority": "medium"
    },
    {
      "description": "Prepare bday gift for Ishita",
      "due": "2026-08-20",
      "priority": "high"
    },
    {
      "description": "Call plumber to fix leaking bathroom tap",
      "due": "2026-08-15",
      "priority": "high"
    },
    {
      "description": "Return Amazon parcel before Sunday window closes",
      "due": "2026-08-16",
      "priorit
```
</details>

## json_schema / temp 0.7 / Track A  (6 failures)
- 3 x `tags: Value error, tags must be unique`
- 3 x `summary: Value error, summary must be at most 2 sentences`

<details><summary>a024 r1 - ok_retry</summary>

```
{
  "title": "Vitamin D deficiency and treatment plan",
  "note_type": "journal",
  "tags": ["health", "fitness", "health"],
  "summary": "Annual checkup revealed low Vitamin D levels. Doctor prescribed weekly supplementation and a recheck in November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "November",
    "blood test"
  ]
}
```
</details>

<details><summary>a008 r1 - ok_retry</summary>

```
{
  "title": "Bday Gift & Home Fixes",
  "note_type": "todo",
  "tags": ["home", "work", "fitness"],
  "summary": "Purchase a foam roller and prepare a birthday gift for Ishita. Fix a leaking bathroom tap by calling a plumber. Return an Amazon parcel before the window closes on Sunday.",
  "action_items": [
    {
      "description": "Buy foam roller",
      "due": null,
      "priority": "medium"
    },
    {
      "description": "Prepare bday gift for Ishita",
      "due": "2026-08-20",
      "priority": "high"
    },
    {
      "description": "Call plumber to fix leaking bathroom tap",
      "due": "2026-08-15",
      "priority": "medium"
    },
    {
      "description": "Return Amazon parcel before Sunday window closes",
      "due": "2026-08-16",
      "priority": "medium"
    }
  ]
```
</details>

<details><summary>a008 r2 - ok_retry</summary>

```
{
  "title": "Bday Gift & Home Fixes",
  "note_type": "todo",
  "tags": ["home", "work", "fitness"],
  "summary": "Purchase a foam roller and prepare a birthday gift for Ishita. Fix a leaking bathroom tap by calling a plumber. Return an Amazon parcel before the window closes on Sunday.",
  "action_items": [
    {
      "description": "Buy foam roller",
      "due": null,
      "priority": "medium"
    },
    {
      "description": "Prepare bday gift for Ishita",
      "due": "2026-08-20",
      "priority": "high"
    },
    {
      "description": "Call plumber to fix leaking bathroom tap",
      "due": "2026-08-15",
      "priority": "medium"
    },
    {
      "description": "Return Amazon parcel before Sunday window closes",
      "due": "2026-08-16",
      "priority": "medium"
    }
  ]
```
</details>

## prompt_only / temp 0.0 / Track A  (39 failures)
- 18 x `note_type: Input should be 'idea', 'meeting', 'journal', 'reading', 'todo' or 'reference'`
- 9 x `tags.3: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `tags.2: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `summary: Value error, summary must be at most 2 sentences`
- 3 x `tags.1: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `action_items.1.due: Input should be a valid date or datetime, input is too short`

<details><summary>a013 r1 - failed</summary>

```
{
  "title": "Physio Follow-up: IT Band Syndrome",
  "note_type": "health",
  "tags": ["health", "fitness"],
  "summary": "Diagnosed with IT band syndrome affecting the left knee. Treatment includes daily foam rolling and specific exercises with a cap on long runs.",
  "action_items": [
    {
      "description": "Perform daily foam rolling",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Do glute bridges and clamshells 3x15 daily",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Cap long runs at 12 km for two weeks",
      "due": "2026-10-02",
      "priority": "medium"
    },
    {
      "description": "Attend follow-up appointment with Dr. Neha Shah",
      "due": "2026-09-29",
      "priority": "high"
    }
  ],
  "entities
```
</details>

<details><summary>a024 r1 - failed</summary>

```
{
  "title": "Vitamin D deficiency and doctor's prescription",
  "note_type": "health",
  "tags": ["health", "fitness", "learning"],
  "summary": "Annual checkup shows low Vitamin D levels at 14 ng/mL. Doctor prescribed weekly supplementation for 8 weeks with a recheck scheduled for November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "8 weeks",
    "November"
  ]
}
```
</details>

<details><summary>a025 r1 - ok_retry</summary>

```
{
  "title": "Follow up with Kabir on analytics dashboard",
  "note_type": "meeting",
  "tags": ["work", "team", "productivity"],
  "summary": "Schedule a catch-up with Kabir to discuss post-launch analytics dashboard progress and consider Q1 OKRs.",
  "action_items": [
    {
      "description": "Catch up with Kabir on post-launch analytics dashboard",
      "due": "2026-11-02",
      "priority": "medium"
    },
    {
      "description": "Review and define Q1 OKRs",
      "due": null,
      "priority": "medium"
    }
  ],
  "entities": [
    "Kabir",
    "post-launch analytics dashboard",
    "Q1 OKRs"
  ]
}
```
</details>

## prompt_only / temp 0.7 / Track A  (42 failures)
- 18 x `note_type: Input should be 'idea', 'meeting', 'journal', 'reading', 'todo' or 'reference'`
- 18 x `tags.2: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 6 x `summary: Value error, summary must be at most 2 sentences`
- 3 x `tags.1: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `tags.3: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`
- 3 x `tags.0: Input should be 'work', 'design', 'engineering', 'career', 'learning', 'reading', 'health', 'fitness', 'finance', 'travel', 'family'`

<details><summary>a013 r1 - failed</summary>

```
{
  "title": "Physio Follow-up: IT Band Syndrome",
  "note_type": "health",
  "tags": ["health", "fitness"],
  "summary": "Diagnosed with IT band syndrome affecting the left knee. Treatment includes daily foam rolling and specific exercises, with a cap on long runs at 12 km for two weeks.",
  "action_items": [
    {
      "description": "Perform daily foam rolling",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Do glute bridges and clamshells 3x15 daily",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Cap long runs at 12 km for two weeks",
      "due": "2026-10-02",
      "priority": "medium"
    },
    {
      "description": "Attend follow-up appointment with Dr. Neha Shah",
      "due": "2026-09-29",
      "priority": "high
```
</details>

<details><summary>a024 r1 - failed</summary>

```
{
  "title": "Vitamin D deficiency and treatment plan",
  "note_type": "health",
  "tags": ["health", "fitness", "wellness"],
  "summary": "Annual checkup shows low Vitamin D levels at 14 ng/mL. Doctor recommends a 60,000 IU weekly supplement for 8 weeks with a blood test recheck in November.",
  "action_items": [
    {
      "description": "Take 60,000 IU of Vitamin D once weekly for 8 weeks",
      "due": null,
      "priority": "high"
    },
    {
      "description": "Recheck blood test in November",
      "due": "2026-11-30",
      "priority": "medium"
    }
  ],
  "entities": [
    "Vitamin D",
    "doctor",
    "60,000 IU",
    "8 weeks",
    "blood test",
    "November"
  ]
}
```
</details>

<details><summary>a025 r1 - ok_retry</summary>

```
{
  "title": "Follow up with Kabir on analytics dashboard",
  "note_type": "meeting",
  "tags": ["work", "team", "communication"],
  "summary": "Schedule a catch-up with Kabir to discuss post-launch analytics dashboard progress and review Q1 OKRs.",
  "action_items": [
    {
      "description": "Schedule a meeting with Kabir to discuss post-launch analytics dashboard",
      "due": "2026-11-02",
      "priority": "medium"
    },
    {
      "description": "Review and formulate Q1 OKRs",
      "due": null,
      "priority": "medium"
    }
  ],
  "entities": [
    "Kabir",
    "post-launch analytics dashboard",
    "Q1 OKRs"
  ]
}
```
</details>
