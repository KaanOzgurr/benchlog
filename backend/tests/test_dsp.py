from app.dsp import CaptureParams, simulate, analyze


def run(**kw):
    p = CaptureParams(**kw)
    codes, m = simulate(p)
    return analyze(codes, m, p.bits)


def test_ideal_adc_enob_close_to_bits():
    r = run(bits=12, amp_dbfs=-0.1, noise_lsb=0.0, hd2_dbc=-200, hd3_dbc=-200)
    assert abs(r["enob"] - 12) < 0.3


def test_more_noise_lowers_enob():
    clean = run(noise_lsb=0.5)
    noisy = run(noise_lsb=3.0)
    assert noisy["enob"] < clean["enob"]


def test_same_seed_is_reproducible():
    assert run(seed=7) == run(seed=7)