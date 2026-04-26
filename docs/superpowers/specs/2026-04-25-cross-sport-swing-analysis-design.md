# Cross-Sport Swing Analysis Design

## Goal

Extend the swing analyzer so it can support both baseball and softball without splitting the core biomechanics pipeline into separate products. The system should automatically classify a job as `baseball`, `softball`, or `neutral`, and then use that profile to adjust interpretation, coaching language, and projection messaging.

## Product Contract

- The app must support baseball swings, softball swings, and ambiguous swings.
- Sport detection is automatic.
- The app only commits to a sport label when it has strong evidence.
- If evidence is weak or conflicting, the job remains in `neutral` mode for the full lifecycle of that job.
- `neutral` mode still performs full swing analysis, but it avoids baseball-only or softball-only assumptions.

## Why This Approach

Most of the existing pipeline is already sport-agnostic at the mechanics level: pose estimation, phase labeling, kinematic extraction, viewer rendering, and projection all operate on body motion rather than sport-specific metadata. The product is currently baseball-specific mainly in language, thresholds, and expectations.

Because of that, the correct first move is not to fork the analyzer. The right move is to add a sport profile layer above the shared pipeline and let that layer shape downstream interpretation.

## Alternatives Considered

### 1. Shared pipeline with sport-aware interpretation

Use one analysis path for pose, phases, and metrics. Add a `sport_profile` field and let it drive wording, thresholds, and calibration.

Pros:
- Smallest architectural change
- Reuses existing analysis investments
- Keeps testing surface manageable
- Easiest to extend incrementally

Cons:
- Some sport-specific nuances remain approximations until we add more sport-aware modeling

Recommendation: yes

### 2. Partially forked downstream analyzers

Keep ingest and pose shared, but split metrics/coaching/projection by sport.

Pros:
- More room for sport-specific tuning

Cons:
- Higher maintenance cost
- Easier to drift behavior between sports
- Harder to reason about regressions

Recommendation: not yet

### 3. Fully separate baseball and softball analyzers

Build independent products with separate rules and data contracts.

Pros:
- Maximum specialization

Cons:
- Heavy duplication
- High long-term complexity
- Premature for current maturity

Recommendation: no

## Architecture

### 1. Sport Profile

Every analyzed job gets a `sport_profile` object with:

- `label`: `baseball` | `softball` | `neutral`
- `confidence`: float `0.0..1.0`
- `context_confidence`: float `0.0..1.0`
- `mechanics_confidence`: float `0.0..1.0`
- `reasons`: short list of evidence strings for observability and debugging

This profile is computed once near the start of analysis and then attached to job metadata, results, and any downstream viewer/projection responses that need it.

### 2. Detection Logic

Detection uses two evidence buckets:

- `context_evidence`
  - scene and field cues
  - pitcher release style if visible
  - mound / circle / distance cues
  - overall environmental hints

- `mechanics_evidence`
  - setup posture and hand position
  - plane / approach characteristics
  - swing pattern cues that lean baseball vs softball

The labeling rule is:

- If both evidence buckets strongly support `baseball`, label `baseball`
- If both evidence buckets strongly support `softball`, label `softball`
- Otherwise label `neutral`

There is no late relabeling. Once the job is `neutral`, it stays `neutral`.

### 3. Shared Core Pipeline

The following remain shared:

- upload and job queue
- frame sampling
- pose inference
- 2D and heuristic 3D reconstruction
- phase detection
- core kinematic metrics
- viewer data generation

This keeps one canonical definition of contact frame, hip/shoulder angles, head drift, and similar shared mechanics.

### 4. Sport-Aware Interpretation Layer

Once the shared analysis finishes, sport profile affects:

- coaching copy
- threshold interpretation
- summary labels
- projection calibration copy
- any sport-specific UI language

The intent is:

- same motion model
- different interpretation rules

### 5. Neutral Mode

Neutral mode is a first-class outcome, not an error state.

Neutral mode behavior:

- analyze the swing normally
- show generic hitting language
- use conservative, shared thresholds
- avoid baseball-only references like mound, infield carry assumptions, or pitch-model assumptions
- avoid softball-only references unless sport was confidently detected

## API and Data Contract

### Backend

Results payload gains a `sport_profile` field. Projection payloads should also expose the profile when relevant so the frontend can render consistent labels.

Example shape:

```json
{
  "sport_profile": {
    "label": "neutral",
    "confidence": 0.42,
    "context_confidence": 0.38,
    "mechanics_confidence": 0.46,
    "reasons": [
      "Field context ambiguous",
      "Mechanics do not strongly separate baseball from softball"
    ]
  }
}
```

### Frontend

The results page and viewer should surface:

- `Detected sport: Baseball`
- `Detected sport: Softball`
- `Detected sport: Neutral`

If neutral:

- show a short note that no strong sport signal was found
- continue with generic swing analysis language

## UI Behavior

### Results Page

- Remove any implication that the app is baseball-only
- Show sport profile near the top summary area
- If neutral, explain the fallback clearly but briefly

### Viewer

- Keep the 3D viewer shared
- Replace baseball-only labels with sport-aware or generic wording
- What If panel should avoid pretending it knows measured baseball outcomes when sport is neutral

### Upload / Waiting Flow

This design does not require a visible user sport choice in the upload flow. Detection is automatic. If we later add a correction affordance, it should be optional and explicitly separate from the initial classifier.

## Thresholding Strategy

Initial implementation should use sport-specific thresholds only where the current rules already encode obvious assumptions. Avoid a full threshold rewrite in this phase.

Priority areas:

- coaching rules
- projection copy and estimate framing
- any flagging logic that implies baseball-specific expectations

Do not block this phase on perfect softball-specific calibration. It is acceptable to start with:

- baseball thresholds
- softball thresholds where obvious
- neutral shared fallback everywhere else

## Observability

We need enough traceability to debug wrong sport calls without guessing.

Minimum observability:

- log the chosen `sport_profile`
- persist it with results
- expose reasons in the API

This supports future tuning without needing to reconstruct decisions from raw logs.

## Testing Strategy

We do not need perfect real-world sport classification coverage in this first pass, but we do need deterministic tests for the contract.

Required tests:

- strong baseball signals -> `baseball`
- strong softball signals -> `softball`
- mixed or weak signals -> `neutral`
- neutral jobs do not emit baseball-only copy
- existing baseball flows keep working with the new result shape

Fixture-driven tests are enough initially as long as they validate the contract, not brittle visual details.

## Non-Goals

This phase does not:

- build separate baseball and softball analyzers
- retrain the pose or phase models
- guarantee perfect real-world sport detection
- add ball-tracking or true sport-specific exit-velocity calibration

## Success Criteria

This design is successful when:

1. Every completed job has a `sport_profile`
2. Clearly baseball clips classify as `baseball`
3. Clearly softball clips classify as `softball`
4. Ambiguous clips classify as `neutral`
5. Neutral mode uses generic swing-analysis wording throughout results and viewer
6. The current baseball flow continues to work without regression

## Open Follow-Up

If this phase works well, the next layer of improvement is not a split pipeline. The next layer is better evidence quality:

- stronger context cues
- better softball/baseball fixture coverage
- optional user correction after analysis
- better sport-specific coaching calibration
