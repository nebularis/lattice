{-# LANGUAGE EmptyDataDecls, RankNTypes, ScopedTypeVariables #-}

module Formal_Methods_Kernel(Decision(..), neg3, some_value, every_value)
  where {

import Prelude ((==), (/=), (<), (<=), (>=), (>), (+), (-), (*), (/), (**),
  (>>=), (>>), (=<<), (&&), (||), (^), (^^), (.), ($), ($!), (++), (!!), Eq,
  error, id, return, not, fst, snd, map, filter, concat, concatMap, reverse,
  zip, null, takeWhile, dropWhile, all, any, Integer, negate, abs, divMod,
  String, Bool(True, False), Maybe(Nothing, Just));
import Data.Bits ((.&.), (.|.), (.^.));
import qualified Prelude;
import qualified Data.Bits;

data Decision = Permitted | Denied | Undetermined;

fold :: forall a b. (a -> b -> b) -> [a] -> b -> b;
fold f [] s = s;
fold f (x : xs) s = fold f xs (f x s);

or3 :: Decision -> Decision -> Decision;
or3 Permitted uu = Permitted;
or3 Denied b = b;
or3 Undetermined Permitted = Permitted;
or3 Undetermined Denied = Undetermined;
or3 Undetermined Undetermined = Undetermined;

and3 :: Decision -> Decision -> Decision;
and3 Permitted b = b;
and3 Denied uu = Denied;
and3 Undetermined Permitted = Undetermined;
and3 Undetermined Denied = Denied;
and3 Undetermined Undetermined = Undetermined;

neg3 :: Decision -> Decision;
neg3 Permitted = Denied;
neg3 Denied = Permitted;
neg3 Undetermined = Undetermined;

some_value :: [Decision] -> Decision;
some_value [] = Undetermined;
some_value (x : xs) = fold or3 xs x;

every_value :: [Decision] -> Decision;
every_value [] = Undetermined;
every_value (x : xs) = fold and3 xs x;

}
