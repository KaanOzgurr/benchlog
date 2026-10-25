export type NewRun = {
  bits: number
  fs_mhz: number
  fin_mhz: number
  amp_dbfs: number
  noise_lsb: number
  hd2_dbc: number
  hd3_dbc: number
  seed: number
  min_enob: number
}

export type Run = NewRun & {
  id: number
  created_at: string
  snr_db: number
  sinad_db: number
  sfdr_dbc: number
  thd_db: number
  enob: number
  status: 'pass' | 'fail'
}

export type Spectrum = {
  fs_mhz: number
  dbfs: number[]
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)

  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (Array.isArray(body.detail)) {
        msg = body.detail.map((d: { msg: string }) => d.msg).join('; ')
      } else if (body.detail) {
        msg = String(body.detail)
      }
    } catch {
      // yanıt gövdesi JSON değil, varsayılan mesajı kullan
    }
    throw new Error(msg)
  }

  return res.status === 204 ? (undefined as T) : res.json()
}

export const listRuns = () => request<Run[]>('/api/runs')

export const getSpectrum = (id: number) =>
  request<Spectrum>(`/api/runs/${id}/spectrum`)

export const deleteRun = (id: number) =>
  request<void>(`/api/runs/${id}`, { method: 'DELETE' })

export const createRun = (body: NewRun) =>
  request<Run>('/api/runs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })