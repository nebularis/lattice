"""Emits the policy mapping's Turtle: wording, words, conditions, stated meaning, instance.
Anonymised: insurer, insured, addresses, policy numbers, producer, product and URLs."""
import sys

OUT = sys.argv[1]
L = []
w = L.append

def rank(i):
    return f"{chr(97 + i // 10)}{i % 10}"

def lit(s):
    return '"""' + s.replace('\\', '\\\\') + '"""'

# ---------------------------------------------------------------- wording tree
# node: (id, objectId, elementType, kind, payload, flags)
#   kind "el": payload = list of child nodes
#   kind "tx": payload = list of parts (str, or ("var", var_id))
VARS = {}   # var_id -> (key, space or None, multi)

def var(vid, key, space=None, multi=False):
    VARS[vid] = (key, space, multi)
    return ("var", vid)

def el(i, oid, et, children):
    return (i, oid, et, "el", children, set())

def tx(i, oid, et, parts, *flags):
    return (i, oid, et, "tx", parts if isinstance(parts, list) else [parts], set(flags))

NOMEANING = "nomeaning"

decl = el("declarations", "Declarations", "Schedule", [
    tx("item-1", "Item 1", "Clause", ["Named Entity: ", var("var-named-entity", "named-entity"),
        ". Named Entity Address: ", var("var-ne-address", "named-entity-address"),
        ". State of Formation: ", var("var-ne-state", "state-of-formation"), "."]),
    tx("item-2", "Item 2", "Clause", ["Policy Period: Inception Date: ", var("var-inception", "inception-date", "time"),
        ". Expiration Date: ", var("var-expiration", "expiration-date", "time"),
        ". 12:01 A.M. at the Named Entity Address."]),
    tx("item-3", "Item 3", "Clause", ["Premium: ", var("var-premium", "premium", "usd-space")]),
    tx("item-4", "Item 4", "Clause", ["Insurer: (a) Insurer Address: ", var("var-insurer-address", "insurer-address"),
        " (b) Claims Address: ", var("var-claims-address", "claims-address"),
        " (c) By E-Mail: ", var("var-claims-email", "claims-email"),
        " Reference the Policy Number and any applicable Coverage Section."]),
    tx("item-5", "Item 5", "Clause", ["Policy Aggregate: ", var("var-aggregate", "policy-aggregate", "usd-space")]),
    el("item-6", "Item 6", "Clause", [
        el("item-6-do", "Item 6, Non-Profit D&O", "Clause", [
            tx("do-limit", "6 D&O limit", "Clause", ["Limit of Liability: Separate Limit of Liability: Not Applicable. Shared Limit of Liability: ",
                var("var-do-shared-limit", "do-shared-limit", "usd-space"), ". Shared Limit of Liability, if any, is shared with: EPLI."]),
            tx("do-excess", "6 D&O excess", "Clause", ["Excess Limit for Executives: ", var("var-do-excess", "do-excess-limit-executives", "usd-space")]),
            tx("do-retention", "6 D&O retention", "Clause", ["Retention: ", var("var-do-retention", "do-retention", "usd-space")]),
            tx("do-continuity", "6 D&O continuity", "Clause", ["Continuity Date: Outside Entity Executive Coverage: Date on which the Executive first served as an Outside Entity Executive for such Outside Entity. All other Non-Profit D&O Coverage: ",
                var("var-do-continuity", "do-continuity-date", "time")]),
            tx("do-premium", "6 D&O premium", "Clause", ["Coverage Section Premium: ", var("var-do-premium", "do-premium", "usd-space")]),
        ]),
        el("item-6-epl", "Item 6, EPL", "Clause", [
            tx("epl-limit", "6 EPL limit", "Clause", ["Limit of Liability: Separate Limit of Liability: Not Applicable. Shared Limit of Liability: ",
                var("var-epl-shared-limit", "epl-shared-limit", "usd-space"), ". Shared Limit of Liability, if any, is shared with: Non-Profit D&O."]),
            tx("epl-retention", "6 EPL retention", "Clause", ["Retention: (i) Class Action Retention: ", var("var-epl-retention-class", "epl-retention-class-action", "usd-space"),
                " (ii) Third Party Retention: ", var("var-epl-retention-third", "epl-retention-third-party", "usd-space"),
                " (iii) All other Loss to which a Retention applies: ", var("var-epl-retention-other", "epl-retention-other", "usd-space")]),
            tx("epl-continuity", "6 EPL continuity", "Clause", ["Continuity Date: Outside Entity Executive Coverage: Date on which the Executive first served as an Outside Entity Executive for such Outside Entity. All other EPL Coverage: ",
                var("var-epl-continuity", "epl-continuity-date", "time")]),
            tx("epl-premium", "6 EPL premium", "Clause", ["Coverage Section Premium: ", var("var-epl-premium", "epl-premium", "usd-space")]),
        ]),
        el("item-6-fid", "Item 6, Fiduciary", "Clause", [
            tx("fid-limit", "6 Fiduciary limit", "Clause", ["Limit of Liability: Separate Limit of Liability: ",
                var("var-fid-separate-limit", "fid-separate-limit", "usd-space"), ". Shared Limit of Liability: Not Applicable."]),
            tx("fid-retention", "6 Fiduciary retention", "Clause", ["Retention: (i) Securities Retention: ", var("var-fid-retention-securities", "fid-retention-securities", "usd-space"),
                " (ii) All other Loss to which a Retention applies: ", var("var-fid-retention-other", "fid-retention-other", "usd-space")]),
            tx("fid-continuity", "6 Fiduciary continuity", "Clause", ["Continuity Date: ", var("var-fid-continuity", "fid-continuity-date", "time")]),
            tx("fid-premium", "6 Fiduciary premium", "Clause", ["Coverage Section Premium: ", var("var-fid-premium", "fid-premium", "usd-space")]),
        ]),
        el("item-6-cpl", "Item 6, CPL", "Clause", [
            tx("cpl-limit", "6 CPL limit", "Clause", ["Limit of Liability: Separate Limit of Liability: ",
                var("var-cpl-separate-limit", "cpl-separate-limit", "usd-space"), ". Shared Limit of Liability: Not Applicable."]),
            tx("cpl-retention", "6 CPL retention", "Clause", ["Retention: ", var("var-cpl-retention", "cpl-retention", "usd-space")]),
            tx("cpl-continuity", "6 CPL continuity", "Clause", ["Continuity Date: ", var("var-cpl-continuity", "cpl-continuity-date", "time")]),
            tx("cpl-retro", "6 CPL retroactive", "Clause", ["Retroactive Date: ", var("var-cpl-retro", "cpl-retroactive-date", "time")]),
            tx("cpl-premium", "6 CPL premium", "Clause", ["Coverage Section Premium: ", var("var-cpl-premium", "cpl-premium", "usd-space")]),
        ]),
    ]),
    tx("item-7", "Item 7", "Clause", "Passport: This policy does not serve as a master Passport policy. Each of the following Coverage Sections shall serve as a master Passport policy solely with respect to the coverage provided thereunder: Not Applicable."),
    tx("item-8", "Item 8", "Clause", ["TRIA Premium, Taxes and Surcharges: (a) TRIA Premium: ", var("var-tria-premium", "tria-premium", "usd-space"),
        ". 'TRIA Premium' means the premium for Certified Acts of Terrorism Coverage under Terrorism Risk Insurance Act, as amended. Amount indicated above is included in Premium. A copy of the TRIA disclosure sent with the original quote is attached hereto."]),
    tx("attestation", "Attestation", "Clause", "IN WITNESS WHEREOF, the Insurer has caused this Policy to be signed by its President, Secretary and Authorized Representative. This Policy shall not be valid unless signed below at the time of issuance by an authorized representative of the insurer."),
])

gtc = el("gtc", "General Terms and Conditions", "Section", [
    tx("gtc-recital", "GTC recital", "Clause", "In consideration of the payment of the premium, and each of their respective rights and obligations in this policy, the Insureds and the Insurer agree as follows:"),
    tx("gtc-1", "GTC 1", "Clause", "These General Terms and Conditions shall apply to all Coverage Sections, unless any Coverage Section states specifically that all or part of these General Terms and Conditions shall not apply to such Coverage Section. The definitions, terms, conditions and limitations set forth in each Coverage Section shall apply only to that particular Coverage Section."),
    tx("gtc-2", "GTC 2", "Clause", "The Insurer shall be liable only for the amount of Loss arising from each Claim or group of Related Claims that exceeds the Retention amount stated in Item 6 of the Declarations as applicable to the Coverage Section affording coverage to such Claim or group of Related Claims. Amounts within such Retention shall remain uninsured. A single Retention amount shall apply to each Claim or group of Related Claims. If a Claim or a group of Related Claims triggers more than one Coverage Section all of which are subject to a Shared Limit of Liability, the highest applicable Retention amount shall apply to such Claim or group of Related Claims. If a Claim or a group of Related Claims triggers more than one Coverage Section at least one of which is subject to a Separate Limit of Liability, the Retention applicable to Loss in connection with such Claim or group of Related Claims under any such Coverage Section subject to a Separate Limit of Liability shall apply separately to such Loss, and the applicable Retention for such Coverage Section shall not be satisfied by payments of Loss made towards the Retention required under any other Coverage Section."),
    tx("gtc-3", "GTC 3", "Clause", "The Policy Aggregate is the Insurer's maximum liability for all Loss under all Coverage Sections combined. Under no circumstances shall the Insurer be responsible to pay any Loss in excess of the Policy Aggregate. The term \"Limits of Liability\" refers to the several types of limits provided under this policy, including the Policy Aggregate, any Separate Limits of Liability, any Shared Limits of Liability, and any sublimits of liability set forth in any applicable Coverage Sections. If Separate Limits of Liability are stated in Item 6 of the Declarations, then each such Separate Limit of Liability shall be the maximum limit of the Insurer's liability for all Loss arising out of all Claims first made against the Insureds during the Policy Period or the Discovery Period (if applicable) with respect to the applicable Coverage Section as stated on the Declarations. Each Separate Limit of Liability shall be part of, and not in addition to, the Policy Aggregate for all Loss under this policy and shall in no way serve to increase the Policy Aggregate as therein stated. If Shared Limits of Liability are stated in Item 6 of the Declarations, then each such Shared Limit of Liability shall be the maximum limit of the Insurer's liability for all Loss arising out of all Claims first made against the Insureds during the Policy Period or the Discovery Period (if applicable) with respect to all Coverage Sections for which such Shared Limit of Liability is applicable, as indicated on the Declarations. In the event that the amount stated as a Shared Limit of Liability in Item 6 of the Declarations for a Coverage Section is less than the amount(s) stated for the other Coverage Section(s) with which it shares such Shared Limit of Liability, such lesser amount stated in Item 6 shall serve as the limit of liability for all Loss in the aggregate under such Coverage Section, subject to reduction through any prior payments of Loss under such Shared Limit of Liability. Each Shared Limit of Liability shall be part of, and not in addition to, the Policy Aggregate for all Loss under this policy and shall in no way serve to increase the Policy Aggregate as therein stated. Each sublimit of liability set forth in any Coverage Section is the maximum limit of the Insurer's liability for all Loss in the aggregate under this policy that is subject to that sublimit of liability. All sublimits of liability shall be part of, and not in addition to, the Policy Aggregate and any applicable Separate Limit of Liability or Shared Limit of Liability. All Related Claims that pursuant to the applicable Notice and Reporting Clause are considered made or received during the Policy Period or Discovery Period (if applicable), shall also be subject to the applicable Limits of Liability set forth in this policy. Each of the Limits of Liability for the Discovery Period (if applicable) shall be part of, and not in addition to, each of the corresponding Limits of Liability for the Policy Period. Defense Costs are not payable by the Insurer in addition to the Limits of Liability. Defense Costs are part of Loss and as such are subject to the Limits of Liability for Loss."),
    tx("gtc-4", "GTC 4", "Clause", "Except as indicated below, if the Named Entity shall cancel or the Named Entity or the Insurer shall refuse to renew this policy, the Named Entity shall have the right to a period of up to six (6) years following the effective date of such cancellation or nonrenewal (\"Discovery Period\"), upon payment of an Additional Premium Amount described in each Coverage Section, in which to give written notice to the Insurer of: (i) Claims first made against an Insured; (ii) if provided by a purchased Coverage Section, Pre-Claim Inquiries first received by an Insured Person; and (iii) circumstances of which an Organization or an Insured shall become aware, in any such case, during the Discovery Period and solely with respect to any covered acts, errors, omissions, failures or violations (including but not limited to Wrongful Acts, Privacy Events and Security Failures) occurring prior to the end of the Policy Period and otherwise covered by this policy. In the event of a Transaction, the Named Entity shall have the right to request an offer from the Insurer of a Discovery Period with respect to covered acts, errors, omissions, failures or violations (including but not limited to Wrongful Acts, Privacy Events and Security Failures) occurring prior to the effective time of the Transaction and otherwise covered by this policy. The Insurer shall offer such Discovery Period pursuant to such terms, conditions, exclusions and additional premium as the Insurer may reasonably decide. In the event of a Transaction, the right to a Discovery Period shall not otherwise exist except as indicated in this paragraph. If the Named Entity exercises its right to purchase a Discovery Period, that period incepts at the end of the Policy Period or, if purchased in the event of a Transaction, as of the effective time of such Transaction. The right to purchase a Discovery Period shall terminate unless written notice of election, together with any additional premium due, is received by the Insurer no later than thirty (30) days after the effective date of the cancellation, nonrenewal or Transaction. Any Discovery Period is not cancelable and the additional premium charged is non-refundable in whole or in part. This Discovery Clause shall not apply to any cancellation resulting from non-payment of premium."),
    tx("gtc-5", "GTC 5", "Clause", "In the event of a Transaction, this policy shall continue in full force and effect only as to those covered acts, errors, omissions, failures or violations (including but not limited to Wrongful Acts, Privacy Events and Security Failures) occurring prior to the effective time of the Transaction and otherwise covered by this policy, and no portion of the premium paid for this policy shall be refundable. The Named Entity shall also have the right to an offer by the Insurer of a Discovery Period described in Clause 4 above. This policy may not be canceled after the effective time of the Transaction. Notwithstanding the foregoing, this policy may continue in full force and effect as to those covered acts, errors, omissions, failures or violations (including but not limited to Wrongful Acts, Privacy Events and Security Failures) occurring subsequent to the effective time of the Transaction and otherwise covered by this policy, if: (a) within thirty (30) days subsequent to the effective time of such Transaction the Insurer has been provided with full particulars of the Transaction, the related entity(ies) and any other information requested by the Insurer; and (b) the Insurer waives the restrictions set forth above with respect to such Transaction by written endorsement to this policy and the Named Entity or its successor has paid any additional premium and accepted any amendments to this policy required by the Insurer."),
    el("gtc-6", "GTC 6", "Clause", [
        tx("gtc-6a", "GTC 6(a)", "Clause", "Worldwide Territory. The coverage afforded by this policy shall apply anywhere in the world.", NOMEANING),
        tx("gtc-6b", "GTC 6(b)", "Clause", "Passport. If a Coverage Section is listed in Item 7 of the Declarations, then such Coverage Section and the applicable provisions of these General Terms and Conditions shall act as a master policy solely with respect to the coverage provided by such Coverage Section. The coverage afforded by such Coverage Section shall be provided in conjunction with the Passport foreign underlyer policy issued in each jurisdiction selected by the Named Entity. The specific structure of the coverage provided by such Coverage Section in conjunction with each Passport foreign underlyer policy is set forth in the Passport Structure Appendix for such Coverage Section that is attached to this policy."),
        tx("gtc-6c", "GTC 6(c)", "Clause", "Spousal, Domestic Partner and Legal Representative Extension. If a Claim against an Insured Person includes a Claim against: (1) the lawful spouse or legally recognized domestic partner of such Insured Person; or (2) a property interest of such spouse or domestic partner; and in either such case, such Claim arises from any actual or alleged Wrongful Acts of such Insured Person, this policy shall pay covered Loss arising from the Claim made against such spouse or domestic partner or the property of such spouse or domestic partner to the extent that such Loss does not arise from a Claim for any actual or alleged act, error or omission of such spouse or domestic partner. This policy shall pay covered Loss arising from a Claim made against the estates, heirs, or legal representatives of any deceased Insured Person, and the legal representatives of any Insured Person in the event of incompetence, insolvency or bankruptcy, who was an Insured Person at the time the Wrongful Acts upon which such Claim is based were alleged to have been committed."),
    ]),
    el("gtc-7", "GTC 7", "Clause", [
        tx("gtc-7a", "GTC 7(a)", "Clause", "By Named Entity: This policy may be canceled by the Named Entity at any time only by mailing written prior notice to the Insurer or by surrender of this policy to the Insurer's authorized agent or to the Insurer."),
        tx("gtc-7b", "GTC 7(b)", "Clause", "By the Insurer: This policy may be canceled by the Insurer only in the event of non-payment of premium by delivering to the Named Entity by registered, certified or other first class mail, at the Named Entity Address, written notice stating when, not less than fifteen (15) days, the cancellation shall be effective. Proof of mailing or delivery of such notice as aforesaid shall be sufficient proof of notice and this policy shall be deemed canceled as to all Insureds at the date and hour specified in such notice."),
        tx("gtc-7c", "GTC 7(c)", "Clause", "Return of Premium: If this policy shall be canceled, the Insurer shall retain the pro rata proportion of the premium hereon."),
    ]),
    tx("gtc-8", "GTC 8", "Clause", "In the event the Insurer recovers amounts it paid under this policy, the Insurer shall reinstate the Limits of Liability of this policy to the extent of such recovery, less its costs incurred in administering and obtaining such recovery. The Insurer assumes no duty to seek a recovery of any amounts paid under this policy."),
    tx("gtc-9", "GTC 9", "Clause", "Except for the giving of a notice of Claim, which shall be governed by the Notice and Reporting Clause of the applicable Coverage Section, all notices required under this policy to be given by an Insured to the Insurer shall be given in writing to the Insurer at the Insurer Address. It is agreed that the Named Entity shall act on behalf of all Insureds with respect to the giving of notice of a Claim, Pre-Claim Inquiry, Crisis or circumstances, the giving and receiving of notice of conditional renewal, premium increase, nonrenewal and cancellation, the payment of premiums and the receiving of any return premiums that may become due under this policy, the receipt and acceptance of any endorsements issued to form a part of this policy, the exercising or declining of the right to tender the defense of a Claim, Crisis or circumstance to the Insurer, and the exercising or declining to exercise any right to a Discovery Period."),
    tx("gtc-10", "GTC 10", "Clause", "This policy and any and all rights hereunder are not assignable without the prior written consent of the Insurer."),
    tx("gtc-11", "GTC 11", "Clause", "Except as provided in any Alternative Dispute Resolution Clause of a Coverage Section, no action shall lie against the Insurer unless, as a condition precedent thereto, there shall have been full compliance with all of the terms of this policy, nor until the amount of an Insured's obligation to pay shall have been finally determined either by judgment against such Insured after actual trial or by written agreement of such Insured, the claimant and the Insurer. Any Insured or the legal representative thereof who has secured such judgment or written agreement shall be entitled thereafter to recover under this policy to the extent of the insurance afforded by this policy. No person or organization shall have any right under this policy to join the Insurer as a party to any action against an Insured or the Named Entity to determine an Insured's liability, nor shall the Insurer be impleaded by any Insured or by any spouse, domestic partner or legal representative thereof."),
    tx("gtc-12", "GTC 12", "Clause", "Bankruptcy or insolvency of any Insured or of their estates shall not relieve the Insurer of any of its obligations under this policy. In such event, the Insurer and each Insured agree to cooperate in any efforts by the Insurer or any Insured to obtain relief for the benefit of the Insured Persons from any stay or injunction applicable to the distribution of the policy proceeds."),
    tx("gtc-13", "GTC 13", "Clause", "In the event that there is an inconsistency between: (i) any period of limitation in this policy relating to the giving of notice of cancellation or discovery/extended reporting election, and (ii) the minimum or maximum period required by applicable law, where such law allows, the Insurer will resolve the inconsistency by applying the notice period that is more favorable to the Insureds. Otherwise, the notice period is hereby amended to the extent necessary to conform to applicable law. Coverage under this policy shall not be provided to the extent prohibited by any law."),
    tx("gtc-14", "GTC 14", "Clause", "All premiums, limits, retentions, Loss and other amounts under this policy are expressed and payable in the currency of the United States of America. If judgment is rendered, settlement is denominated or other elements of Loss are stated or incurred in a currency other than United States of America dollars, payment of covered Loss due under this policy (subject to the terms, conditions and limitations of this policy) will be made either in such other currency (at the option of the Insurer and if agreeable to the Named Entity) or, in United States of America dollars, at the rate of exchange published in The Wall Street Journal on the date the Insurer's obligation to pay such Loss is established (or if not published on such date the next publication date of The Wall Street Journal)."),
    tx("gtc-15", "GTC 15", "Clause", "The descriptions in the headings of this policy are solely for convenience, and form no part of the terms and conditions of coverage.", NOMEANING),
    el("gtc-16", "GTC 16", "Clause", [
        tx("gtc-16a", "GTC 16(a)", "Clause", "Terms appearing in bold in a Coverage Section shall have the meaning and/or value ascribed to them in the Definitions Clause of that Coverage Section. If a term appearing in bold in a Coverage Section is not defined in the Definitions Clause of that Coverage Section, then the meaning and/or value ascribed to such term in the Declarations or below in Clause 16(c) Definitions of General Applicability shall apply for purposes of coverage provided under that particular Coverage Section. Certain terms, including without limitation the following, appear in bold and are defined in more than one Coverage Section: (1) Claim; (2) Crisis; (3) Defense Costs; (4) Insured; (5) Insured Person; (6) Loss; (7) Pre-Claim Inquiry; (8) Privacy Event; (9) Related Claim; (10) Security Failure; (11) Wrongful Act. Each of these terms shall have the meaning ascribed to the term in a Coverage Section in which the term appears, but that meaning shall apply solely for purposes of coverage provided under that particular Coverage Section."),
        tx("gtc-16b", "GTC 16(b)", "Clause", "Terms appearing in bold in these General Terms and Conditions and not defined below in Clause 16(c) Definitions of General Applicability shall have the meaning and/or value ascribed to them in the Declarations or in a particular Coverage Section for purposes of coverage provided under that particular Coverage Section."),
        el("gtc-16c", "GTC 16(c)", "Clause", [
            tx("def-continuity", "16(c) Continuity Date", "Definition", "\"Continuity Date\" means the date set forth in Item 6 of the Declarations with respect to each Coverage Section."),
            tx("def-coverage-section", "16(c) Coverage Section", "Definition", "\"Coverage Section\" means each Coverage Section that is purchased by the Named Entity as reflected in Item 6 of the Declarations."),
            tx("def-e-consultant", "16(c) E-Consultant Firm", "Definition", "\"E-Consultant Firm\" means a pre-approved e-discovery consulting firm. A list of pre-approved E-Consultant Firms is accessible through [the Insurer's online panel directory] under the \"e-Consultant Panel Members\" link."),
            tx("def-e-discovery", "16(c) E-Discovery", "Definition", "\"E-Discovery\" means the development, collection, storage, organization, cataloging, preservation and/or production of electronically stored information."),
            tx("def-e-services", "16(c) E-Discovery Consultant Services", "Definition", "\"E-Discovery Consultant Services\" means solely the following services performed by an E-Consultant Firm: (1) assisting the Insured with managing and minimizing the internal and external costs associated with E-Discovery; (2) assisting the Insured in developing or formulating an E-Discovery strategy which shall include interviewing qualified and cost effective E-Discovery vendors; (3) serving as project manager, advisor and/or consultant to the Insured, defense counsel and the Insurer in executing and monitoring the E-Discovery strategy; and (4) such other services provided by the E-Discovery Consultant Firm that the Insured, Insurer and E-Discovery Consultant Firm agree are reasonable and necessary given the circumstances of the Claim."),
            tx("def-enforcement-body", "16(c) Enforcement Body", "Definition", "\"Enforcement Body\" means: (1) any federal, state, local or foreign law enforcement authority or other governmental investigative authority (including, but not limited to, the U.S. Department of Justice, the U.S. Securities and Exchange Commission and any attorney general), or (2) the enforcement unit of any securities or commodities exchange or other self-regulatory organization."),
            tx("def-foreign-jurisdiction", "16(c) Foreign Jurisdiction", "Definition", "\"Foreign Jurisdiction\" means any jurisdiction, other than the United States of America or any of its territories or possessions."),
            tx("def-organization", "16(c) Organization", "Definition", "\"Organization\" means: (1) the Named Entity; (2) each Subsidiary; and (3) in the event a bankruptcy proceeding shall be instituted by or against any of the foregoing entities, the resulting debtor-in-possession (or equivalent status outside the United States of America), if any."),
            tx("def-policy-period", "16(c) Policy Period", "Definition", "\"Policy Period\" means the period of time from the Inception Date to the earlier of the Expiration Date or the effective date of cancellation of this policy. The Policy Period incepts and expires as of 12:01 A.M. on such dates at the Named Entity Address."),
            tx("def-retroactive", "16(c) Retroactive Date", "Definition", "\"Retroactive Date\" means the date set forth in Item 6 of the Declarations as such for each Coverage Section."),
            tx("def-separate-limit", "16(c) Separate Limit of Liability", "Definition", "\"Separate Limit of Liability\" means the applicable Separate Limit of Liability, if any, stated in Item 6 of the Declarations."),
            tx("def-shared-limit", "16(c) Shared Limit of Liability", "Definition", "\"Shared Limit of Liability\" means the applicable Shared Limit of Liability, if any, stated in Item 6 of the Declarations, which limit of liability shall be shared between all of the Coverage Sections which are listed as being subject to such Shared Limit of Liability in the Declarations."),
            tx("def-transaction", "16(c) Transaction", "Definition", "\"Transaction\" means: (1) the Named Entity consolidating with or merging into another entity such that the Named Entity is not the surviving entity, or selling all or substantially all of its assets to any other person or entity or group of persons or entities acting in concert; (2) any person or entity or group of persons or entities acting in concert acquiring Management Control of the Named Entity; or (3) any additional meaning ascribed to the term Transaction in any Coverage Section, but such additional meaning shall apply solely to the coverage provided by such Coverage Section."),
        ]),
    ]),
])

EXCL_TEXT = {
    "a": "(a) arising out of, based upon or attributable to: (i) with respect to all Claims other than Securities Claims, any: (1) dishonest, fraudulent, criminal or malicious act or omission (other than malicious prosecution), (2) intentional or knowing violation of the law, (3) profit, remuneration or pecuniary advantage to which an Insured Person was not legally entitled, or (4) commingling, misappropriation, or improper use of funds; provided, however, the Insurer will defend a Claim against an Insured Person alleging any of the foregoing conduct until there is a final judgment against, final adjudication against, adverse finding of fact against in a binding arbitration proceeding or plea of guilty or no contest by an Insured Person as to such conduct, at which time the Insured Person shall reimburse the Insurer for Defense Costs; or (ii) with respect to Securities Claims, any: (1) deliberate criminal or deliberate fraudulent act; or (2) profit, remuneration or pecuniary advantage to which an Insured Person was not legally entitled; provided, however, the Insurer will defend a Securities Claim against an Insured Person alleging any of the foregoing conduct until there is a final judgment against, final adjudication against, adverse finding of fact against or plea of guilty or no contest by an Insured Person as to such conduct, at which time the Insured Person shall reimburse the Insurer for Defense Costs;",
    "b": "(b) alleging, arising out of, based upon, or attributable to employment of any individual or any employment practice (including but not limited to wrongful dismissal, discharge or termination, discrimination, harassment, retaliation or other employment-related claim); provided, however, this exclusion shall not apply to the Legal Services provided by an Insured Person in connection with the employment of any individual or any employment practice, whether such Legal Services are provided to a third party or to an Organization;",
    "c": "(c) alleging, arising out of, based upon or attributable to any Wrongful Act committed or omitted prior to the Retroactive Date or any related Wrongful Act thereto, regardless of when such related Wrongful Act is committed or omitted;",
    "d": "(d) alleging, arising out of, based upon or attributable to the facts alleged, or to the same or related Wrongful Act(s) alleged or contained in any claim which has been reported, or in any circumstances of which notice has been given, under any policy of which this Coverage Section is a renewal or replacement of in whole or in part or which it may succeed in time;",
    "e": "(e) alleging, arising out of, based upon or attributable to, as of the Continuity Date, any pending or prior: (i) litigation; or (ii) administrative or regulatory proceeding or investigation of which an Insured had notice, or alleging any Wrongful Act which is the same or related Wrongful Act(s) to that alleged in such pending or prior litigation or administrative or regulatory proceeding or investigation;",
    "f": "(f) alleging, arising out of, based upon or attributable to any bodily injury, sickness, disease or death of any person, or damage to, loss of use of or destruction of any tangible property;",
    "g": "(g) against an Insured Person that is brought, directly or indirectly, by or on behalf an Organization; provided, however, this exclusion shall not apply to Defense Costs incurred in connection with such Claim;",
    "h": "(h) that is brought by a security holder or member of an Organization, whether directly or derivatively, unless such security holder or member Claim is instigated and continued totally independent of, and totally without the solicitation of, or assistance of, or active participation of, or intervention of an Insured Person, an Organization or any Executive of an Organization; provided, however, this exclusion shall not apply to: (i) any Claim brought by any past Executive of an Organization who has not served as a duly elected or appointed director, officer, trustee, governor, management committee member, member of the management board, General Counsel or Risk Manager (or equivalent position) of or consultant for an Organization for at least four (4) years prior to such Claim being first made against any person; or (ii) any Claim brought by an Executive of an Organization formed and operating in a Foreign Jurisdiction against such Organization or any Executive thereof, provided that such Claim is brought and maintained outside the United States of America, Canada or any other common law country (including any territories thereof);",
    "i": "(i) for any violation of responsibilities, obligations or duties imposed by the Employee Retirement Income Security Act of 1974 (ERISA), as amended, or any similar provisions of any state, local or foreign statutory or common law; provided, however, this exclusion shall not apply to Claims arising out of a Corporate Counsel providing Legal Services to an ERISA fiduciary;",
    "j": "(j) for violation(s) of any of the responsibilities, obligations or duties imposed by the Fair Labor Standards Act (except the Equal Pay Act), the National Labor Relations Act, the Worker Adjustment and Retraining Notification Act, the Consolidated Omnibus Budget Reconciliation Act, the Occupational Safety and Health Act, any rules or regulations of the foregoing promulgated thereunder, and amendments thereto or any similar federal, state, local or foreign statutory law or common law;",
    "wage": "It is further understood and agreed that the Insurer shall not be liable to make any payment for Loss in connection with a Claim made against an Insured Person alleging, arising out of, based upon, attributable to or in any way relating to: (i) the refusal, failure or inability of any Insured Person(s), Employee, Executive of the Organization or Organization to pay wages or overtime pay (or amounts representing such wages or overtime pay) for services rendered (as opposed to tort-based back pay or front pay damages for torts other than conversion); (ii) improper payroll deductions taken by any Insured Person(s), Employee, Executive of the Organization or Organization from any Employee(s) or purported Employee(s); or (iii) the failure to provide or enforce legally required meal or rest break periods;",
    "k": "(k) alleging, arising out of, based upon or attributable to any actual or alleged breach of duty, neglect, error, misstatement, misleading statement or omission by an Insured Person in any capacity other than when providing Legal Services;",
    "l": "(l) alleging, arising out of, based upon or attributable to; (i) any actual or threatened discharge, dispersal, release or escape of Pollutants; or (ii) any direction or request to test for, monitor, clean up, remove, contain, treat, detoxify or neutralize Pollutants; provided, however, this exclusion shall not apply to Claims alleging any of the foregoing where the underlying Legal Services performed by an Insured Person giving rise to such Claim were not the direct immediate cause of the foregoing;",
    "m": "(m) alleging, arising out of, based upon or attributable to any misappropriation of a trade secret;",
    "n": "(n) alleging, arising out of, based upon or attributable to any services performed by any contract, seasonal, part-time or leased lawyer other than Legal Services provided for the Organization at the direction of Corporate Counsel;",
    "o": "(o) alleging, arising out of, based upon or attributable to any Insured Person notarizing, certifying or acknowledging any signature not signed by such Insured Person at the time of such notarization, certification or acknowledgment;",
    "p": "(p) alleging, arising out of, based upon or attributable to the return or restitution of fees, expenses or costs, or other disgorgement;",
    "q": "(q) alleging, arising out of, based upon or attributable to the price or consideration paid or proposed to be paid for the acquisition or completion of the acquisition of all or substantially all of the ownership interest in or assets of any entity is inadequate; provided, however, this exclusion shall not apply to Defense Costs or to any Non-Indemnifiable Loss in connection therewith; or",
    "r": "(r) for compensation, salary, wages, fees, benefits, overhead, charges or expenses of any: (i) Insured Person; (ii) Employee; (iii) Executive of the Organization; or (iv) Organization.",
}
EXCL_ORDER = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "wage", "k", "l", "m", "n", "o", "p", "q", "r"]

def excl_oid(k):
    return "CPL 3 (j) wage and hour" if k == "wage" else f"CPL 3({k})"

cpl_3 = el("ccp-3", "CPL 3", "Clause",
    [tx("ccp-3-intro", "CPL 3 intro", "Clause", "Exclusions. The Insurer shall not be liable to make any payment for Loss in connection with any Claim made against an Insured Person:")]
    + [x for k in EXCL_ORDER for x in (
        [tx(f"ccp-3{k}", excl_oid(k), "Clause", EXCL_TEXT[k])]
        + ([tx("ccp-3a-imputation", "CPL 3(a) imputation", "Clause", "For the purpose of determining the applicability of the foregoing Exclusion 3(a): (1) the facts pertaining to and knowledge possessed by any Insured Person shall not be imputed to any other Insured Person; and (2) only facts pertaining to and knowledge possessed by any past, present or future chairman of the board, president, chief executive officer, chief operating officer, chief financial officer or General Counsel (or equivalent positions) of an Organization shall be imputed to an Organization.")] if k == "a" else []))])

cpl = el("cpl", "CPL Coverage Section", "Section", [
    tx("cpl-notice", "CPL notice", "Clause", "Notice: Pursuant to Clause 1 of the General Terms and Conditions, the General Terms and Conditions are incorporated by reference into, made a part of, and are expressly applicable to this CPL Coverage Section, unless otherwise explicitly stated to the contrary in this CPL Coverage Section."),
    tx("cpl-recital", "CPL recital", "Clause", "In consideration of the payment of the premium, and each of their respective rights and obligations in this policy, the Insureds and the Insurer agree as follows:"),
    tx("ccp-1", "CPL 1", "Clause", "Insuring Agreements. All coverage granted for Loss under this Coverage Section is provided solely with respect to Claims first made against an Insured during the Policy Period or any applicable Discovery Period and reported to the Insurer as required by this Coverage Section. Subject to the foregoing and the other terms, conditions and limitations of this policy, this Coverage Section affords the following coverage: A. Counsel Professional Liability. This policy shall pay amounts an Insured Person is legally obligated to pay as Loss arising from any Claim made against such Insured Person for Wrongful Acts, except when and to the extent that the Organization has indemnified the Insured Person for such Loss. B. Organization Indemnification of Insured Persons. This policy shall pay amounts the Organization is legally obligated to pay as Loss arising from any Claim made against an Insured Person for Wrongful Acts, but only to the extent that the Organization has indemnified the Insured Person for such Loss."),
    el("ccp-2", "CPL 2", "Clause", [
        tx("ccp-2a", "CPL 2(a)", "Clause", "The Insurer's Duty To Defend: The Insurer has the right and duty to defend a Claim brought against an Insured Person for Wrongful Acts, even if the Claim is groundless, false or fraudulent. The Insurer shall pay for Defense Costs incurred in the defense of a Claim for Wrongful Acts. The Insurer shall have no duty to defend a Claim insured by D&O Coverage or a Securities Claim."),
        tx("ccp-2b", "CPL 2(b)", "Clause", "Defense Costs: The Insurer shall indemnify for Defense Costs incurred in: (i) any Securities Claim; or (ii) in any Claim where the coverage afforded by this Coverage Section is excess of D&O Coverage, provided that such Defense Costs are incurred with the Insurer's prior written consent in the defense of Wrongful Acts."),
        tx("ccp-2c", "CPL 2(c)", "Clause", "When the Insurer's Duty Ends: The Insurer's duty to defend and any obligation to indemnify an Insured Person shall end: (i) once the Policy Aggregate or any applicable Separate Limit of Liability or Shared Limit of Liability has been exhausted by payment of Defense Costs or Loss; or (ii) if the Insured Person or, if applicable, an Organization, fails or refuses to consent to a settlement that the Insurer recommends and the claimant will accept. The Insured Person must then defend the Claim at their own expense. As a consequence of such failure or refusal to consent, the Insurer's liability for Loss shall not exceed the amount for which the Insurer could have settled such Claim had the Insured Person or, if applicable, an Organization, consented, plus Defense Costs incurred prior the time the Insurer made such recommendation, plus seventy percent (70%) of Defense Costs incurred with the Insurer's consent after the date of the Insured Person's or, if applicable, an Organization's refusal. Provided, however, this subparagraph (c)(ii) shall not apply to the settlement of the following proceedings that are brought in connection with a Securities Claim when such settlement would require an Insured Person to enter into a plea of guilty: (1) criminal proceeding commenced by a return of an indictment, information, notice of charges or similar document; or (2) a civil, administrative or regulatory investigation of an Insured Person by the Securities and Exchange Commission, Department of Justice or a similar state or foreign government authority, commenced by the service of a subpoena on such Insured Person."),
        el("ccp-2d", "CPL 2(d)", "Clause", [
            tx("ccp-2d1", "CPL 2(d)(1)", "Clause", "In addition to providing notice as required under this Coverage Section, each and every Insured Person and Organization must also: (i) send the Insurer copies of all demands, suit papers, other legal documents and invoices for Defense Costs received by such Insured Person, as soon as practicable; (ii) immediately record the specifics of any Claim and the date such Insured Person first received such Claim; (iii) upon the Insurer's request, furnish to the Insurer any and all documentation within the possession of the Insured Person; and (iv) give to the Insurer, and to any counsel the Insurer selects to represent an Insured Person in connection with a Claim, full cooperation and such information as the Insurer or the counsel may require, including, but not limited to, assisting the Insurer or the counsel in: (1) any investigation of a Claim, or other matter relating to the coverage afforded under this Coverage Section (including submission to an examination by the Insurer or the Insurer's designee, under oath if required by the Insurer); (2) making settlements; (3) enforcing any legal rights any Insured Person or the Insurer may have against any person or entity who may be liable to an Insured Person; (4) attending depositions, hearings and trials; (5) securing and giving evidence, and obtaining the attendance of witnesses; and (6) any inspection or survey conducted by the Insurer."),
            tx("ccp-2d2", "CPL 2(d)(2)", "Clause", "No Insured Person or Organization shall admit any liability, settle any Claim, assume any financial obligation or pay any money in connection with any Claim without the Insurer's prior written consent. If any Insured Person or Organization does, it will be at their own expense and such amounts shall not be applied to the applicable Retention."),
            tx("ccp-2d3", "CPL 2(d)(3)", "Clause", "The Insurer shall have the right to associate fully and effectively with each and every Insured Person and, with respect to Insuring Agreement B. Organization Indemnification of Insured Persons, the Organization, in the defense of any Claim or any matter that involves or appears reasonably likely to involve, the Insurer, including, but not limited to, negotiating a settlement."),
            tx("ccp-2d4", "CPL 2(d)(4)", "Clause", "This Coverage Section affords no coverage for Defense Costs incurred by, settlements by or on behalf of, contractual obligations of, or judgments against any entity whether arising out of a Claim made against the Organization, based upon any legal obligation to pay any amount that the Organization has or may have to a claimant, or derived from the acts or omissions of Insured Persons. No Organization is covered in any respect under Insuring Agreement A. Counsel Professional Liability or under Clause 2. DEFENSE AND SETTLEMENT. The Organization is covered, subject to this Coverage Section's terms, conditions, exclusions and other limitations only with respect to its indemnification of Insured Persons under Insuring Agreement B. Organization Indemnification of Insured Persons as respects a Claim against such Insured Person."),
            tx("ccp-2d5", "CPL 2(d)(5)", "Clause", "Panel Counsel: The following shall only apply to a Securities Claims and related Claims for which there is no other D&O Coverage: The list of approved panel counsel law firms (\"Panel Counsel\") is accessible through [the Insurer's online panel directory] under the \"Directors & Officers (Securities Claims)\" link. The list provides the Insureds with a choice of law firms from which a selection of legal counsel shall be made to conduct the defense of any Securities Claim made against such Insureds. With the express prior written consent of the Insurer, an Insured may select a Panel Counsel different from that selected by another Insured defendant if such selection is required due to an actual conflict of interest or is otherwise reasonably justifiable. The list of Panel Counsel may be amended from time to time by the Insurer. However, if a firm is removed from the list during the Policy Period, the Insureds shall be entitled to select such firm to conduct the defense of any Securities Claim made against such Insureds during the Policy Period. The Insureds shall select a Panel Counsel to defend the Securities Claim made against the Insureds in the jurisdiction in which the Securities Claim is brought. In the event the Claim is brought in a jurisdiction not included on the list, the Insureds shall select a Panel Counsel in the listed jurisdiction which is the nearest geographic jurisdiction to either where the Securities Claim is brought or where the headquarters of the Named Entity is located. In such instance the Insureds also may, with the express prior written consent of the Insurer, which consent shall not be unreasonably withheld, select a non-Panel Counsel in the jurisdiction in which the Securities Claim is brought to function as \"local counsel\" on the Claim to assist the Panel Counsel which will function as \"lead counsel\" in conducting the defense of the Securities Claim."),
            tx("ccp-2d6", "CPL 2(d)(6)", "Clause", "In all events, no Insured Person shall intentionally take any action, or fail to take any required action, which prejudices the Insurer's rights."),
        ]),
    ]),
    cpl_3,
    tx("ccp-4", "CPL 4", "Clause", "Retention. In addition to the provisions of Clause 2. RETENTION of the General Terms and Conditions, in no event shall a Retention be applied to: (i) Non-Indemnifiable Loss; or (ii) Securities Claims to which, pursuant to Clause 6. OTHER INSURANCE, this Coverage Section applies only as excess."),
    el("ccp-5", "CPL 5", "Clause", [
        tx("ccp-5-intro", "CPL 5 intro", "Clause", "Notice and Reporting. Notice hereunder shall be given in writing to the Insurer at the Claims Address indicated in the Declarations. If mailed or transmitted by electronic mail, the date of such mailing or transmission shall constitute the date that such notice was given and proof of mailing or transmission shall be sufficient proof of notice."),
        tx("ccp-5a", "CPL 5(a)", "Clause", "Reporting a Claim. An Organization or an Insured shall, as a condition precedent to the obligations of the Insurer under this policy notify the Insurer in writing of a Claim made against an Insured as soon as practicable after the Named Entity's Risk Manager or General Counsel (or equivalent position) first becomes aware of the Claim. In all such events, notification must be provided no later than 90 days after the end of the Policy Period or the Discovery Period (if applicable)."),
        tx("ccp-5b", "CPL 5(b)", "Clause", "Relation Back to the First Reported Claim. Solely for the purpose of establishing whether any subsequent Related Claim was first made during the Policy Period or Discovery Period (if applicable), if during any such period a Claim was first made and reported in accordance with Clause 5(a) above, then any Related Claim that is subsequently made against an Insured and that is reported in accordance with Clause 5(a) above shall be deemed to have been first made at the time that such previously reported Claim was first made. With respect to any subsequent Related Claim, this policy shall not cover Loss incurred before such subsequent Related Claim is actually made against an Insured."),
        tx("ccp-5c", "CPL 5(c)", "Clause", "Relation Back to Reported Circumstances Which May Give Rise to a Claim. If during the Policy Period or Discovery Period (if applicable) an Organization or an Insured Person becomes aware of and notifies the Insurer in writing of circumstances that may give rise to a Claim being made against an Insured and provides details as required below, then any Claim that is subsequently made against an Insured that arises from such circumstances and that is reported in accordance with Clause 5(a) above shall be deemed to have been first made at the time of the notification of circumstances for the purpose of establishing whether such subsequent Claim was first made during the Policy Period or during the Discovery Period (if applicable). Coverage for Loss arising from any such subsequent Claim shall only apply to Loss incurred after that subsequent Claim is actually made against an Insured. In order to be effective, notification of circumstances must specify the facts, circumstances, nature of the alleged Wrongful Act anticipated and reasons for anticipating such Claim, with full particulars as to dates, persons and entities involved; however, notification that includes a copy of an agreement to toll a statute of limitations shall be presumed sufficiently specific as to the potential Claims described within that agreement."),
    ]),
])

FORM = [
    tx("policyholder-notice", "Policyholder notice", "Clause", "Policyholder Notice. Thank you for purchasing insurance from a member company of [the insurer's group]. The member companies generally pay compensation to brokers and independent agents, and may have paid compensation in connection with your policy. You can review and obtain information about the nature and range of compensation paid by member companies to brokers and independent agents [at the insurer's website or telephone number].", NOMEANING),
    tx("front-notice", "Front notice", "Clause", "NOTICE: CERTAIN COVERAGE SECTIONS OF THIS POLICY ARE LIMITED TO LIABILITY FOR CLAIMS THAT ARE FIRST MADE AGAINST THE INSUREDS DURING THE POLICY PERIOD AND REPORTED IN WRITING TO THE INSURER AS REQUIRED BY THE TERMS OF THE POLICY. COVERED DEFENSE COSTS SHALL REDUCE THE APPLICABLE LIMITS OF LIABILITY AND SUBLIMITS OF LIABILITY AND ARE SUBJECT TO APPLICABLE RETENTIONS. THE INSURER DOES NOT ASSUME ANY DUTY TO DEFEND UNLESS SUCH COVERAGE IS EXPRESSLY PROVIDED WITHIN A COVERAGE SECTION. PLEASE READ THIS POLICY CAREFULLY AND REVIEW IT WITH YOUR INSURANCE AGENT OR BROKER.", NOMEANING),
    decl,
    tx("tria-disclosure", "TRIA disclosure", "Clause", "Policyholder Disclosure: Notice of Terrorism Insurance Coverage (Coverage Included). Coverage for acts of terrorism is included in your policy. [The statutory disclosure under the Terrorism Risk Insurance Act, as amended in 2015, follows: the Act's definition of an act of terrorism, the federal reimbursement percentages by year, and the $100 billion annual cap.] The portion of your annual premium that is attributable to coverage for acts of terrorism is $0, and does not include any charges for the portion of losses covered by the United States government under the Act.", NOMEANING),
    gtc,
    el("do", "Non-Profit D&O Coverage Section", "Section", []),
    el("epl", "EPL Coverage Section", "Section", []),
    el("fid", "Fiduciary Coverage Section", "Section", []),
    cpl,
]

ALL_IDS = []

def emit_node(n, r):
    i, oid, et, kind, payload, flags = n
    ALL_IDS.append(i)
    if kind == "el":
        w(f"ex:{i} a wrd:Element ;")
        w(f"    fnd:hasIdentity ex:{i}-identity ; fnd:hasGovernanceState fnd:Active ;")
        tail = " ;" if payload else " ."
        w(f'    wrd:elementType wrd-voc:{et} ; wrd:objectId "{oid}" ; wrd:rankKey "{rank(r)}"{tail}')
        if payload:
            w("    wrd:directlyComprises " + " , ".join(f"ex:{c[0]}" for c in payload) + " .")
        for k, c in enumerate(payload):
            emit_node(c, k)
        return
    vids = [p[1] for p in payload if isinstance(p, tuple)]
    w(f"ex:{i} a wrd:Text ;")
    w(f"    fnd:hasIdentity ex:{i}-identity ; fnd:hasGovernanceState fnd:Active ;")
    w(f'    wrd:elementType wrd-voc:{et} ; wrd:objectId "{oid}" ; wrd:rankKey "{rank(r)}" ;')
    w("    wrd:inclusionMode wrd-voc:Mandatory ;")
    if NOMEANING in flags:
        w("    ins:encodingStatus ins-voc:NoMeaning ;")
    if vids:
        w("    wrd:directlyComprises " + " , ".join(f"ex:{v}" for v in vids) + " ;")
    parts = []
    for k, p in enumerate(payload):
        if isinstance(p, tuple):
            parts.append(f"[ a wrd:TextPart ; wrd:partIndex {k} ; wrd:refersToVariable ex:{p[1]}-identity ]")
        else:
            parts.append(f"[ a wrd:TextPart ; wrd:partIndex {k} ;\n        wrd:partText {lit(p)} ]")
    w("    wrd:hasTextPart " + " ,\n                    ".join(parts) + " .")
    for k, v in enumerate(vids):
        key, space, multi = VARS[v]
        w(f"ex:{v} a wrd:EmbeddedVariable ;")
        w(f"    fnd:hasIdentity ex:{v}-identity ; fnd:hasGovernanceState fnd:Active ;")
        sp = f" ; wrd:valueSpace ex:{space}" if space else ""
        w(f'    wrd:variableKey "{key}" ; wrd:rankKey "z{k}"{sp} ; wrd:multiValued {"true" if multi else "false"} .')

# ------------------------------------------------------------------ the file
HEADER = open(sys.argv[2]).read()
w(HEADER)
w("# ==== The form: wording =======================================================")
w("#")
w("# The fragment's text, anonymised and lightly normalised: the PDF extraction")
w("# scrambled CPL 5(b) and the table cells of GTC 16(c), whose reading order is")
w("# restored. Each leaf is one clause, or one paragraph where the clause is a")
w("# list. A leaf with no stated meaning and no ins:encodingStatus is not yet")
w("# assessed (§18.5): those are the gaps, listed in clause-map.md.")
w("")
w("ex:form a wrd:Wording ;")
w("    fnd:hasIdentity ex:form-identity ; fnd:hasGovernanceState fnd:Active ;")
w("    wrd:directlyComprises " + " , ".join(f"ex:{n[0]}" for n in FORM) + " .")
w("")
for k, n in enumerate(FORM):
    emit_node(n, k)
    w("")

w(open(sys.argv[3]).read())

# ---- exclusions, generated: one term per clause, one exclusion per insuring agreement
EXCL_SCOPE = {"a": "conduct-adjudicated", "b": "employment-not-legal-services", "c": "act-before-retro-date",
              "d": "noticed-under-prior-policy", "e": "pending-or-prior-as-of-continuity", "f": "bodily-injury-property-damage",
              "g": "brought-by-organization-not-defense-costs", "h": "security-holder-claim-not-carved-back", "i": "erisa-not-counsel-to-fiduciary",
              "j": "labour-statutes", "wage": "wage-and-hour", "k": "capacity-other-than-legal-services", "l": "pollution-not-carved-back",
              "m": "trade-secret", "n": "contract-lawyer-not-directed", "o": "notarizing-unsigned", "p": "disgorgement",
              "q": "inadequate-consideration-not-carved-back", "r": "compensation-and-overhead"}
w("# ---- CPL 3: exclusions --------------------------------------------------------")
w("#")
w("# Each excludes Loss under both insuring agreements. An exclusion excepts one")
w("# relation (ins:excepts is functional), so each clause's term has two: one")
w("# excepting A, owed to the Insured Person, one excepting B, owed to the")
w("# indemnifying Organization. The holder is the excepted obligation's obligor")
w("# (law I8). Carve-backs are negated members of the scope (ADR-A103).")
w("")
for k in EXCL_ORDER:
    t = f"ccp-3{k}"
    w(f"tmpl:term-{t} a ins:Term , ins:Template ; ins:expressedIn ex:{t} .")
    for ag, party in (("a", "InsuredPerson"), ("b", "IndemnifyingOrganization")):
        w(f"tmpl:excl-3{k}-{ag} a ins:Exclusion , ins:Template ;")
        w(f"    ins:arisesUnder tmpl:term-{t} ;")
        w(f"    ins:holder ex:Insurer ; ins:counterparty ex:{party} ;")
        w(f"    ins:excepts tmpl:pay-{ag} ;")
        w(f"    ins:scope ex:{EXCL_SCOPE[k]} .")
    w("")

w(open(sys.argv[4]).read())

# ---- conditions, generated: stated, not yet evaluable (C13) -------------------
ATOMS = {
    # the claims-made trigger
    "first-made-in-period": "the Claim was first made against an Insured during the Policy Period or an applicable Discovery Period",
    "reported-as-required": "the Claim was reported to the Insurer as CPL 5 requires",
    "for-wrongful-acts": "the Claim is made against an Insured Person for Wrongful Acts",
    "claim-made": "a Claim has been made against an Insured Person",
    "indemnified": "the Organization has indemnified the Insured Person for the Loss",
    "securities-claim": "the Claim is a Securities Claim",
    "insured-by-do": "the Claim is insured by D&O Coverage",
    "excess-of-do": "the coverage of the CPL section is excess of D&O Coverage",
    "no-other-do": "there is no other D&O Coverage for the Claim",
    "insurer-consented": "the Insurer gave its prior written consent",
    "limits-exhausted": "the Policy Aggregate, or an applicable Separate or Shared Limit, is exhausted by payment of Defense Costs or Loss",
    "settlement-refused": "the Insured Person or Organization fails or refuses to consent to a settlement the Insurer recommends and the claimant will accept",
    "guilty-plea-securities": "the settlement is of a Securities Claim proceeding, criminal or an investigation, that would require a plea of guilty",
    "unconsented-settlement": "the amount was admitted, settled, assumed or paid without the Insurer's prior written consent",
    "entity-own-liability": "the Loss is an entity's own, not its indemnification of an Insured Person",
    "refusal-unreasonable": "refusing consent to local counsel would be unreasonable",
    "intentional": "the act or failure to act is intentional",
    # exclusion facts
    "conduct-dishonest": "dishonest, fraudulent, criminal or malicious act or omission, other than malicious prosecution",
    "conduct-violation": "intentional or knowing violation of the law",
    "illegal-profit": "profit, remuneration or pecuniary advantage to which the Insured Person was not legally entitled",
    "conduct-commingling": "commingling, misappropriation or improper use of funds",
    "deliberate-criminal-fraud": "deliberate criminal or deliberate fraudulent act",
    "finally-adjudicated": "final judgment, final adjudication, adverse finding in binding arbitration, or plea of guilty or no contest, as to the conduct",
    "employment": "employment of any individual or any employment practice",
    "legal-services-employment": "Legal Services provided by an Insured Person in connection with employment or an employment practice",
    "noticed-under-prior-policy": "facts or related Wrongful Acts reported, or noticed as circumstances, under a policy this section renews, replaces or succeeds",
    "proceeding-with-notice": "an administrative or regulatory proceeding or investigation pending or prior as of the Continuity Date, of which an Insured had notice",
    "bodily-injury-property-damage": "bodily injury, sickness, disease or death, or damage to or loss of use of tangible property",
    "brought-by-organization": "brought, directly or indirectly, by or on behalf of an Organization",
    "loss-is-defense-costs": "the Loss is Defense Costs",
    "non-indemnifiable-loss": "the Loss is Non-Indemnifiable Loss",
    "security-holder-claim": "brought by a security holder or member of an Organization, not totally independent of Insureds and Executives",
    "past-executive-4-years": "brought by a past Executive who has not served in the listed positions for at least four years",
    "foreign-executive-claim": "brought by an Executive of an Organization in a Foreign Jurisdiction, and maintained outside the United States, Canada and other common law countries",
    "erisa": "a violation of duties under ERISA or similar law",
    "counsel-to-erisa-fiduciary": "arising out of Corporate Counsel providing Legal Services to an ERISA fiduciary",
    "labour-statutes": "a violation of the FLSA (except the Equal Pay Act), NLRA, WARN Act, COBRA, OSHA or similar law",
    "wage-and-hour": "unpaid wages or overtime, improper payroll deductions, or meal or rest breaks not provided",
    "capacity-other-than-legal-services": "an Insured Person's act in a capacity other than providing Legal Services",
    "pollution": "discharge of Pollutants, or a direction or request to test for or clean them up",
    "legal-services-not-direct-cause": "the underlying Legal Services were not the direct immediate cause",
    "trade-secret": "misappropriation of a trade secret",
    "contract-lawyer-not-directed": "services by a contract, seasonal, part-time or leased lawyer, other than Legal Services for the Organization at the direction of Corporate Counsel",
    "notarizing-unsigned": "notarizing, certifying or acknowledging a signature not signed by the Insured Person at the time",
    "disgorgement": "return or restitution of fees, expenses or costs, or other disgorgement",
    "inadequate-consideration": "inadequate price or consideration for acquiring all or substantially all of an entity",
    "compensation-and-overhead": "compensation, salary, wages, fees, benefits, overhead, charges or expenses of an Insured Person, Employee, Executive or Organization",
    # GTC facts
    "premium-unpaid": "the premium has not been paid",
    "not-complied": "the terms of the policy have not all been complied with",
    "not-finally-determined": "the Insured's obligation to pay is not finally determined by judgment after trial or written agreement",
    "insolvency": "an Insured or its estate is bankrupt or insolvent",
    "merger-or-sale": "the Named Entity merges or consolidates without surviving, or sells all or substantially all its assets",
    "management-control-acquired": "a person or group acting in concert acquires Management Control of the Named Entity",
    "particulars-in-30-days": "the Insurer received full particulars of the Transaction within 30 days of it",
    "spouse-claim": "the Claim is against a spouse, domestic partner, estate, heir or legal representative of an Insured Person, for the Insured Person's Wrongful Acts",
    "spouse-own-acts": "the Loss arises from the spouse's or partner's own act, error or omission",
    # CPL 5
    "notice-sent": "the notice was mailed or e-mailed on that date",
    "notice-given": "the notice was given on that date",
    "related-to-reported-claim": "the Claim is a Related Claim of a Claim first made and reported in the period",
    "arises-from-notified-circumstances": "the Claim arises from circumstances notified in the period with the required details",
    "circumstances-specific": "the notification of circumstances is sufficiently specific",
    "tolling-agreement-attached": "the notification includes a copy of an agreement tolling a statute of limitations",
    "loss-before-actual-claim": "the Loss was incurred before the subsequent Claim was actually made",
    # filters and condition words
    "is-insured-person": "the person is an Insured Person under the CPL section",
    "is-organization": "the entity is an Organization",
    "is-spouse-or-representative": "the person is a spouse, domestic partner, estate, heir or legal representative of an Insured Person",
    "is-e-consultant-firm": "the firm is a pre-approved e-discovery consulting firm",
    "is-e-discovery": "the activity develops, collects, stores, organises, catalogues, preserves or produces electronically stored information",
    "is-e-discovery-services": "the services are among those listed, performed by an E-Consultant Firm",
    "is-enforcement-body": "the body is a law enforcement or investigative authority, or an exchange's or self-regulatory organisation's enforcement unit",
    "is-foreign-jurisdiction": "the jurisdiction is not the United States or its territories or possessions",
}
NEG = {"not-indemnified": "indemnified", "not-securities-claim": "securities-claim", "not-guilty-plea-securities": "guilty-plea-securities",
       "not-legal-services-employment": "legal-services-employment", "not-defense-costs": "loss-is-defense-costs",
       "not-non-indemnifiable": "non-indemnifiable-loss", "not-past-executive": "past-executive-4-years",
       "not-foreign-executive": "foreign-executive-claim", "not-counsel-to-erisa-fiduciary": "counsel-to-erisa-fiduciary",
       "not-direct-cause": "legal-services-not-direct-cause", "not-spouse-own-acts": "spouse-own-acts"}
ALL, ANY = "AllRequired", "AnySufficient"
COMP = {
    "covered-claim": (ALL, ["first-made-in-period", "reported-as-required", "for-wrongful-acts"]),
    "do-or-securities": (ANY, ["insured-by-do", "securities-claim"]),
    "securities-or-excess": (ANY, ["securities-claim", "excess-of-do"]),
    "consented-costs-scope": (ALL, ["securities-or-excess", "insurer-consented"]),
    "hammer-applies": (ALL, ["settlement-refused", "not-guilty-plea-securities"]),
    "securities-claim-without-do": (ALL, ["securities-claim", "no-other-do"]),
    "nonsecurities-conduct": (ANY, ["conduct-dishonest", "conduct-violation", "illegal-profit", "conduct-commingling"]),
    "securities-conduct": (ANY, ["deliberate-criminal-fraud", "illegal-profit"]),
    "nonsecurities-adjudicated": (ALL, ["not-securities-claim", "nonsecurities-conduct", "finally-adjudicated"]),
    "securities-adjudicated": (ALL, ["securities-claim", "securities-conduct", "finally-adjudicated"]),
    "conduct-adjudicated": (ANY, ["nonsecurities-adjudicated", "securities-adjudicated"]),
    "employment-not-legal-services": (ALL, ["employment", "not-legal-services-employment"]),
    "pending-or-prior-as-of-continuity": (ANY, ["litigation-by-continuity", "proceeding-with-notice"]),
    "brought-by-organization-not-defense-costs": (ALL, ["brought-by-organization", "not-defense-costs"]),
    "security-holder-claim-not-carved-back": (ALL, ["security-holder-claim", "not-past-executive", "not-foreign-executive"]),
    "erisa-not-counsel-to-fiduciary": (ALL, ["erisa", "not-counsel-to-erisa-fiduciary"]),
    "pollution-not-carved-back": (ALL, ["pollution", "not-direct-cause"]),
    "inadequate-consideration-not-carved-back": (ALL, ["inadequate-consideration", "not-defense-costs", "not-non-indemnifiable"]),
    "action-not-ripe": (ANY, ["not-complied", "not-finally-determined"]),
    "transaction-meaning": (ANY, ["merger-or-sale", "management-control-acquired"]),
    "spousal-scope": (ALL, ["spouse-claim", "not-spouse-own-acts"]),
}
HAND = {"act-before-retro-date", "litigation-by-continuity", "policy-period-span"}
known = set(ATOMS) | set(NEG) | set(COMP) | HAND
for cid, (_, members) in COMP.items():
    assert set(members) <= known, (cid, set(members) - known)
body = "\n".join(L)
import re
used = set(re.findall(r"ins:(?:scope|condition|means|deems|when|resolutionFilter) (ex:[a-z][\w-]*)", body))
used |= {m for line in re.findall(r"ins:means ([^.;]+)", body) for m in re.findall(r"ex:([a-z][\w-]*)", line)}
missing = {u[3:] if u.startswith("ex:") else u for u in used} - known - {"NamedEntity", "Subsidiary", "DebtorInPossession"}
missing = {m for m in missing if not m[0].isupper()}
assert not missing, missing

w("# ---- conditions: stated, not yet evaluable (C13) ------------------------------")
w("#")
w("# Facts of the claims file, each a concept the case either shows or does not.")
w("# Carve-backs are the same concept, negated (ADR-A103). Composites state the")
w("# clause's logic, with AnySufficient for its \"or\".")
w("")
w("ex:claim-facts a voc:ConceptScheme ;")
w("    fnd:hasIdentity ex:claim-facts-identity ; fnd:hasGovernanceState fnd:Active ;")
w("    skos:prefLabel \"Claim facts\"@en .")
def cond(cid, concept, negated=False):
    w(f"ex:{cid} a elg:Condition ;")
    w(f'    elg:conditionKey "{cid}" ;')
    w("    elg:matchStrategy elg:ExactMatch ; elg:compatibilityOperation elg:AllRequired ;")
    w("    elg:wildcardSemantics elg:NoWildcard ;")
    w(f"    elg:requiredConcept ex:{concept}-fact" + (" ;\n    elg:negated true ." if negated else " ."))
for cid, label in ATOMS.items():
    w(f'ex:{cid}-fact a skos:Concept ; skos:inScheme ex:claim-facts ; rdfs:label {lit(label)} .')
    cond(cid, cid)
w("")
for cid, of in NEG.items():
    cond(cid, of, True)
w("")
for cid, (op, members) in COMP.items():
    w(f"ex:{cid} a elg:Condition ;")
    w(f'    elg:conditionKey "{cid}" ;')
    w(f"    elg:matchStrategy elg:ExactMatch ; elg:compatibilityOperation elg:{op} ;")
    w("    elg:wildcardSemantics elg:NoWildcard ;")
    w("    elg:hasCondition " + " , ".join(f"ex:{m}" for m in members) + " .")
w("")

# ---- the instance's assembled wording and values
VALUES = {
    "var-named-entity": "wrd:value ex:named-entity-occ",
    "var-ne-address": 'wrd:literalValue "[Named Entity Address, withheld]"',
    "var-ne-state": 'wrd:literalValue "[withheld]"',
    "var-inception": 'wrd:value [ a qnt:Quantity ; qnt:onSpace ex:time ; qnt:numericValue "2024-06-01T00:01:00-04:00"^^xsd:dateTime ]',
    "var-expiration": 'wrd:value [ a qnt:Quantity ; qnt:onSpace ex:time ; qnt:numericValue "2025-06-01T00:01:00-04:00"^^xsd:dateTime ]',
    "var-insurer-address": 'wrd:literalValue "[Insurer Address, withheld]"',
    "var-claims-address": 'wrd:literalValue "[Claims Address, withheld]"',
    "var-claims-email": 'wrd:literalValue "[claims e-mail, withheld]"',
}
MONEY = {"var-premium": 71447, "var-aggregate": 6000000, "var-do-shared-limit": 4000000, "var-do-excess": 500000,
         "var-do-retention": 50000, "var-do-premium": 32570, "var-epl-shared-limit": 4000000, "var-epl-retention-class": 250000,
         "var-epl-retention-third": 50000, "var-epl-retention-other": 50000, "var-epl-premium": 33590,
         "var-fid-separate-limit": 1000000, "var-fid-retention-securities": 0, "var-fid-retention-other": 0, "var-fid-premium": 2800,
         "var-cpl-separate-limit": 1000000, "var-cpl-retention": 10000, "var-cpl-premium": 2487, "var-tria-premium": 0}
DATES = {"var-do-continuity": "2007-04-26", "var-epl-continuity": "2007-04-26", "var-fid-continuity": "2019-08-01",
         "var-cpl-continuity": "2019-12-01", "var-cpl-retro": "2019-12-01"}
for v, n in MONEY.items():
    VALUES[v] = f'wrd:value [ a qnt:Quantity ; qnt:onSpace ex:usd-space ; qnt:numericValue "{n}"^^xsd:decimal ; qnt:inUnit ex:usd ]'
for v, d in DATES.items():
    VALUES[v] = f'wrd:value [ a qnt:Quantity ; qnt:onSpace ex:time ; qnt:numericValue "{d}T00:00:00Z"^^xsd:dateTime ]'
assert set(VALUES) == set(VARS), set(VARS) ^ set(VALUES)

w("# ==== The instance: what the policy stores (D1) ===============================")
w("")
w("ex:policy-wording-v1 a wrd:AssembledWording ;")
w("    fnd:hasIdentity ex:policy-wording-identity ; fnd:hasGovernanceState fnd:Active ;")
w("    wrd:assembledFrom ex:form ;")
w("    wrd:includes " + " ,\n                 ".join(", ".join(f"ex:{i}" for i in ALL_IDS[k:k + 6]) for k in range(0, len(ALL_IDS), 6)).replace(", ", " , ") + " ;")
w("    wrd:hasValue " + " ,\n                 ".join(f"ex:v-{v[4:]}" for v in VARS) + " .")
w("")
for v in VARS:
    w(f"ex:v-{v[4:]} a wrd:VariableValue ; wrd:forVariable ex:{v} ;\n    {VALUES[v]} .")
w("")
w(open(sys.argv[5]).read())

open(OUT, "w").write("\n".join(L) + "\n")
print(len(ALL_IDS), "elements,", len(VARS), "variables")
