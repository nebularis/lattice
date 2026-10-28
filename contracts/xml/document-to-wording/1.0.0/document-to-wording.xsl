<?xml version="1.0" encoding="UTF-8"?>
<!-- SPDX-License-Identifier: MPL-2.0 -->
<!--
  Ingress kit: a document in LATTICE's markup (ADR-A137) to its Wording graph, as canonical sorted
  N-Triples (ADR-A119). Plain XSLT 3.0 with no extension function, so any conformant processor gives
  the same output. A section is the document's n-th section, and an element the n-th clause or
  definition of its section, so unmarked text numbers nothing.
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:d="https://www.nebularis.org/neuro-semantic/lattice/document/1"
    xmlns:k="urn:lattice:kit:document-to-wording"
    exclude-result-prefixes="#all">

  <xsl:output method="text" encoding="UTF-8"/>

  <!-- The base every instance IRI is minted under. It ends with a slash. -->
  <xsl:param name="base" as="xs:string" required="yes"/>
  <!-- The revision of the document this graph records, from 1. -->
  <xsl:param name="revision" as="xs:integer" required="yes"/>

  <xsl:variable name="RDF" select="'http://www.w3.org/1999/02/22-rdf-syntax-ns#'"/>
  <xsl:variable name="RDFS" select="'http://www.w3.org/2000/01/rdf-schema#'"/>
  <xsl:variable name="XSD" select="'http://www.w3.org/2001/XMLSchema#'"/>
  <xsl:variable name="DCT" select="'http://purl.org/dc/terms/'"/>
  <xsl:variable name="WRD" select="'https://www.nebularis.org/neuro-semantic/lattice/wording#'"/>
  <xsl:variable name="WAP" select="'https://www.nebularis.org/neuro-semantic/lattice/poc/word-authoring#'"/>

  <xsl:template match="/">
    <xsl:if test="not(ends-with($base, '/'))">
      <xsl:message terminate="yes">base must end with '/'</xsl:message>
    </xsl:if>
    <xsl:if test="$revision lt 1">
      <xsl:message terminate="yes">revision is at least 1</xsl:message>
    </xsl:if>
    <xsl:variable name="lines" as="xs:string*">
      <xsl:apply-templates select="d:document"/>
    </xsl:variable>
    <xsl:for-each select="distinct-values($lines)">
      <xsl:sort select="." collation="http://www.w3.org/2005/xpath-functions/collation/codepoint"/>
      <xsl:value-of select="concat(., '&#10;')"/>
    </xsl:for-each>
  </xsl:template>

  <xsl:template match="d:document">
    <xsl:variable name="doc" select="k:doc(@id)"/>
    <xsl:variable name="w" select="$doc || 'wording'"/>
    <xsl:sequence select="k:t($w, $RDF || 'type', k:i($WRD || 'Wording'))"/>
    <xsl:sequence select="k:t($w, $DCT || 'title', k:s(d:meta/d:title))"/>
    <xsl:sequence select="k:t($w, $WAP || 'documentId', k:s(@id))"/>
    <xsl:sequence select="k:t($w, $WAP || 'templateId', k:s(d:meta/d:template))"/>
    <xsl:sequence select="k:t($w, $WAP || 'revisionNumber', k:int($revision))"/>
    <xsl:for-each select="d:body/d:section">
      <xsl:variable name="s" select="position()"/>
      <xsl:variable name="sec" select="$doc || 'section/' || @key"/>
      <xsl:sequence select="k:t($w, $WRD || 'directlyComprises', k:i($sec))"/>
      <xsl:sequence select="k:t($sec, $RDF || 'type', k:i($WRD || 'Element'))"/>
      <xsl:sequence select="k:t($sec, $WRD || 'elementType', k:i($WAP || 'Section'))"/>
      <xsl:sequence select="k:t($sec, $WAP || 'sectionKey', k:s(@key))"/>
      <xsl:sequence select="k:t($sec, $WRD || 'rankKey', k:s(k:rank('s', $s - 1)))"/>
      <xsl:sequence select="k:t($sec, $WRD || 'objectId', k:s(string($s)))"/>
      <xsl:for-each select="d:clause | d:definition">
        <xsl:variable name="e" select="position()"/>
        <xsl:variable name="el" select="$doc || 'element/' || @id"/>
        <xsl:variable name="definition" select="exists(self::d:definition)"/>
        <xsl:sequence select="k:t($sec, $WRD || 'directlyComprises', k:i($el))"/>
        <xsl:sequence select="k:t($el, $RDF || 'type', k:i($WRD || 'Text'))"/>
        <xsl:if test="$definition">
          <xsl:sequence select="k:t($el, $RDF || 'type', k:i($WAP || 'DefinitionText'))"/>
          <xsl:sequence select="k:t($el, $WAP || 'definedTerm', k:s(@term))"/>
        </xsl:if>
        <xsl:sequence select="k:t($el, $WRD || 'elementType', k:i($WAP || (if ($definition) then 'Definition' else 'Clause')))"/>
        <xsl:sequence select="k:t($el, $WAP || 'elementId', k:s(@id))"/>
        <xsl:sequence select="k:t($el, $WRD || 'rankKey', k:s(k:rank('e', $e - 1)))"/>
        <xsl:sequence select="k:t($el, $WRD || 'objectId', k:s($s || '.' || $e))"/>
        <xsl:sequence select="k:t($el, $WAP || 'plainText', k:s(string(.)))"/>
        <xsl:for-each select="node()[self::text() or self::d:var or self::d:ref]">
          <xsl:variable name="i" select="position() - 1"/>
          <xsl:variable name="part" select="$el || '/part/' || $i"/>
          <xsl:sequence select="k:t($el, $WAP || 'hasPart', k:i($part))"/>
          <xsl:sequence select="k:t($part, $RDF || 'type', k:i($WRD || 'TextPart'))"/>
          <xsl:sequence select="k:t($part, $WRD || 'partIndex', k:int($i))"/>
          <xsl:choose>
            <xsl:when test="self::text()">
              <xsl:sequence select="k:t($part, $WRD || 'partText', k:s(string(.)))"/>
            </xsl:when>
            <xsl:when test="self::d:var">
              <xsl:sequence select="k:t($part, $WRD || 'refersToVariable', k:i($doc || 'variable/' || @key))"/>
              <xsl:sequence select="k:t($part, $WAP || 'displayText', k:s(string(.)))"/>
            </xsl:when>
            <xsl:otherwise>
              <xsl:sequence select="k:t($part, $WRD || 'refersToObject', k:i($doc || 'element/' || @target))"/>
              <xsl:sequence select="k:t($part, $WAP || 'displayText', k:s(string(.)))"/>
            </xsl:otherwise>
          </xsl:choose>
        </xsl:for-each>
      </xsl:for-each>
    </xsl:for-each>
    <xsl:for-each select="d:meta/d:variable">
      <xsl:variable name="v" select="$doc || 'variable/' || @key"/>
      <xsl:sequence select="k:t($w, $WRD || 'directlyComprises', k:i($v))"/>
      <xsl:sequence select="k:t($v, $RDF || 'type', k:i($WRD || 'EmbeddedVariable'))"/>
      <xsl:sequence select="k:t($v, $WRD || 'variableKey', k:s(@key))"/>
      <xsl:sequence select="k:t($v, $RDFS || 'label', k:s(string(.)))"/>
      <xsl:sequence select="k:t($v, $WAP || 'valueType', k:i($WAP || upper-case(substring(@type, 1, 1)) || substring(@type, 2)))"/>
      <xsl:sequence select="k:t($v, $WRD || 'rankKey', k:s(k:rank('v', position() - 1)))"/>
    </xsl:for-each>
  </xsl:template>

  <xsl:function name="k:doc" as="xs:string">
    <xsl:param name="id" as="xs:string"/>
    <xsl:sequence select="$base || 'doc/' || $id || '/'"/>
  </xsl:function>

  <xsl:function name="k:t" as="xs:string">
    <xsl:param name="s" as="xs:string"/>
    <xsl:param name="p" as="xs:string"/>
    <xsl:param name="o" as="xs:string"/>
    <xsl:sequence select="'&lt;' || $s || '&gt; &lt;' || $p || '&gt; ' || $o || ' .'"/>
  </xsl:function>

  <xsl:function name="k:i" as="xs:string">
    <xsl:param name="iri" as="xs:string"/>
    <xsl:sequence select="'&lt;' || $iri || '&gt;'"/>
  </xsl:function>

  <!-- A plain literal, escaped as N-Triples requires. -->
  <xsl:function name="k:s" as="xs:string">
    <xsl:param name="text" as="xs:string"/>
    <xsl:variable name="e1" select="replace($text, '\\', '\\\\')"/>
    <xsl:variable name="e2" select="replace($e1, '&quot;', '\\&quot;')"/>
    <xsl:variable name="e3" select="replace($e2, '&#10;', '\\n')"/>
    <xsl:variable name="e4" select="replace($e3, '&#13;', '\\r')"/>
    <xsl:variable name="e5" select="replace($e4, '&#9;', '\\t')"/>
    <xsl:sequence select="'&quot;' || $e5 || '&quot;'"/>
  </xsl:function>

  <xsl:function name="k:int" as="xs:string">
    <xsl:param name="n" as="xs:integer"/>
    <xsl:sequence select="'&quot;' || $n || '&quot;^^&lt;' || $XSD || 'integer&gt;'"/>
  </xsl:function>

  <xsl:function name="k:rank" as="xs:string">
    <xsl:param name="prefix" as="xs:string"/>
    <xsl:param name="n" as="xs:integer"/>
    <xsl:sequence select="$prefix || format-integer($n, '0000')"/>
  </xsl:function>
</xsl:stylesheet>
