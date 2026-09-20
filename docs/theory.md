---
layout: theory
title: Theoretical Foundations
eyebrow: Why the substrate is shaped this way
dek: "LATTICE borrows one specific, named piece of mathematics or formal-methods theory at almost every layer — and it's always borrowed for the same reason: so that something derived can <em>prove</em> a safety property about itself, rather than asking a reader to trust it."
note: This page assumes no background in any of the theories it covers. Each section explains the idea in plain terms before showing exactly where LATTICE uses it and what it buys.
description: The mathematics underneath LATTICE — description logic, order theory, conservative extension, three-valued logic, category theory, session types, and determinism — and why each one is there.
---

<!--
  This page is a spine, not the content. Each section lives in its own small
  Markdown file under _includes/theory/ — edit those directly. Page chrome
  (CSS, topbar, TOC, footer, the Mermaid <script> setup) lives once, in
  _layouts/theory.html, not here and not per-section.
-->

{% include theory/00-thesis.md %}

{% include theory/01-description-logic.md %}

{% include theory/02-order-theory.md %}

{% include theory/03-conservative-extension.md %}

{% include theory/04-three-valued-logic.md %}

{% include theory/05-category-theory-mork.md %}

{% include theory/06-session-types-spc.md %}

{% include theory/07-determinism.md %}

{% include theory/08-one-thread.md %}

{% include theory/09-further-reading.md %}
