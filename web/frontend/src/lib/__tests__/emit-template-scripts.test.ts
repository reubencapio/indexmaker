/**
 * Generates the Python snippet for every built-in template.
 *
 * Doubles as a dev tool: set CODEGEN_OUT_DIR and the generated files are written
 * to disk so they can be executed against the real indexforge library, which is
 * the only check that proves they actually run.
 *
 *   CODEGEN_OUT_DIR=/tmp/gen npx vitest run src/lib/__tests__/emit-template-scripts.test.ts
 *   for f in /tmp/gen/*.py; do python "$f"; done
 *
 * The assertions here hold without a Python toolchain, so CI still gets value.
 */
import { describe, it, expect } from 'vitest'
import { mkdirSync, writeFileSync } from 'fs'
import { indexTemplates } from '../../data/templates'
import { generatePythonCode } from '../codegen'
import { IndexConfiguration } from '../../types'

const OUT_DIR = process.env.CODEGEN_OUT_DIR

describe('every built-in template generates a complete script', () => {
  it.each(indexTemplates.map(t => [t.id, t] as const))('%s', (id, template) => {
    const code = generatePythonCode(template.config as IndexConfiguration)

    if (OUT_DIR) {
      mkdirSync(OUT_DIR, { recursive: true })
      writeFileSync(`${OUT_DIR}/${id.replace(/-/g, '_')}.py`, code)
    }

    // Every snippet must be a complete, self-contained program: imports, an
    // index, a universe, a weighting scheme, a schedule, and the wiring.
    expect(code).toMatch(/^from indexforge import \(/)
    expect(code).toContain('index = Index.create(')
    expect(code).toContain('universe = (Universe.builder()')
    expect(code).toContain('weighting = ')
    expect(code).toContain('rebalancing = RebalancingSchedule.')
    expect(code).toContain('.set_universe(universe)')
    expect(code).toContain('.set_weighting_method(weighting)')
    expect(code).toContain('.set_rebalancing_schedule(rebalancing)')

    // No unresolved placeholders should reach the user.
    expect(code).not.toContain('undefined')
    expect(code).not.toContain('[object Object]')
    expect(code).not.toContain('NaN')
  })
})
