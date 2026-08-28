import { render, screen } from '@testing-library/react'
import BrandMark, { letterSpacingFor } from './BrandMark'

describe('BrandMark', () => {
  it('SUPERSUB 를 그린다', () => {
    render(<BrandMark />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
  })

  it('자간은 크기 × 1.2 / 44 다 — 앱과 같은 공식', () => {
    expect(letterSpacingFor(44)).toBeCloseTo(1.2)
    expect(letterSpacingFor(34)).toBeCloseTo(34 * 1.2 / 44)
    expect(letterSpacingFor(88)).toBeCloseTo(2.4)
  })
})
