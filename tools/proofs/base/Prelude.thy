(* The prelude, LatticeBase (ADR-A-FM2's addendum of 2026-11-08, plan formal-methods-track-e,
   FME-0). It imports the nineteen HOL-Library theories of the HOL sessions survey's section 7,
   docs/developer/sketches/hol-sessions-survey.md, which records why each is here, and nothing
   else. It states no law and carries no claim. Adding a theory is one import here, reviewed once. *)

theory Prelude
  imports
    "HOL-Library.Multiset"
    "HOL-Library.Sublist"
    "HOL-Library.FSet"
    "HOL-Library.Finite_Map"
    "HOL-Library.Mapping"
    "HOL-Library.Option_ord"
    "HOL-Library.Product_Order"
    "HOL-Library.Order_Continuity"
    "HOL-Library.Complete_Partial_Order2"
    "HOL-Library.While_Combinator"
    "HOL-Library.Interval"
    "HOL-Library.Disjoint_Sets"
    "HOL-Library.Extended_Nat"
    "HOL-Library.Stream"
    "HOL-Library.Linear_Temporal_Logic_on_Streams"
    "HOL-Library.Monad_Syntax"
    "HOL-Library.Code_Target_Numeral"
    "HOL-Library.Code_Abstract_Char"
    "HOL-Library.RBT_Mapping"
begin

end
