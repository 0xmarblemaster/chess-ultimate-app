import { describe, it, expect } from 'vitest'
import type { NextApiRequest, NextApiResponse } from 'next'
import handler from '../pages/api/position-analysis'

/**
 * The position-analysis endpoint exposes Mastra's CCP (PositionPrompter) over
 * HTTP so Hermes can reuse the exact `<detailed_board_analysis>` fusion the
 * in-app coach uses. Purely additive route.
 */
function mockRes() {
  const res: Record<string, unknown> = {}
  res.statusCode = 200
  res.status = (code: number) => {
    res.statusCode = code
    return res
  }
  res.json = (body: unknown) => {
    res.body = body
    return res
  }
  res.setHeader = () => res
  return res as unknown as NextApiResponse & { statusCode: number; body: unknown }
}

describe('POST /api/position-analysis', () => {
  it('returns the detailed board analysis for a valid FEN', () => {
    const req = {
      method: 'POST',
      body: { fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' },
    } as NextApiRequest
    const res = mockRes()
    handler(req, res)
    expect(res.statusCode).toBe(200)
    const body = res.body as { valid: boolean; board_analysis: string }
    expect(body.valid).toBe(true)
    expect(body.board_analysis).toContain('<detailed_board_analysis>')
  })

  it('returns 400 when fen is missing', () => {
    const req = { method: 'POST', body: {} } as NextApiRequest
    const res = mockRes()
    handler(req, res)
    expect(res.statusCode).toBe(400)
    expect((res.body as { error: string }).error).toBeTruthy()
  })

  it('returns 405 for non-POST methods', () => {
    const req = { method: 'GET', body: {} } as NextApiRequest
    const res = mockRes()
    handler(req, res)
    expect(res.statusCode).toBe(405)
  })

  it('does not crash on a malformed FEN (returns a JSON error response)', () => {
    const req = { method: 'POST', body: { fen: 'not-a-fen' } } as NextApiRequest
    const res = mockRes()
    expect(() => handler(req, res)).not.toThrow()
    expect(res.body).toBeTruthy()
  })
})
