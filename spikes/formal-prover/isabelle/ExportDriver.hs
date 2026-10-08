-- Driver for the exported Haskell kernel (M5): checks the same reference fixtures as
-- Adequacy.thy, run as plain Haskell outside Isabelle entirely.
module Main (main) where

import Formal_Methods_Kernel (Decision (..), every_value, neg3, some_value)
import System.Exit (exitFailure)

showDecision :: Decision -> String
showDecision Permitted = "Permitted"
showDecision Denied = "Denied"
showDecision Undetermined = "Undetermined"

check :: String -> Decision -> Decision -> IO ()
check name actual expected =
  if sameDecision actual expected
    then putStrLn ("ok   " ++ name ++ " = " ++ showDecision actual)
    else do
      putStrLn ("FAIL " ++ name ++ " = " ++ showDecision actual ++ ", expected " ++ showDecision expected)
      exitFailure

sameDecision :: Decision -> Decision -> Bool
sameDecision Permitted Permitted = True
sameDecision Denied Denied = True
sameDecision Undetermined Undetermined = True
sameDecision _ _ = False

main :: IO ()
main = do
  check "some(pd)" (some_value [Permitted, Denied]) Permitted
  check "every(pd)" (every_value [Permitted, Denied]) Denied
  check "some(dd)" (some_value [Denied, Denied]) Denied
  check "every(dd)" (every_value [Denied, Denied]) Denied
  check "some(du)" (some_value [Denied, Undetermined]) Undetermined
  check "every(du)" (every_value [Denied, Undetermined]) Denied
  check "some(pp)" (some_value [Permitted, Permitted]) Permitted
  check "every(pp)" (every_value [Permitted, Permitted]) Permitted
  check "some(pu)" (some_value [Permitted, Undetermined]) Permitted
  check "every(pu)" (every_value [Permitted, Undetermined]) Undetermined
  check "some(none)" (some_value []) Undetermined
  check "every(none)" (every_value []) Undetermined
  check "neg(some(pd))" (neg3 (some_value [Permitted, Denied])) Denied
  check "neg(some(dd))" (neg3 (some_value [Denied, Denied])) Permitted
  check "neg(some(du))" (neg3 (some_value [Denied, Undetermined])) Undetermined
  putStrLn "all reference fixtures matched by the exported Haskell kernel"
