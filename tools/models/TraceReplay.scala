// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

// Replays the steps of the multi-store protocol models' traces through the interpreter Isabelle
// exports from the multi-store model (spikes/multi-store-model, Export.thy), used as generated.
// The traces arrive as a tree whose nodes share their common prefixes, so each step is run once. A
// root is a seed state. A node is one command of the IR, run by exec_literal on its parent's state,
// or one step the IR has no command for, the bump of the dataset epoch, which the driver writes into
// the state as the entry the IR reads. It reuses the spike's driver, replay/Replay.scala, for the
// commands, the parameters and the reading of a state, and computes nothing the model computes.
//
// Usage: TraceReplay tree <tree.tsv> <out>
//   R id                         a root, whose seed records follow
//   SV root epoch seq head       a version row of the seed, head empty for none
//   SD epoch                     the dataset epoch of the seed
//   N id parent C op arg         a command, whose parameters follow as PA, PN, PF and PE records
//   N id parent X depoch n       the dataset epoch set to n, a step the IR has no command for
// It writes, for each root and node in order, "O id outcome", with "-" where no command ran, and
// "S id line" for each line of the state after it, as Replay.dump reads a state.

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters.*

object TraceReplay {
  val M = MultiStoreModel
  type V = MultiStoreModel.vala[String]

  sealed trait Node
  final case class Root(id: Int, rows: Vector[(String, String, String, String)], depoch: Option[String]) extends Node
  final case class Cmd(id: Int, parent: Int, op: String, arg: String, params: Vector[(String, V)]) extends Node
  final case class Ext(id: Int, parent: Int, kind: String, value: String) extends Node

  def seed(rows: Vector[(String, String, String, String)], depoch: Option[String]): Replay.State = {
    val seedRows: Replay.State = rows.toList.map { case (root, epoch, seq, head) =>
      val fields = List[(MultiStoreModel.field, V)]((M.Epoch(), Replay.num(epoch)), (M.Seq(), Replay.num(seq))) ++
        (if (head.isEmpty) Nil else List((M.Head(), M.Atom[String](head))))
      (M.Kvrow[String](M.Atom[String](root)), M.Entrya[String](fields, M.seta[String](Nil)))
    }
    val seedDepoch: Replay.State = depoch.toList.map(e => depochEntry(e))
    seedRows ++ seedDepoch
  }

  def depochEntry(e: String): (MultiStoreModel.res[String], MultiStoreModel.entry[String]) =
    (M.Kdepoch[String](), M.Entrya[String](List((M.Epoch(), Replay.num(e))), M.seta[String](Nil)))

  // A parameter named twice is a list of facts, gathered in order, as Replay.parse gathers them.
  def params(ps: Vector[(String, V)]): Replay.Params = {
    val merged = ps.foldLeft(Vector[(String, V)]()) { case (acc, (p, v)) =>
      (acc.indexWhere(_._1 == p), v) match {
        case (-1, _) => acc :+ (p, v)
        case (i, M.Facts(more)) => acc(i)._2 match {
          case M.Facts(have) => acc.updated(i, (p, M.Facts[String](have ++ more)))
          case _ => sys.error(s"parameter $p is both a value and facts")
        }
        case _ => sys.error(s"parameter $p given twice")
      }
    }
    merged.toList.map { case (p, v) => (Replay.pnames(p), v) }
  }

  def parse(path: String): Vector[Node] = {
    val lines = Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8).asScala.toVector.filter(_.nonEmpty)
    var nodes = Vector[Node]()
    def addParam(p: (String, V)): Unit = nodes.last match {
      case c: Cmd => nodes = nodes.init :+ c.copy(params = c.params :+ p)
      case _ => sys.error("a parameter outside a command")
    }
    def addSeed(f: Root => Root): Unit = nodes.last match {
      case r: Root => nodes = nodes.init :+ f(r)
      case _ => sys.error("a seed record outside a root")
    }
    for (line <- lines) {
      val f = line.split("\t", -1)
      f(0) match {
        case "R" => nodes :+= Root(f(1).toInt, Vector(), None)
        case "SV" => addSeed(r => r.copy(rows = r.rows :+ ((f(1), f(2), f(3), f(4)))))
        case "SD" => addSeed(r => r.copy(depoch = Some(f(1))))
        case "N" if f(3) == "C" => nodes :+= Cmd(f(1).toInt, f(2).toInt, f(4), f(5), Vector())
        case "N" if f(3) == "X" => nodes :+= Ext(f(1).toInt, f(2).toInt, f(4), f(5))
        case "PA" => addParam((f(1), M.Atom[String](f(2))))
        case "PN" => addParam((f(1), Replay.num(f(2))))
        case "PF" => addParam((f(1), M.Facts[String](List(f(2)))))
        case "PE" => addParam((f(1), M.Facts[String](Nil)))
        case other => sys.error(s"unknown record $other")
      }
    }
    nodes
  }

  def run(nodes: Vector[Node]): List[String] = {
    val states = scala.collection.mutable.Map[Int, Replay.State]()
    val out = scala.collection.mutable.ListBuffer[String]()
    for (node <- nodes) {
      val (id, s, o) = node match {
        case Root(id, rows, depoch) => (id, seed(rows, depoch), "-")
        case Cmd(id, parent, op, arg, ps) =>
          val (s1, o) = M.exec_literal(states(parent))(Replay.clock)(params(ps))(Replay.command(op, arg))
          (id, s1, Replay.outcome(o))
        case Ext(id, parent, "depoch", n) =>
          val rest = states(parent).filterNot { case (r, _) => r match { case M.Kdepoch() => true; case _ => false } }
          (id, depochEntry(n) :: rest, "-")
        case Ext(_, _, kind, _) => sys.error(s"unknown step $kind")
      }
      states(id) = s
      out += s"O\t$id\t$o"
      Replay.dump(s).foreach(l => out += s"S\t$id\t$l")
    }
    out.toList
  }

  def main(argv: Array[String]): Unit = {
    // isabelle scala passes its compiler options ahead of the program's own arguments, so the
    // arguments start at the mode.
    val args = argv.dropWhile(_ != "tree")
    if (args.length < 3) sys.error("usage: TraceReplay tree <tree.tsv> <out>")
    val lines = run(parse(args(1)))
    Files.write(Paths.get(args(2)), (lines.mkString("\n") + "\n").getBytes(StandardCharsets.UTF_8))
  }
}
