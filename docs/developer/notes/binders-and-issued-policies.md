<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Binders, cover notes and issued policies: how jurisdictions treat interim cover

**Status:** developer note, 2026-10-21, research for the phase 7 plan's P7-Q9. Not legal advice.
**For:** [phase 7 plan](../plans/applied-insurance-reference-phase-7.md), P7-Q9.

## 1. In short

- Where we found a rule, the interim document is a contract of insurance in its own right for its period. New York, California, Florida, Australia, Germany and India say so in statute, regulation or leading case law [S1] [S2] [S4] [S5] [S15] [S16] [S21].
- Several statutes define the interim document by its function. It "temporarily obligates the insurer" to provide cover pending the policy [S5]. Australia defines an "interim contract" as one meant to be replaced or superseded by another contract [S15]. Germany treats provisional cover as a contract with its own rules, separate from the main contract (Hauptvertrag) [S16] [S17].
- Most sources treat the policy as ending the interim document, not as restating it. California says no binder stays valid on or after the date the policy issues [S2]. The New York Court of Appeals held that the binder ended when the insurer agreed to issue the policy, and that the binder was not part of the policy [S1]. German provisional cover ends at the latest when equivalent cover starts under the main contract [S17]. Australian interim cover ends when cover starts under the replacement contract [S15].
- A merger rule appears in only one place we found, a North Carolina decision of 1944 reported in secondary summaries, and we could not open it (unverified). French doctrine records two views, a provisional record of a definitive contract and an autonomous temporary commitment, and leaves the choice to the parties' intention [S18].
- Where the two documents differ, no jurisdiction we read applies the later policy mechanically. California and Florida read the usual policy terms into the binder and let the binder's express terms prevail [S2] [S4]. German law applies the insurer's usual provisional-cover terms first, then the main contract terms, then the terms most favourable to the policyholder [S16]. A Missouri appellate court held that a binder governed over a later policy and that only usual policy terms fill its gaps [S8]. A Texas appellate court applied an endorsement found only in the later policy, because the insured did not show it fell outside the insurer's standard form [S7]. French case law makes a general-conditions exclusion absent from the note unenforceable against the insured [S18].
- Duration is set by statute in some places. California allows 90 days, with a covering note needing a policy within 90 days [S2] [S3]. Texas requires a replacing policy within 30 days for a binder a lender must accept [S6]. India limits motor cover notes to 60 days by rule [S21]. Florida sets 60 days as the point after which cancellation and nonrenewal notices apply [S4]. England, Germany and Australia set no general cap in the provisions we read.
- Terminology trap. In the London market "binder" usually means a binding authority, a delegated authority contract that is not itself a contract of insurance for the policyholder [S12]. US usage and Québec usage (note de couverture, rendered in English as "interim binder") mean the interim cover document [S14].
- We found nothing usable for Ireland, New Zealand, the Netherlands, Singapore, Hong Kong, South Africa or Japan. Italy, Spain and Switzerland yielded statutes that mention provisional cover but not its relation to the policy.

What this means for modelling, offered as evidence only. Option (a), one instrument with the interim document as its first version and the policy a restatement, matches the French first view and a North Carolina line we could not verify, and it fits the commercial sense that both documents describe one risk. Option (b), two instruments with the policy superseding the interim one, matches the statutory text in California, New York case law, Australia and Germany, which give the interim document its own definition, terms and end events. Option (b) needs an extra rule for terms read back from the policy into the interim period, which Texas, Florida, California and Germany all show. Option (a) needs a way to record the interim document's separate end events, such as the Australian and German ones. We have not weighed these, and the choice is for the plan.

## 2. Terms

| Term | Meaning in the sources | Where used |
|---|---|---|
| Binder | A writing that temporarily obligates the insurer to provide cover until the policy issues [S2] [S5]. Often oral or written [S4]. | United States, Canada |
| Cover note | A temporary document confirming cover before the policy is drawn up. Usually in common form and incorporating the insurer's standard terms [S9] [S10]. In India it is a regulated form [S21]. | England and Wales, India, Australia (in the Act's definition, an interim contract exists whether or not a cover note is issued [S15]) |
| Interim contract | The Australian statutory term for a contract intended to give temporary cover and to be replaced or superseded [S15]. | Australia |
| Provisional cover (vorläufige Deckung, note de couverture, documento de cobertura provisional) | German law regulates a contract for provisional cover [S16] [S17]. French law calls the document a note de couverture [S14] [S18]. Spain refers to a "documento de cobertura provisional" [S19]. | Germany, France, Québec, Spain |
| Binding authority | An agreement under which a coverholder, usually a broker or underwriting agency, accepts risks for an insurer and issues documents evidencing cover without further approval [S12]. It is not itself a contract of insurance [S12]. | London market |

The trap. In London a "binder" is informally the binding authority, so a phrase such as "the binder" in a Lloyd's or London document refers to a delegated authority contract between insurer and coverholder, and each risk accepted under it is a separate contract of insurance [S12]. In US and Canadian documents "binder" means the interim cover document for one risk [S2] [S5] [S13]. A model that uses one class for both would conflate a master contract with a single interim cover. The Québec terminology office lists "interim binder" and "binding receipt" as English equivalents of note de couverture [S14].

## 3. Jurisdiction by jurisdiction

### 3.1 United States, general

| Question | Finding |
|---|---|
| Status of the interim document | Treated as a temporary contract of insurance. State statutes define it, for example New York [S5], California [S2] and Florida [S4]. We found no NAIC model law on binders (unverified, the searches returned only the surplus lines model act). |
| Relation to the issued policy | Mixed. See the state subsections. The common pattern is that the binder ends when the policy issues, while usual policy terms are read into the binder period [S2] [S4] [S7]. |
| Conflicts | Express binder terms prevail over usual policy terms in California [S2] and Florida [S4]. Unusual policy terms do not fill binder gaps in Missouri [S8]. |
| Duration and ending | Set state by state. See below. |

### 3.2 New York

| Question | Finding |
|---|---|
| Status of the interim document | Insurance Law section 3404(h) defines a binder as a writing that "temporarily obligates the insurer" to provide the cover pending the policy [S5]. The Court of Appeals describes it as an interim policy [S1]. |
| Relation to the issued policy | Separate. In Springer v Allstate (2000) the court held the binder did not form part of the policy because it was not attached, and the policy and application alone formed the contract. The contestability periods ran from the policy date [S1]. |
| Conflicts | The binder governed its own period and the policy its own. The court enforced the binder's end date [S1]. |
| Duration and ending | No time limit in section 3404(h) as summarised. Cancellation follows the standard fire policy provisions [S5]. Under Springer a binder ends when the policy is issued or refused [S1]. |

### 3.3 California

| Question | Finding |
|---|---|
| Status of the interim document | Insurance Code section 382.5 defines a binder and treats it as a policy for proving the cover it states. It excludes life, disability and insurance of $1,000,000 or more [S2]. Section 382 separately covers "covering notes" [S3]. |
| Relation to the issued policy | Statute says no binder remains valid on or after the date the policy issues [S2]. Section 382 requires a policy to issue in place of a covering note within 90 days with the same cover [S3]. |
| Conflicts | A binder includes the usual policy terms for the cover and designated endorsements. Its clear and express terms take precedence [S2]. |
| Duration and ending | Valid for the stated period up to 90 days from execution, and 90 days if none is stated. Expiry is not a cancellation or nonrenewal [S2]. A covering note can be extended past 90 days with the commissioner's approval [S3]. |

### 3.4 Texas

| Question | Finding |
|---|---|
| Status of the interim document | We found no general statutory definition (unverified). Insurance Code section 549.055 requires a lender to accept a binder issued by an authorised agent as evidence of required cover [S6]. |
| Relation to the issued policy | The statute expects an original policy to replace the binder [S6]. A 2011 Houston appellate decision, as reported by a law firm blog, determined binder cover by reference to the insurer's standard policy form [S7]. |
| Conflicts | In QB Investments the policy endorsement, absent from the binder, applied because the binder said other endorsements may apply and the insured did not show it was outside the standard form [S7]. |
| Duration and ending | A replacing policy is due on or before the 30th day after the binder issues, for the lender case [S6]. We found no general limit (unverified). |

### 3.5 Florida

| Question | Finding |
|---|---|
| Status of the interim document | Statute section 627.420 provides that temporary property, marine, casualty or surety cover may be made orally or in writing [S4]. |
| Relation to the issued policy | The binder is deemed to include the usual policy terms and named endorsements unless it states otherwise. An insurer cancelling a motor binder gives 5 days' notice unless a policy or another binder replaces it [S4]. We read this as treating replacement as ending the binder, which is our inference. |
| Conflicts | The binder's explicit terms override the usual terms [S4]. |
| Duration and ending | Cancellation and nonrenewal notices are not required unless the binder lasts more than 60 days [S4]. |

### 3.6 Illinois

| Question | Finding |
|---|---|
| Status of the interim document | Not confirmed. A search result pointed to an Illinois administrative rule on binders (50 Ill. Adm. Code 2301.70) that would read the standard policy terms into a binder (unverified, the page could not be opened). |
| Relation to the issued policy | Not confirmed (unverified). |
| Conflicts | Not confirmed (unverified). |
| Duration and ending | Not confirmed (unverified). |

### 3.7 Other US states in the sources

A Missouri appellate court held in 2006 that a faxed binder, not the later policy, governed coverage, because policy terms fill a binder only if usual, and a surplus lines insurer's customised exclusion was not shown to be usual [S8]. A North Carolina decision of 1944, State Distributing Corp v Travelers Indemnity, is summarised in a search result as holding that a binder merged into a later formal policy (unverified, we could not open the report).

### 3.8 England and Wales (Scotland not separately found)

| Question | Finding |
|---|---|
| Status of the interim document | Halsbury's Laws describes interim insurance as usually granted by a cover note in common form [S9]. A reinsurance text says cover is fully effective from the date the temporary cover note issues [S10]. We found no statute defining a cover note. The Road Traffic Act 1988 section 147 speaks of a certificate of insurance and does not mention cover notes [S11]. |
| Relation to the issued policy | Not confirmed. A cover note normally incorporates the insurer's standard policy terms by reference [S9]. We saw a statement that English authority is thin and that a Hong Kong first-instance case treated the cover note as distinct from the later policy (unverified, not opened). |
| Conflicts | Not confirmed. The proposer is bound by the incorporated standard terms only if otherwise shown to have accepted them [S9]. |
| Duration and ending | No statutory limit found for general cover notes. Motor cover notes are commonly short, around 30 days in insurer guidance (unverified, the insurer page could not be opened). Motor requirements under the 1988 Act and the Third Party Risks Regulations 1972 were not confirmed. Scotland, and the Insurance Act 2015, were not found to address interim cover (unverified). |

### 3.9 Ireland

We found nothing on cover notes or interim cover in Irish statute or case law. The Consumer Insurance Contracts Act 2019 contents list shows no heading on temporary cover (unverified, the sections were not read).

### 3.10 Canada, common-law provinces

| Question | Finding |
|---|---|
| Status of the interim document | The Ontario Insurance Act definition of "contract" includes interim receipts and writings evidencing a contract, which courts have read to cover cover notes and interim binders [S13]. |
| Relation to the issued policy | Not confirmed in statute. Case reports concern terms of the binder against terms of the policy booklet [S13]. |
| Conflicts | Section 124 requires all terms to be set out in the policy or attached writing, otherwise limiting terms are invalid against the insured. Results vary. An Alberta decision (New Forty Four Mine, 1987) enforced a security-guard condition named in the binder. A BC trial decision (2007) refused to enforce an alarm warranty in a binder the insured had no chance to read [S13]. |
| Duration and ending | No statutory limit found (unverified). |

### 3.11 Canada, Québec

| Question | Finding |
|---|---|
| Status of the interim document | The terminology office defines the note de couverture as a document confirming temporary cover before the policy is drawn up, covering both a provisional record of a definitive contract and a time-limited provisional agreement [S14]. We did not open the Civil Code of Québec (unverified). |
| Relation to the issued policy | Not confirmed in the Code. The office's two situations suggest the same two views as in France [S14]. |
| Conflicts | Not confirmed (unverified). |
| Duration and ending | Not confirmed (unverified). |

### 3.12 Australia

| Question | Finding |
|---|---|
| Status of the interim document | Insurance Contracts Act 1984 section 11(2) defines an interim contract as one intended to give temporary cover and to be replaced or superseded by another contract, whether or not a cover note issues [S15]. |
| Relation to the issued policy | Replacement is treated as ending the interim contract. Under section 38(2), where the insured has submitted a replacement proposal before the interim cover expires, the insurer stays liable until cover starts under the replacement contract, the interim contract is cancelled, or the proposal is withdrawn [S15]. |
| Conflicts | Section 38(1) voids a provision making liability depend on the insurer receiving or accepting the replacement proposal. Section 38(3) disapplies several general provisions to interim contracts [S15]. |
| Duration and ending | No fixed period in the part we read. The first paragraphs of section 38(2) were not captured and should be read in the Act (unverified). |

### 3.13 New Zealand

We found nothing on how the Contracts of Insurance Act 2024 or earlier law treats cover notes or binders (unverified). Search results pointed only to a 1907 newspaper note on stamp duty.

### 3.14 Germany

| Question | Finding |
|---|---|
| Status of the interim document | Versicherungsvertragsgesetz sections 49 to 52 regulate the contract for provisional cover (Vertrag über vorläufige Deckung) as a contract in its own right [S16] [S17]. |
| Relation to the issued policy | Separate from the main contract. Provisional cover ends at the latest when equivalent cover starts under a main contract or another provisional cover contract the policyholder concluded, including one with another insurer [S17]. |
| Conflicts | If the general terms were not handed over, the insurer's usual provisional-cover terms apply. If none exist, the main contract terms apply. If doubt remains, the terms most favourable to the policyholder that the insurer used at the time apply [S16]. |
| Duration and ending | No statutory cap in the sections read. Ends on equivalent cover starting, on late premium if the insurer gave the required warning, or on withdrawal or objection by the policyholder. Either party may end an open-ended contract, with the insurer's termination effective two weeks after receipt. Rules cannot be varied to the policyholder's disadvantage [S17]. |

### 3.15 France

| Question | Finding |
|---|---|
| Status of the interim document | A commentary reports that Code des assurances article L112-2 lets the note record the parties' engagement and that no formality is needed. The Cour de cassation (1993) held insurer and insured are bound by delivery of the note [S18]. |
| Relation to the issued policy | The note precedes the policy and is meant to give way to it while keeping its own effect for the period it governs. Doctrine divides between a provisional instrument of a definitive contract and an autonomous temporary commitment, decided by the parties' intention [S18]. |
| Conflicts | Later general conditions cannot be set against the insured for the period covered by the note alone. An exclusion present in the general conditions and absent from the note was held unenforceable (Cass. 1re civ., 13 May 1998) [S18]. |
| Duration and ending | Set by the note. Where it states no term, the insurer must prove that cover has ended (Cass. 1re civ., 25 October 1994) [S18]. |

### 3.16 Spain, Italy, Switzerland, Netherlands

| Jurisdiction | Finding |
|---|---|
| Spain | Article 5 of Law 50/1980 requires the insurer to deliver the policy or at least a provisional cover document [S19]. We found no source on its relation to the policy, conflicts or duration. |
| Italy | Article 1888 of the Civil Code requires the contract to be proved in writing and the insurer to deliver the policy or another signed document [S20]. We found nothing on provisional cover or nota di copertura. |
| Switzerland | Article 9 of the Insurance Contract Act regulates provisional cover. A search summary says it is cancellable on 14 days' notice, ends when a definitive contract is concluded with the same or another insurer, and must be confirmed in writing (unverified, the official text could not be opened). |
| Netherlands | Nothing found on the legal treatment of voorlopige dekking. |

### 3.17 India

| Question | Finding |
|---|---|
| Status of the interim document | A law-firm article states that the Motor Vehicles Act section 145(b) includes a cover note in "certificate of insurance" and calls the cover note an autonomous, limited-duration contract importing the policy's standard terms [S21]. We did not open the Act. |
| Relation to the issued policy | Not settled in what we read. The insurer must issue the certificate of insurance before the cover note expires [S22]. |
| Conflicts | Not confirmed. |
| Duration and ending | Rule 142 of the Central Motor Vehicles Rules 1989 prescribes the form and limits validity to sixty days [S21]. An insurer page states 60 days from issue [S22]. |

### 3.18 Singapore, Hong Kong, South Africa, Japan

We found nothing usable on interim cover in these jurisdictions.

## 4. Patterns across jurisdictions

| Pattern | Jurisdictions | Sources |
|---|---|---|
| Separate contract, ended by the policy, with usual policy terms read back into the interim period | New York, California, Florida, Texas (appellate), Missouri (appellate), Australia, Germany | [S1] [S2] [S4] [S7] [S8] [S15] [S17] |
| Merges into the policy | North Carolina 1944 (unverified, not opened) | Search summary only |
| Open between the two views, decided by the parties' intention | France, Québec (by the terminology office's two situations) | [S14] [S18] |
| Separate and time-limited by rule | India (60 days), California (90 days), Texas lender binders (30 days) | [S2] [S6] [S21] |
| Unclear or not found | England and Wales and Scotland (thin authority), Ireland, New Zealand, Netherlands, Italy, Spain, Switzerland, Singapore, Hong Kong, South Africa, Japan, Illinois, Canadian common-law provinces on merger | [S9] [S10] [S19] [S20] |

## 5. Open points

- Illinois rule 2301.70 and any Illinois case law could not be opened.
- The North Carolina merger decision, the Swiss Article 9 text and the Employers Commercial Union decision (New York) were seen only in search summaries.
- Section 38(2)(a) and (b) of the Australian Act, and the full text of section 11, were not captured.
- No English case on the cover note and the later policy was read. The Hong Kong decision in China Ping v Tsang Fung Yin was cited in a search summary only. Halsbury's section 67 is behind a paywall beyond its opening lines.
- Motor cover notes under the Road Traffic Act 1988 and the Third Party Risks Regulations 1972 were not confirmed. A Northern Ireland version of the 1972 regulations was reported to define "policy" as including a covering note, but the scanned PDF could not be read.
- The Civil Code of Québec articles 2398 to 2400, the Ontario Insurance Act text, the Irish 2019 Act sections, and the Indian Motor Vehicles Act text were not opened.
- No NAIC model law on binders was found. Texas and Illinois general binder definitions were not found.
- Whether any jurisdiction treats the interim document as an offer or condition precedent rather than a contract was not examined.
- Case-law statements in secondary sources (law-firm blogs, summaries, doctrine) should be checked against the reports before they support a decision.

## 6. Sources

- **S1.** Springer v Allstate Life Insurance Co of New York, New York Court of Appeals, 9 May 2000. https://www.law.cornell.edu/nyctap/I00_0051.htm. Primary (decision text hosted by Cornell).
- **S2.** California Insurance Code section 382.5 (binders). https://california.public.law/codes/ca_ins_code_section_382.5. Primary (statute on a public-law mirror).
- **S3.** California Insurance Code section 382 (covering notes). https://california.public.law/codes/insurance_code_section_382. Primary (statute on a public-law mirror).
- **S4.** Florida Statutes section 627.420 (binders), Florida Senate. https://m.flsenate.gov/Statutes/627.420. Primary.
- **S5.** New York Insurance Law section 3404, New York State Senate. https://www.nysenate.gov/legislation/laws/ISC/3404. Primary.
- **S6.** Texas Insurance Code section 549.055 (insurance binder as evidence of insurance), FindLaw. https://codes.findlaw.com/tx/insurance-code/ins-sect-549-055/. Primary (statute on a commercial host).
- **S7.** "The legal effect of insurance binders in Texas", on QB Investments v Certain Underwriters at Lloyd's, Tex App Houston 1st Dist, 4 August 2011. https://www.propertyinsurancecoveragelaw.com/blog/the-legal-effect-of-insurance-binders-in-texas/. Secondary.
- **S8.** Alea London Ltd v Bono-Soltysiak Enterprises, 186 S.W.3d 403, Missouri Court of Appeals, 2006, case summary. https://studicata.com/case-briefs/case/alea-london-ltd-v-bono-soltysiak-enterprises. Secondary.
- **S9.** Halsbury's Laws of England, Insurance, paragraph 67 "Cover notes", LexisNexis (opening lines only). https://www.lexisnexis.co.uk/legal/commentary/halsburys-laws-of-england/insurance/67-cover-notes. Secondary.
- **S10.** "Brokers' Cover Notes", chapter 13 of Reinsurance Practice and the Law, i-law (opening lines only, undated). https://www.i-law.com/ilaw/doc/view.htm?id=131251. Secondary.
- **S11.** Road Traffic Act 1988 section 147, legislation.gov.uk. https://www.legislation.gov.uk/ukpga/1988/52/section/147. Primary.
- **S12.** "Brokers and binding authorities", CMS, 26 October 2004. https://cms.law/en/gbr/legal-updates/brokers-and-binding-authorities. Secondary.
- **S13.** "Deliver policies quickly to avoid unwanted risk", Canadian Underwriter, 30 September 2009. https://canadianunderwriter.ca/2009/09/30/deliver-policies-quickly-to-avoid-unwanted-risk/. Secondary.
- **S14.** "note de couverture", Grand dictionnaire terminologique, Office québécois de la langue française. https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/2084771/note-de-couverture. Secondary.
- **S15.** Insurance Contracts Act 1984 (Cth), sections 11 and 38, legislation.gov.au (2016 compilation). https://www.legislation.gov.au/C2004A02944/2016-07-01/2016-07-01/text/original/epub/OEBPS/document_1/document_1.html. Primary.
- **S16.** Versicherungsvertragsgesetz section 49, Bundesministerium der Justiz. https://www.gesetze-im-internet.de/vvg_2008/__49.html. Primary.
- **S17.** Versicherungsvertragsgesetz section 52, Bundesministerium der Justiz. https://www.gesetze-im-internet.de/vvg_2008/__52.html. Primary.
- **S18.** "Formation du contrat d'assurance, la note de couverture", Gdroit, updated 5 October 2026. https://gdroit.fr/2025/09/15/formation-du-contrat-dassurance-la-note-de-couverture/. Secondary.
- **S19.** Ley 50/1980 de Contrato de Seguro, article 5, Boletín Oficial del Estado (consolidated text). https://www.boe.es/buscar/act.php?id=BOE-A-1980-22501. Primary.
- **S20.** Codice civile article 1888, Brocardi. https://www.brocardi.it/codice-civile/libro-quarto/titolo-iii/capo-xx/sezione-i/art1888.html. Primary (statute on a commentary site).
- **S21.** "Interim and Final Insurance Contracts in India", CaseMine column. https://www.casemine.com/in/column/interim-and-final-insurance-contracts-in-india:-a-critical-analysis-of-policies-and-cover-notes/view. Secondary.
- **S22.** "What is a Cover Note?", IFFCO-Tokio General Insurance. https://www.iffcotokio.co.in/motor-insurance/what-is-a-cover-note. Secondary (insurer page).
