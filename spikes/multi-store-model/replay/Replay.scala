// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

// Replays histories through the interpreter Isabelle exports from the multi-store model
// (Export.thy), used as generated. This driver parses the histories, builds the model's values,
// calls the generated exec_literal and replay_literal, and prints the state. It computes nothing
// the model computes.
//
// Usage: Replay check <histories.tsv> <out>            the outcome and the state after every command
//        Replay time <histories.tsv> <out> <rounds>    the time of each round of every history

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters.*

object Replay {
  val M = MultiStoreModel
  type State = List[(MultiStoreModel.res[String], MultiStoreModel.entry[String])]
  type Params = List[(MultiStoreModel.pname, MultiStoreModel.vala[String])]
  type Step = (MultiStoreModel.vala[String], (Params, MultiStoreModel.command[String]))

  final case class History(name: String, seed: State, steps: List[Step])

  val clock: MultiStoreModel.vala[String] = M.Atom[String]("T")

  def num(n: String): MultiStoreModel.vala[String] = M.Numa[String](M.nat_of_integer(BigInt(n)))

  val pnames: Map[String, MultiStoreModel.pname] = Map(
    "Root" -> M.Root(), "Stream" -> M.Stream(), "EpochP" -> M.Epochp(), "ExpectedSeq" -> M.Expectedseq(),
    "NewRev" -> M.Newrev(), "TxnId" -> M.Txnid(), "RequestDigest" -> M.Requestdigest(), "RevBase" -> M.Revbase(),
    "ClaimP" -> M.Claimp(), "OwnerP" -> M.Ownerp(), "Payload" -> M.Payload(), "Asserted" -> M.Asserted(),
    "Retracted" -> M.Retracted(), "EventRows" -> M.Eventrows())

  def command(op: String, arg: String): MultiStoreModel.command[String] = op match {
    case "create" => M.create_if_absent[String]
    case "replace" => M.delta_replace[String]
    case "append" => M.append_event[String]
    case "claim" => M.key_claim_write[String](arg)
    case other => sys.error(s"unknown command $other")
  }

  // The histories file: one record a line, fields split by tabs.
  //   H name | SV root epoch seq head | SD epoch | SA root fact
  //   C op arg | PA pname atom | PN pname n | PF pname fact | PE pname (an empty list of facts)
  def parse(path: String): List[History] = {
    val lines = Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8).asScala.toList.filter(_.nonEmpty)
    val histories = scala.collection.mutable.ListBuffer[History]()
    var name: String = null
    var vrows = Vector[(String, String, String, String)]()
    var aggs = Vector[(String, String)]()
    var depoch: Option[String] = None
    var steps = Vector[(String, String, Vector[(String, MultiStoreModel.vala[String])])]()

    def flush(): Unit = if (name != null) {
      val seedRows: State = vrows.toList.map { case (root, epoch, seq, head) =>
        val fields = List[(MultiStoreModel.field, MultiStoreModel.vala[String])]((M.Epoch(), num(epoch)), (M.Seq(), num(seq))) ++
          (if (head.isEmpty) Nil else List((M.Head(), M.Atom[String](head))))
        (M.Kvrow[String](M.Atom[String](root)), M.Entrya[String](fields, M.seta[String](Nil)))
      }
      val seedAggs: State = aggs.groupBy(_._1).toList.sortBy(_._1).map { case (root, facts) =>
        (M.Kagg[String](M.Atom[String](root)), M.Entrya[String](Nil, M.seta[String](facts.map(_._2).toList)))
      }
      val seedDepoch: State = depoch.toList.map(e => (M.Kdepoch[String](), M.Entrya[String](List((M.Epoch(), num(e))), M.seta[String](Nil))))
      val built: List[Step] = steps.toList.map { case (op, arg, ps) =>
        // A parameter named twice is a list of facts, gathered in order.
        val merged = ps.foldLeft(Vector[(String, MultiStoreModel.vala[String])]()) { case (acc, (p, v)) =>
          (acc.indexWhere(_._1 == p), v) match {
            case (-1, _) => acc :+ (p, v)
            case (i, M.Facts(more)) => acc(i)._2 match {
              case M.Facts(have) => acc.updated(i, (p, M.Facts[String](have ++ more)))
              case _ => sys.error(s"parameter $p is both a value and facts")
            }
            case _ => sys.error(s"parameter $p given twice")
          }
        }
        val params: Params = merged.toList.map { case (p, v) => (pnames(p), v) }
        (clock, (params, command(op, arg)))
      }
      histories += History(name, seedRows ++ seedAggs ++ seedDepoch, built)
    }

    for (line <- lines) {
      val f = line.split("\t", -1)
      f(0) match {
        case "H" => flush(); name = f(1); vrows = Vector(); aggs = Vector(); depoch = None; steps = Vector()
        case "SV" => vrows :+= ((f(1), f(2), f(3), f(4)))
        case "SA" => aggs :+= ((f(1), f(2)))
        case "SD" => depoch = Some(f(1))
        case "C" => steps :+= ((f(1), f(2), Vector()))
        case "PA" => steps = steps.init :+ steps.last.copy(_3 = steps.last._3 :+ (f(1), M.Atom[String](f(2))))
        case "PN" => steps = steps.init :+ steps.last.copy(_3 = steps.last._3 :+ (f(1), num(f(2))))
        case "PF" => steps = steps.init :+ steps.last.copy(_3 = steps.last._3 :+ (f(1), M.Facts[String](List(f(2)))))
        case "PE" => steps = steps.init :+ steps.last.copy(_3 = steps.last._3 :+ (f(1), M.Facts[String](Nil)))
        case other => sys.error(s"unknown record $other")
      }
    }
    flush()
    histories.toList
  }

  // A value as text. A revision is decoded from its base and position, padded to 19 digits, as the
  // RDF realisation writes it.
  def render(v: MultiStoreModel.vala[String]): String = v match {
    case M.Atom(a) => a
    case M.Numa(n) => M.integer_of_nat(n).toString
    case M.Flag(b) => b.toString
    case M.Noval() => "-"
    case M.Facts(xs) => xs.mkString("|")
    case M.App(M.Revisioniri(), List(M.Atom(base), M.Numa(n))) => base + String.format("%019d", M.integer_of_nat(n).bigInteger)
    case M.App(_, args) => args.map(render).mkString("app(", ",", ")")
  }

  // A reason by the name the theory gives it. The Scala target's case_insensitive option renames
  // the generated classes, for example EpochMismatch to Epochmismatch.
  def reason(r: MultiStoreModel.reason): String = r match {
    case M.Exists() => "Exists"
    case M.Missing() => "Missing"
    case M.Tombstoned() => "Tombstoned"
    case M.Stale() => "Stale"
    case M.Heldbyother() => "HeldByOther"
    case M.Epochmismatch() => "EpochMismatch"
  }

  def outcome(o: MultiStoreModel.outcome): String = o match {
    case M.Applied() => "Applied"
    case M.Duplicate() => "Duplicate"
    case M.Conflict(r) => "Conflict " + reason(r)
    case M.Refused(r) => "Refused " + reason(r)
  }

  def dump(s: State): List[String] = {
    val out = scala.collection.mutable.ListBuffer[String]()
    for ((r, e) <- s) {
      val (fs, facts) = e match { case M.Entrya(fs, facts) => (fs, facts) }
      def f(x: MultiStoreModel.field): String =
        fs.collectFirst { case (k, v) if M.equal_fielda(k, x) => render(v) }.getOrElse("-")
      val fl: List[String] = facts match {
        case M.seta(xs) => xs
        case M.coset(_) => List("a cofinite set")
      }
      r match {
        case M.Kvrow(k) =>
          val deleted = if (f(M.Deleted()) == "true") "true" else "false"
          out += s"vrow\t${render(k)}\tepoch=${f(M.Epoch())}\tseq=${f(M.Seq())}\thead=${f(M.Head())}\tdeleted=$deleted"
        case M.Ktxn(k) => out += s"txn\t${render(k)}\trev=${f(M.Rev())}\tdigest=${f(M.Digest())}"
        case M.Krcpt(t, ep, n) =>
          out += s"rcpt\t${render(t)}\t${render(ep)}\t${render(n)}\trev=${f(M.Rev())}\tprev=${f(M.Prev())}\ttxn=${f(M.Txnof())}"
        case M.Kpatch(t, ep, n, d) =>
          val dir = d match { case M.Add() => "add"; case M.Del() => "del" }
          fl.foreach(x => out += s"patch\t${render(t)}\t${render(ep)}\t${render(n)}\t$dir\t$x")
        case M.Kagg(k) => fl.foreach(x => out += s"agg\t${render(k)}\t$x")
        case M.Kevt(st, n) =>
          fl.foreach(x => out += (if (x.startsWith("ROW ")) s"evrow\t${render(st)}\t${render(n)}\t${x.drop(4)}" else s"evfact\t$x"))
        case M.Kclaim(k) => out += s"claim\t${render(k)}\tconstraint=${f(M.Constraint())}\towner=${f(M.Owner())}"
        case M.Kdepoch() => out += s"depoch\t${f(M.Epoch())}"
      }
    }
    out.distinct.sorted.toList
  }

  def check(histories: List[History]): List[String] = histories.flatMap { h =>
    var s = h.seed
    val lines = scala.collection.mutable.ListBuffer[String](s"H\t${h.name}")
    for (((t, (ps, c)), i) <- h.steps.zipWithIndex) {
      val (s1, o) = M.exec_literal(s)(t)(ps)(c)
      lines += s"O\t${i + 1}\t${outcome(o)}"
      dump(s1).foreach(l => lines += s"S\t${i + 1}\t$l")
      s = s1
    }
    lines.toList
  }

  def time(histories: List[History], rounds: Int): List[String] = {
    var sink = 0L
    val ns = (1 to rounds).map { _ =>
      val t0 = System.nanoTime()
      for (h <- histories) sink += M.replay_literal(h.seed)(h.steps).length
      System.nanoTime() - t0
    }
    // The Scala 3 library's jar names its version, and its manifest does not.
    val scala3 = Option(classOf[scala.runtime.TupleXXL].getProtectionDomain.getCodeSource)
      .map(source => Paths.get(source.getLocation.toURI).getFileName.toString).getOrElse("unknown")
    List(
      s"scala\t$scala3\tlibrary\t${scala.util.Properties.versionNumberString}",
      s"java\t${System.getProperty("java.version")}\t${System.getProperty("java.vm.name")}",
      s"histories\t${histories.length}\tcommands\t${histories.map(_.steps.length).sum}\trounds\t$rounds",
      s"sink\t$sink"
    ) ++ ns.map(n => s"round_ns\t$n")
  }

  def main(argv: Array[String]): Unit = {
    // isabelle scala passes its compiler options ahead of the program's own arguments, so the
    // arguments start at the mode.
    val args = argv.dropWhile(a => a != "check" && a != "time")
    val histories = parse(args(1))
    val lines = args(0) match {
      case "check" => check(histories)
      case "time" => time(histories, args(3).toInt)
      case other => sys.error(s"unknown mode $other")
    }
    Files.write(Paths.get(args(2)), (lines.mkString("\n") + "\n").getBytes(StandardCharsets.UTF_8))
  }
}
