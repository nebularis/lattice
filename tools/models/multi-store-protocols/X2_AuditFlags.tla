\* SPDX-License-Identifier: MPL-2.0
---------------------------- MODULE X2_AuditFlags ----------------------------
(***************************************************************************)
(* X2's audit, settled by a run. The module extends                        *)
(* X2_EvidenceAcrossStores.tla and changes nothing in it. It adds one      *)
(* invariant, that a decision the audit flags carries evidence that        *)
(* differs from what S held at its position. AuditFindsStale says every    *)
(* stale decision is flagged. This says every flagged decision is stale,   *)
(* so the two together would make the audit exact.                         *)
(***************************************************************************)
EXTENDS X2_EvidenceAcrossStores

\* Once S has reached p, a flagged decision's value differs from what S
\* held at p.
FlaggedIsStale ==
    \A d \in recs : (d.p <= wm /\ Superseded(d)) => d.val # hist[d.p]

=============================================================================
