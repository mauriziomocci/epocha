export const meta = {
  name: 'economy-base-layer-audit',
  description: 'First adversarial scientific audit of the Epocha economy base layer (5 substrate modules), findings adversarially verified two ways and synthesized with a per-module verdict',
  phases: [
    { title: 'Audit', detail: 'one hostile scientific auditor per substrate module vs cited sources' },
    { title: 'Verify', detail: 'two diverse skeptics per finding: source-accuracy and materiality' },
    { title: 'Synthesize', detail: 'cross-module consistency + consolidated report + per-module verdict' },
  ],
}

const REPO = '/Users/mauriziomocci/Documents/workspace/Opensource/epocha'

const MODULES = [
  {
    key: 'production',
    path: 'epocha/apps/economy/production.py',
    claims: 'Constant Elasticity of Substitution (CES) production function Q = A·[Σ αᵢ Xᵢ^ρ]^(1/ρ) with ρ = (σ-1)/σ, Cobb-Douglas log fallback near σ=1, Leontief minimum near σ=0. Cited: Arrow, Chenery, Minhas & Solow (1961) "Capital-Labor Substitution and Economic Efficiency" RES 43(3); multi-factor extension per Shoven & Whalley (1992) applied CGE practice.',
  },
  {
    key: 'monetary',
    path: 'epocha/apps/economy/monetary.py',
    claims: 'Fisher identity (MV = PT / MV = PY) used as a diagnostic (not a price rule) plus a money-velocity counter. Cited: Fisher (1911) The Purchasing Power of Money. Verify the identity form implemented, the velocity definition, and that it is genuinely diagnostic-only.',
  },
  {
    key: 'market',
    path: 'epocha/apps/economy/market.py',
    claims: 'Walrasian tâtonnement (Walras 1874 Éléments d’économie politique pure): prices nudged proportional to excess demand until relative excess < convergence threshold or an iteration cap is hit. The cap is the safety net for the non-convergence regime with 3+ goods (Scarf 1960 "Some Examples of Global Instability of the Competitive Equilibrium"). Verify the adjustment rule form, the excess-demand definition, the stopping criterion, and whether numeraire / Walras-law handling is correct.',
  },
  {
    key: 'distribution',
    path: 'epocha/apps/economy/distribution.py',
    claims: 'Simplified Ricardian rent decomposition (Ricardo 1817 Principles) plus a flat per-tick wage and tax flow. Verify the rent formula against Ricardian differential-rent theory, the wage/tax flow accounting (does output distribute without leakage or double counting), and any conservation-of-value property.',
  },
  {
    key: 'initialization',
    path: 'epocha/apps/economy/initialization.py',
    claims: 'Per-era-template seeding of the base balance sheet (currencies, initial money stock, factor endowments, prices). Less formula-heavy: audit for parameter justification (are seed values cited or tagged tunable), internal consistency of the seeded state (does the initial balance sheet balance / are stock-flow consistent), and whether the seeding could put the substrate in an unphysical or non-reproducible state.',
  },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['module', 'findings'],
  properties: {
    module: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'category', 'claim', 'location', 'evidence', 'source_check', 'severity'],
        properties: {
          id: { type: 'string', description: 'short id like PROD-1' },
          category: { type: 'string', enum: ['INCORRECT', 'UNJUSTIFIED', 'INCONSISTENT', 'MISSING', 'VERIFIED'] },
          claim: { type: 'string', description: 'the model/formula/constant/assumption under review, one sentence' },
          location: { type: 'string', description: 'file:line anchor(s)' },
          evidence: { type: 'string', description: 'what the code actually does vs what the source says; be specific' },
          source_check: { type: 'string', description: 'the specific claim in the cited primary source and whether the code matches it' },
          severity: { type: 'string', enum: ['high', 'medium', 'low', 'none'] },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['survives', 'confidence', 'reasoning', 'refined_category'],
  properties: {
    survives: { type: 'boolean', description: 'true if the finding is a real, defensible defect after adversarial scrutiny' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'string' },
    refined_category: { type: 'string', enum: ['INCORRECT', 'UNJUSTIFIED', 'INCONSISTENT', 'MISSING', 'VERIFIED', 'REJECTED'] },
  },
}

const SYNTHESIS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['per_module', 'cross_module_findings', 'overall_verdict', 'summary'],
  properties: {
    per_module: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['module', 'verdict', 'incorrect_count', 'unjustified_count', 'inconsistent_count', 'missing_count', 'note'],
        properties: {
          module: { type: 'string' },
          verdict: { type: 'string', enum: ['CONVERGED', 'NOT CONVERGED'] },
          incorrect_count: { type: 'integer' },
          unjustified_count: { type: 'integer' },
          inconsistent_count: { type: 'integer' },
          missing_count: { type: 'integer' },
          note: { type: 'string' },
        },
      },
    },
    cross_module_findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['issue', 'modules', 'category', 'evidence'],
        properties: {
          issue: { type: 'string' },
          modules: { type: 'string' },
          category: { type: 'string', enum: ['INCORRECT', 'UNJUSTIFIED', 'INCONSISTENT', 'MISSING'] },
          evidence: { type: 'string' },
        },
      },
    },
    overall_verdict: { type: 'string', enum: ['CONVERGED', 'NOT CONVERGED'] },
    summary: { type: 'string' },
  },
}

function auditPrompt(m) {
  return `You are a HOSTILE adversarial scientific reviewer (Round 1, phase-2 gate) for the Epocha project — a scientific civilization simulator whose GOLDEN RULE is that every formula, parameter and algorithm must be grounded in a cited source. Your mandate is to FIND ERRORS, not confirm correctness. Confirmation bias is the enemy.

Repository: ${REPO}

Target module: ${m.path}
Claimed science: ${m.claims}

Do this:
1. Read the FULL module (Read ${REPO}/${m.path}) and its docstrings/comments.
2. For EVERY formula, constant, and algorithm: verify it against the SPECIFIC cited primary source. Recall the actual mathematical form the source defines and compare it line-by-line to the code. A formula that "looks right" but deviates from the source (wrong exponent placement, wrong aggregation, missing normalization, wrong fallback boundary, sign error) is INCORRECT.
3. For every numeric constant/parameter: is its value justified with a source or explicitly tagged as a tunable design heuristic? An unjustified magic number is UNJUSTIFIED.
4. Check the algorithm implementation matches the claimed algorithm (e.g. does the tâtonnement actually nudge proportional to excess demand and respect Walras' law / a numeraire? does the CES fallback trigger at the correct σ boundaries and match the limiting form? does the Fisher identity use consistent aggregates?).
5. Check every simplification is documented with what the full model would be and what is lost (undocumented simplification = MISSING).
6. Check internal consistency of definitions and units WITHIN the module.
7. Cross-check anchors: cite exact file:line for every finding. Verify line numbers by reading.

Grep the codebase if you need to see how a value is defined elsewhere (e.g. a config default). Be specific and adversarial. If something is genuinely correct and well-sourced, record it as VERIFIED with the evidence — do not pad with false positives, but do not miss real defects.

Return the structured findings for this module. Every finding needs a file:line location, the concrete evidence (code vs source), and the source_check (what the source actually says).`
}

function verifyPrompt(f, lens) {
  const lensText = lens === 'source'
    ? `SOURCE-ACCURACY lens: Is the auditor's reading of the cited primary source correct? Recall what the source ACTUALLY says about this formula/parameter/algorithm. The auditor may have misremembered the source, applied a stricter standard than the source warrants, or flagged a legitimate modeling choice as an error. Try hard to REFUTE the finding on source grounds. If the code actually matches the source (or a defensible standard variant of it), the finding does NOT survive.`
    : `MATERIALITY lens: Even if technically accurate, does this finding matter for a scientific simulation of this kind? Is it a real defect that would mislead a reader or corrupt a result, or is it a pedantic nit, a documented tunable heuristic, or a simplification the module already discloses? A finding that is technically true but immaterial or already-disclosed does NOT survive as an actionable defect. Try hard to REFUTE.`

  return `You are an adversarial VERIFIER for a scientific audit of the Epocha economy base layer. A prior auditor produced this finding; your job is to REFUTE it, not agree. Default to survives=false when genuinely uncertain — a finding must earn its place.

Repository: ${REPO}

Finding under review:
- Module: ${f._module} (${f._path})
- Category: ${f.category} / Severity: ${f.severity}
- Claim: ${f.claim}
- Location: ${f.location}
- Evidence given: ${f.evidence}
- Source check given: ${f.source_check}

${lensText}

Read the actual code at the cited location (Read/Grep in ${REPO}) before deciding — do not rule from memory of the finding text alone. Then return your verdict: survives (is this a real, defensible, actionable defect after your adversarial scrutiny), your confidence, your reasoning, and the refined category (REJECTED if it does not survive).`
}

// ---- Phase 1+2: audit each module, then verify each finding two ways (pipeline, no barrier) ----
phase('Audit')
const perModule = await pipeline(
  MODULES,
  (m) => agent(auditPrompt(m), { label: `audit:${m.key}`, phase: 'Audit', schema: FINDINGS_SCHEMA, effort: 'high' })
    .then((r) => ({ m, findings: (r?.findings || []).map((f) => ({ ...f, _module: m.key, _path: m.path })) })),
  (audited) => {
    // verify only substantive (non-VERIFIED) findings; keep VERIFIED as-is for the record
    const substantive = audited.findings.filter((f) => f.category !== 'VERIFIED')
    const verifiedRecord = audited.findings.filter((f) => f.category === 'VERIFIED')
    return parallel(
      substantive.map((f) => () =>
        parallel([
          () => agent(verifyPrompt(f, 'source'), { label: `verify-src:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' }),
          () => agent(verifyPrompt(f, 'materiality'), { label: `verify-mat:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA, effort: 'high' }),
        ]).then((verds) => {
          const v = verds.filter(Boolean)
          // finding survives only if BOTH lenses let it through (conjunctive: a defect must be both real per-source and material)
          const survives = v.length === 2 && v.every((x) => x.survives)
          return { ...f, verdicts: v, survives, refined: survives ? (v[0].refined_category !== 'REJECTED' ? v[0].refined_category : f.category) : 'REJECTED' }
        })
      )
    ).then((verified) => ({ module: audited.m.key, verifiedRecord, verified: verified.filter(Boolean) }))
  }
)

// flatten
const allVerified = perModule.flatMap((pm) => (pm ? pm.verified : []))
const confirmed = allVerified.filter((f) => f.survives)
const rejected = allVerified.filter((f) => !f.survives)
const verifiedRecords = perModule.flatMap((pm) => (pm ? pm.verifiedRecord : []))
log(`Audit produced ${allVerified.length} substantive findings; ${confirmed.length} survived adversarial verification, ${rejected.length} rejected; ${verifiedRecords.length} items recorded VERIFIED.`)

// ---- Phase 3: cross-module consistency + synthesis (barrier: needs ALL confirmed findings at once) ----
phase('Synthesize')
const confirmedForSynth = confirmed.map((f) => ({
  module: f._module, id: f.id, category: f.refined, severity: f.severity,
  claim: f.claim, location: f.location, evidence: f.evidence, source_check: f.source_check,
}))
const synthesis = await agent(
  `You are the lead scientific auditor synthesizing a Round 1 adversarial audit of the Epocha economy base layer (5 substrate modules: production, monetary, market, distribution, initialization; ${REPO}).

The following findings SURVIVED two-lens adversarial verification (source-accuracy AND materiality). Findings that did not survive were dropped and are not shown.

CONFIRMED FINDINGS (JSON):
${JSON.stringify(confirmedForSynth, null, 2)}

Also, ${verifiedRecords.length} items were recorded as VERIFIED (correct and well-sourced) by the module auditors.

Your job:
1. Do a CROSS-MODULE consistency pass that no single-module auditor could do: check that shared definitions and units agree across modules (e.g. does "price" mean the same in market.py and monetary.py; are money aggregates consistent between monetary.py and initialization.py; does the output Q from production.py distribute without leakage in distribution.py; is the tick-flow accounting stock-flow consistent end to end). Read the actual modules under ${REPO}/epocha/apps/economy/ as needed to confirm any cross-module issue — do not invent.
2. Assign a per-module verdict: CONVERGED means no surviving INCORRECT or UNJUSTIFIED findings for that module (INCONSISTENT/MISSING may be documented rather than fixed, but note them); NOT CONVERGED otherwise.
3. Give the overall verdict for the economy base layer.
4. Write a concise summary (the honest state: what is sound, what must be fixed before this layer can be promoted from whitepaper §8.2 to §4 Methods).

Return the structured synthesis.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTHESIS_SCHEMA, effort: 'high' }
)

return {
  confirmed: confirmedForSynth,
  rejected: rejected.map((f) => ({ module: f._module, id: f.id, claim: f.claim, why: f.verdicts?.map((v) => v.reasoning).join(' | ') })),
  verifiedCount: verifiedRecords.length,
  synthesis,
}
