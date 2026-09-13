# Experimental projected readiness — model v1

**This is an unvalidated, rule-based readiness index, not a calibrated prediction of an exam grade or a probability of passing.** No exam-outcome training set was supplied. Weights, cutoffs and evidence requirements are design choices. A fitted prediction would require prospective validation against independent real exam outcomes, with calibration and subgroup checks. A disclaimer does not turn this index into a validated measurement.

The UI describes the output as “Projected exam readiness,” labels its evidence strength, and keeps this notice visible: “Experimental projected readiness, based on observed study patterns and self-marked card correctness. This is not a promise, guarantee, or certainty of your actual exam grade. It does not measure unrepresented material or replace case/application practice.”

## Inputs and exclusions

Selected decks, current card IDs and their exam-emphasis weights define the material. Topic text does not cause the add-on to read a syllabus or automatically understand the card content. Coverage only concerns the cards actually selected. A separately selected child owns its cards, preventing duplicate parent quotas. Missing/high-emphasis unmeasured material stays in the denominator. Zero emphasis excludes a topic.

The read-only adapter takes the first native review per card/UTC day over 90 days, then combines local session records and keeps only the first retrieval per **note/UTC day**. This makes same-day reverse/cloze siblings and repeated easy answers unable to multiply the evidence. This boundary differs from Anki's configurable study-day rollover. Native Again is a failure; Hard/Good/Easy are passes, not externally verified correctness. This is consistent with Anki's retention convention, but the combined note-day estimator is our own heuristic. Local self-marks use 0 / 0.5 / 1. Confidence never adds score points; confident mistakes are separately surfaced and prioritized.

Coverage uses actual **card variants**, so checking one cloze or image-occlusion sibling does not certify all the others. Exposures in other locally stored exams also prevent a misleading cold repeat. Only representative mocks for the target exam can satisfy that exam's broad-mock evidence requirement.

New-card native ratings are not counted a second time from the practice result: they already belong in Anki's review log. Interrupted sessions contribute completed valid marks only. Answered-but-unmarked questions and rendering errors do not become failures. An unanswered question in a completed mock receives no credit. Older results without item timing receive half evidence weight; records without original IDs cannot be reconstructed. The app retains at most 50 result summaries, so the local evidence history is bounded. A 250,000-event safety cap is disclosed if reached and caps readiness below B.

## Calculation

For each topic, observations have a 14-day half-life. A Beta(1,1) prior shrinks sparse correctness observations toward 0.5. At the exam date, projected recall is never greater than the current estimate merely because time has passed. This is **not FSRS retrievability** and does not change FSRS parameters.

The topic signal is:

`0.45 × observed recall + 0.25 × cold representative-mock recall + 0.20 × introduced-card coverage + 0.10 × delayed retrieval coverage`

When a cold mock is absent, observed recall substitutes for that recall component, but the overall A/S evidence gate remains closed. Multiply the signal by `0.65 + 0.35 × recent card-variant coverage`, and take the exam-emphasis-weighted mean across topics. Recent and delayed coverage use a 14-day window at the exam date. A native review is classed as delayed only if it was a review/relearning item with a preceding positive day interval; independent practice uses an observed last exposure at least 24 hours earlier. A strict cold-only draw excludes new cards, unknown exposure dates, and recently seen note siblings.

The projection assumes **no additional learning before the exam date**. This can make a distant exam look conservative; it is not a forecast of the effort you intend to do. A displayed sensitivity range describes the heuristic's evidence dispersion, **not** a real-exam confidence interval. Related cards, self-grading, selection bias and missing content violate the assumptions of an ordinary independent-trial grade estimate.

## Evidence gates

No usable answer evidence shows an em dash / collecting evidence, not F−. F− requires actual low measured evidence.

Low evidence means fewer than 20 distinct observed notes or fewer than two UTC study days: maximum 79. High evidence requires 80 observed notes, four days and 75% note coverage; this label describes quantity/breadth, not correctness or validation.

A cold representative mock must contain at least `min(30, eligible notes)` first daily note observations and represent at least 80% of the topic-emphasis weight. Without one, readiness is capped at 89. A topic holding at least 15% of exam emphasis but under 50% recent coverage caps the result at 79.

S additionally requires qualifying cold mocks on two separate days, High evidence, at least 90% weighted recent coverage, and at least 90 topic-index points in every topic carrying at least 10% of emphasis. Without these, the maximum is 98.

## App-specific tiers

| Minimum index | Tier |
|---:|:---|
| 99 | S |
| 97 | A+ |
| 93 | A |
| 90 | A− |
| 87 | B+ |
| 83 | B |
| 80 | B− |
| 77 | C+ |
| 73 | C |
| 70 | C− |
| 67 | D+ |
| 63 | D |
| 60 | D− |
| 50 | F+ |
| 30 | F |
| 0 | F− |

These are NOT the user's school's grade boundaries. 86/100 index is not a prediction of 86% on an exam. The scale cannot assess a case, calculation or clinical judgment absent from the source flashcards.

## Pip is separate

Pip grows from one effort point per uniquely studied note per UTC day, capped at 500/day, across exams. A wrong but honestly graded retrieval still counts as effort. Lifetime milestones: 0, 200, 600 and 1,600 points. The percentage is progress toward the next milestone, not exam readiness. Petting/watering add no points. Deleting an exam does not shrink Pip. New lifetime tracking begins with this feature; old readiness percentages are not converted into effort points.

## Primary references

Anki's first-review retention convention and review-log fields: https://docs.ankiweb.net/stats.html#true-retention-table and https://docs.ankiweb.net/stats.html#manual-analysis

Native grade operation surface (inspected, not a substitute for native tests): https://raw.githubusercontent.com/ankitects/anki/main/qt/aqt/operations/scheduling.py
