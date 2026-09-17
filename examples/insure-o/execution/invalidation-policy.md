# Invalidation policy

This execution package should be regenerated whenever either the substrate or the applied layer examples change. The policy is intentionally lightweight and follows the same optional realisation stance documented in ADR-A15.

## Trigger conditions

- changes to `behaviour/` allowance semantics
- changes to `eligibility/` match strategies or hierarchy rules
- changes to the `insure-o` applied layer T-box or scheme contracts
- changes to any example scenario using the runtime profile
