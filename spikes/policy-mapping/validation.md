# Validation

`generator/validate.py` loads the stated meaning and the bound meaning together, over the same model the instrument tests use (`MODEL` and `EVERY_SHAPE` in `tools/test_parameter_bindings.py`). That model is the specs and vocabularies of Foundation, Vocabulary, Quantification, Party, Eligibility, Wording, Behaviour and Instrument. It validates against both shape files of all eight layers with pyshacl, inference off, advanced on. The run took about 20 minutes.

| Severity | Count | What |
|---|---|---|
| Violation | 2 | Law I13: the bound definition of "Policy Period" still holds its two placeholders, `ins:valueFrom ex:InceptionDate` and `ins:valueFrom ex:ExpirationDate`. This is finding I-1, an instantiator defect |
| Warning | 20 | Law I17: a leaf with no stated meaning and no encoding status is not yet assessed. These are the 20 unassessed leaves of the clause map: 11 structural, 9 gaps |
| Info | 0 | |

The 20 warnings:

| Kind | Leaves |
|---|---|
| Structural (G11, G18) | `attestation`, `cpl-notice`, `cpl-recital`, `ccp-3-intro`, `gtc-16a`, `gtc-16b`, `def-continuity`, `def-coverage-section`, `def-retroactive`, `def-separate-limit`, `def-shared-limit` |
| Gap | `item-4` (G13), `item-7` (G14), `gtc-6b` (G14), `gtc-8` (G1), `gtc-9` (G13), `gtc-13` (G16), `gtc-14` (G17), `ccp-3a-imputation` (G21), `ccp-4` (G1) |

## Corrected during the run

The first run also gave 38 violations of my own making. I had declared the 19 money variables' value space as the unit `ex:usd` in place of the space `ex:usd-space`. That fails Wording's value space shape, and then W6, since the stored quantities were on another space. Fixed in the generator, regenerated and re-run. Those results are the ones above.

## What the shapes did not catch

The checks are structural. These findings pass every shape:

- I-2: a generated condition with no evidence binding.
- I-3: a trigger read two ways.
- G2: a qualifier that should cover several relations and names one.
- The 16 ungoverned activities (I-4).
