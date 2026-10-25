from dataclasses import dataclass
import numpy as np

N = 4096  # FFT nokta sayısı


@dataclass
class CaptureParams:
    bits: int = 14
    fs_mhz: float = 100.0
    fin_mhz: float = 10.3
    amp_dbfs: float = -1.0
    noise_lsb: float = 0.7
    hd2_dbc: float = -85.0
    hd3_dbc: float = -80.0
    seed: int = 1


def _db(x):
    return 10 * np.log10(np.maximum(x, 1e-30))


def simulate(p: CaptureParams):
    """Sanal ADC yakalaması üretir. (kodlar, kullanılan FFT bin numarası) döner."""
    m = round(p.fin_mhz / p.fs_mhz * N)
    if m % 2 == 0:
        m += 1                      # tek bin: koherent örnekleme
    m = min(max(m, 3), N // 2 - 1)

    full_scale = 2 ** (p.bits - 1)
    amp = 10 ** (p.amp_dbfs / 20) * full_scale
    rng = np.random.default_rng(p.seed)

    x = np.sin(2 * np.pi * m * np.arange(N) / N)
    y = x + 10 ** (p.hd2_dbc / 20) * x**2 + 10 ** (p.hd3_dbc / 20) * x**3
    raw = amp * y + rng.normal(0, p.noise_lsb, N)
    codes = np.clip(np.round(raw), -full_scale, full_scale - 1)
    return codes, m


def analyze(codes, m: int, bits: int) -> dict:
    """FFT ile SNR, SINAD, SFDR, THD ve ENOB hesaplar."""
    full_scale = 2 ** (bits - 1)
    half = N // 2
    P = np.abs(np.fft.rfft(codes)[:half]) ** 2
    P[0] = 0.0                       # DC'yi dışarıda bırak

    signal = P[m]
    harmonics = set()
    for h in range(2, 7):
        f = (h * m) % N
        if f > half:
            f = N - f                # aliasing: ayna frekansı
        if 0 < f < half and f != m:
            harmonics.add(f)
    dist = sum(P[f] for f in harmonics)
    noise = max(P.sum() - signal - dist, 1e-30)

    mask = np.ones(half, dtype=bool)
    mask[[0, m]] = False
    spur = P[mask].max()

    sinad = _db(signal / (noise + dist))
    amp_lsb = np.sqrt(signal) * 2 / N
    enob = (sinad - 1.76 + 20 * np.log10(full_scale / amp_lsb)) / 6.02

    return {
        "snr_db": float(_db(signal / noise)),
        "sinad_db": float(sinad),
        "sfdr_dbc": float(_db(signal / spur)),
        "thd_db": float(_db(dist / signal)),
        "enob": float(enob),
    }

def spectrum_dbfs(codes, bits: int):
    """Tek taraflı spektrum, 0 dBFS = tam ölçekli sinüs."""
    half = N // 2
    P = np.abs(np.fft.rfft(codes)[:half]) ** 2
    full = (2 ** (bits - 1) * N / 2) ** 2
    return _db(P / full)

