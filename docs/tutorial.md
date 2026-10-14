---
layout: tutorial
title: The LATTICE Tutorial
eyebrow: Reading LATTICE, for data architects
dek: "One loan facility agreement, followed through every layer of LATTICE: its keys and versions, its wording, the legal relations it creates, its amounts, the rules for who may borrow, its covenant default and cure, its drawdowns, and how it is stored and served."
note: Written for a data architect with little exposure to ontologies. Each idea is introduced through its nearest data-architecture counterpart, with a note on where that counterpart misleads. Nothing here needs to be run.
description: A read-only tutorial for data architects, following one loan facility agreement through LATTICE's substrate layers and applied modules.
---

<!--
  SPDX-License-Identifier: CC-BY-SA-4.0

  This page is a spine, as docs/theory.md is. Each chapter lives in its own
  Markdown file under _includes/tutorial/. Edit those directly. Page chrome
  lives once, in _layouts/tutorial.html.

  A Turtle excerpt in a chapter is a fenced turtle block preceded by an HTML
  comment "source: <repository-relative path>", and must match that file.
  `mise run check:tutorial-snippets` checks it, and checks every link to
  https://github.com/nebularis/lattice/blob/main/... names a path that exists
  (docs/developer/plans/lattice-tutorial.md §5).
-->

{% include tutorial/00-why.md %}

{% include tutorial/01-tables-to-graphs.md %}

{% include tutorial/02-reading-turtle.md %}

{% include tutorial/03-layer-map.md %}

{% include tutorial/04-identity-and-keys.md %}

{% include tutorial/05-text-and-meaning.md %}

{% include tutorial/06-who-owes-what.md %}

{% include tutorial/07-amounts-and-reference-data.md %}

{% include tutorial/08-rules-for-admission.md %}

{% include tutorial/09-change-over-time.md %}

{% include tutorial/10-drawing-down.md %}

{% include tutorial/11-storing-and-serving.md %}

{% include tutorial/12-building-a-domain.md %}

{% include tutorial/13-where-next.md %}
