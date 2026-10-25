# Spark prompt and output samples

All ten examples below were produced with `AI_MODE=mock` and fictional seed data on 2026-10-24. They are deterministic local fixtures and fallback templates, **not live Meta responses**. The function inputs shown under **Prompt** are the facts supplied to Spark's user message; every call also applies the standing developer rules in `backend/app/ai/spark.py`: use only supplied facts, keep first steps brief and public, avoid addresses, and return schema-matching JSON. A draft remains editable until the human presses Send. The voice parse is a preview until the human presses Post.

## 1. Hyde Park gap nudge, small ask

**Prompt:** `make_nudge(you=You {interests: [dogs, coffee, board games, gardening], availability: [wed-evening, thu-evening, sat-morning]}, candidate=Priya {cluster: Duval St, interests: [dogs, coffee, board games, gardening], availability: [wed-evening, thu-evening, sat-morning]}, gap={Duval St, size: 6, reach: 0}, mode=small_ask)`

**Output:**

```json
{"headline":"You haven't met anyone on Duval St yet","why":"Priya also likes board games and coffee. You are both free sat morning.","first_step":"A wave and a hello in a public place is enough.","cta":"Draft a hello","draft_message":"Hi Priya! I noticed we both like board games and coffee. Would you like to take a short walk this week?"}
```

## 2. Hyde Park gap nudge for Sofia

**Prompt:** `make_nudge(you=You {interests: [dogs, coffee, board games, gardening], availability: [wed-evening, thu-evening, sat-morning]}, candidate=Sofia {cluster: Duval St, interests: [bikes, dogs], availability: [wed-evening, thu-evening, tue-evening]}, gap={Duval St, size: 6, reach: 0}, mode=small_ask)`

**Output:**

```json
{"headline":"You haven't met anyone on Duval St yet","why":"Sofia also likes dogs. You are both free thu evening.","first_step":"A wave and a hello in a public place is enough.","cta":"Draft a hello","draft_message":"Hi Sofia! I noticed we both like dogs. Would you like to take a short walk this week?"}
```

## 3. Quarry Lofts gap nudge, small ask

**Prompt:** `make_nudge(you=You {interests: [gaming, cooking, film, study groups], availability: [wed-evening, fri-evening, sat-afternoon]}, candidate=Imani {cluster: South Wing, interests: [gaming, cooking, film, study groups], availability: [wed-evening, fri-evening, sat-afternoon]}, gap={South Wing, size: 8, reach: 0}, mode=small_ask)`

**Output:**

```json
{"headline":"You haven't met anyone on South Wing yet","why":"Imani also likes cooking and film. You are both free fri evening.","first_step":"A wave and a hello in a public place is enough.","cta":"Draft a hello","draft_message":"Hi Imani! I noticed we both like cooking and film. Would you like to take a short walk this week?"}
```

## 4. Quarry Lofts gap nudge for Bea

**Prompt:** `make_nudge(you=You {interests: [gaming, cooking, film, study groups], availability: [wed-evening, fri-evening, sat-afternoon]}, candidate=Bea {cluster: South Wing, interests: [books, gaming], availability: [tue-evening, wed-evening]}, gap={South Wing, size: 8, reach: 0}, mode=small_ask)`

**Output:**

```json
{"headline":"You haven't met anyone on South Wing yet","why":"Bea also likes gaming. You are both free wed evening.","first_step":"A wave and a hello in a public place is enough.","cta":"Draft a hello","draft_message":"Hi Bea! I noticed we both like gaming. Would you like to take a short walk this week?"}
```

## 5. Draft to Priya

**Prompt:** `draft_message(community=Hyde Park, you=You {interests: [dogs, coffee, board games, gardening]}, recipient=Priya {interests: [dogs, coffee, board games, gardening]}, context="", tone=casual)`

**Output:** `Hi Priya! I noticed we both like board games. Want to say hello sometime this week?`

## 6. Draft to Sofia

**Prompt:** `draft_message(community=Hyde Park, you=You {interests: [dogs, coffee, board games, gardening]}, recipient=Sofia {interests: [bikes, dogs]}, context="", tone=casual)`

**Output:** `Hi Sofia! I noticed we both like dogs. Want to say hello sometime this week?`

## 7. Draft to Kian

**Prompt:** `draft_message(community=Hyde Park, you=You {interests: [dogs, coffee, board games, gardening]}, recipient=Kian {interests: [gardening, books]}, context="", tone=casual)`

**Output:** `Hi Kian! I noticed we both like gardening. Want to say hello sometime this week?`

## 8. Draft to Imani

**Prompt:** `draft_message(community=Quarry Lofts, you=You {interests: [gaming, cooking, film, study groups]}, recipient=Imani {interests: [gaming, cooking, film, study groups]}, context="", tone=casual)`

**Output:** `Hi Imani! I noticed we both like cooking. Want to say hello sometime this week?`

## 9. Draft to Bea

**Prompt:** `draft_message(community=Quarry Lofts, you=You {interests: [gaming, cooking, film, study groups]}, recipient=Bea {interests: [books, gaming]}, context="", tone=casual)`

**Output:** `Hi Bea! I noticed we both like gaming. Want to say hello sometime this week?`

## 10. Voice transcript to invite preview

**Prompt:** `parse_invite(transcript="Anyone want to play board games near Avenue G this Friday at six? Four spots.", host=You {community: Hyde Park, cluster: Avenue G}, now=2026-10-24T00:00:00+00:00)`

**Output:**

```json
{"title":"Board games this Friday","activity":"board games","starts_at":"2026-10-30T18:00:00-05:00","capacity":4,"place_hint":"near Avenue G","confidence":0.94}
```

The mock parser returns a fixed fixture for this exact example. H1 is complete; live parsing, current-date handling, and hallucination checks still need a targeted Phase 6 verification run. None of these outputs contains a house number, unit, or exact resident coordinate.
