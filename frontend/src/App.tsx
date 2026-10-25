import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { createRun, deleteRun, getSpectrum, listRuns } from './api'
import type { NewRun, Run, Spectrum } from './api'
import './index.css'

const DEFAULTS: NewRun = {
  bits: 14, fs_mhz: 100, fin_mhz: 10.3, amp_dbfs: -1,
  noise_lsb: 0.7, hd2_dbc: -85, hd3_dbc: -80, seed: 1, min_enob: 11.5,
}

const FIELDS: { key: keyof NewRun; label: string }[] = [
  { key: 'bits', label: 'Resolution (bit)' },
  { key: 'fs_mhz', label: 'Sample rate (MHz)' },
  { key: 'fin_mhz', label: 'Input freq (MHz)' },
  { key: 'amp_dbfs', label: 'Input level (dBFS)' },
  { key: 'noise_lsb', label: 'Noise (LSB rms)' },
  { key: 'hd2_dbc', label: 'HD2 (dBc)' },
  { key: 'hd3_dbc', label: 'HD3 (dBc)' },
  { key: 'min_enob', label: 'Spec: min ENOB' },
]

export default function App() {
  const [form, setForm] = useState<NewRun>(DEFAULTS)
  const [runs, setRuns] = useState<Run[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [spectrum, setSpectrum] = useState<Spectrum | null>(null)
  const [error, setError] = useState('')

  const selected = runs.find((r) => r.id === selectedId) ?? null

  useEffect(() => {
    listRuns()
      .then((rs) => {
        setRuns(rs)
        if (rs.length) setSelectedId(rs[0].id)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  useEffect(() => {
    if (selectedId === null) {
      setSpectrum(null)
      return
    }
    getSpectrum(selectedId).then(setSpectrum).catch((e: Error) => setError(e.message))
  }, [selectedId])

  async function onRun() {
    setError('')
    try {
      const run = await createRun({ ...form, seed: Math.floor(Math.random() * 65535) + 1 })
      setRuns((rs) => [run, ...rs])
      setSelectedId(run.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteRun(id)
      const rest = runs.filter((r) => r.id !== id)
      setRuns(rest)
      if (selectedId === id) setSelectedId(rest[0]?.id ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    }
  }

  const data = spectrum
    ? spectrum.dbfs.slice(1).map((db, i) => ({
        mhz: ((i + 1) * spectrum.fs_mhz) / (2 * spectrum.dbfs.length),
        db: Math.max(db, -120),
      }))
    : []

  return (
    <main>
      <h1>BenchLog</h1>
      <p className="sub">Simulated ADC capture, FFT metrics and a history of runs.</p>

      <div className="layout">
        <section>
          <h2>Capture setup</h2>
          {FIELDS.map(({ key, label }) => (
            <label key={key}>
              {label}
              <input
                type="number"
                step="any"
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: Number(e.target.value) })}
              />
            </label>
          ))}
          <button onClick={onRun}>Run capture</button>
          {error && <p className="error" role="alert">{error}</p>}
        </section>

        <section>
          <h2>
            Result{' '}
            {selected && <span className={`badge ${selected.status}`}>{selected.status.toUpperCase()}</span>}
          </h2>
          {selected ? (
            <div className="metrics">
              <div><b>{selected.enob.toFixed(2)}</b><span>ENOB (bit)</span></div>
              <div><b>{selected.snr_db.toFixed(1)}</b><span>SNR (dB)</span></div>
              <div><b>{selected.sinad_db.toFixed(1)}</b><span>SINAD (dB)</span></div>
              <div><b>{selected.sfdr_dbc.toFixed(1)}</b><span>SFDR (dBc)</span></div>
              <div><b>{selected.thd_db.toFixed(1)}</b><span>THD (dB)</span></div>
            </div>
          ) : (
            <p className="empty">No run selected. Choose Run capture to create one.</p>
          )}
          <div className="chart">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#c3d0d8" />
                                <XAxis
                  dataKey="mhz"
                  type="number"
                  domain={[0, 'dataMax']}
                  tickCount={6}
                  tickFormatter={(v: number) => v.toFixed(0)}
                  unit=" MHz"
                />
                <YAxis
                  type="number"
                  domain={[-120, 0]}
                  ticks={[-120, -100, -80, -60, -40, -20, 0]}
                  allowDataOverflow
                  unit=" dB"
                  width={64}
                />
                <Line dataKey="db" dot={false} stroke="#0b7f86" strokeWidth={1} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section>
        <h2>Run history</h2>
        {runs.length === 0 ? (
          <p className="empty">No runs yet.</p>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Run</th><th>Bits</th><th>Fin MHz</th><th>SNR dB</th><th>SFDR dBc</th><th>ENOB</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className={r.id === selectedId ? 'sel' : ''} onClick={() => setSelectedId(r.id)}>
                    <td>#{r.id}</td><td>{r.bits}</td><td>{r.fin_mhz}</td>
                    <td>{r.snr_db.toFixed(1)}</td><td>{r.sfdr_dbc.toFixed(1)}</td><td>{r.enob.toFixed(2)}</td>
                    <td><span className={`badge ${r.status}`}>{r.status.toUpperCase()}</span></td>
                    <td>
                      <button className="ghost" aria-label={`Delete run ${r.id}`}
                        onClick={(e) => { e.stopPropagation(); onDelete(r.id) }}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}