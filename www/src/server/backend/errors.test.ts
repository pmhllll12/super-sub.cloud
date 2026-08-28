import { BackendError, parseErrorBody, errorResponseBody } from './errors'

describe('parseErrorBody', () => {
  it('계약 형태의 에러에서 code 와 message 를 꺼낸다', () => {
    const e = parseErrorBody(401, {
      error: { code: 'INVALID_CREDENTIALS', message: '이메일 또는 비밀번호가 올바르지 않습니다.' },
    })
    expect(e.status).toBe(401)
    expect(e.code).toBe('INVALID_CREDENTIALS')
    expect(e.message).toBe('이메일 또는 비밀번호가 올바르지 않습니다.')
  })

  it('형태가 어긋난 본문이면 UNKNOWN_ERROR 로 떨어진다', () => {
    const e = parseErrorBody(500, '<html>502 Bad Gateway</html>')
    expect(e.status).toBe(500)
    expect(e.code).toBe('UNKNOWN_ERROR')
  })

  it('본문이 비어도 던지지 않는다', () => {
    const e = parseErrorBody(503, null)
    expect(e.code).toBe('UNKNOWN_ERROR')
  })
})

describe('errorResponseBody', () => {
  it('계약과 같은 형태로 되돌린다', () => {
    const e = new BackendError(404, 'CARD_NOT_FOUND', '카드가 없습니다.')
    expect(errorResponseBody(e)).toEqual({
      error: { code: 'CARD_NOT_FOUND', message: '카드가 없습니다.' },
    })
  })
})
