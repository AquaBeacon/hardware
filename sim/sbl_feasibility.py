"""SBL geometry and chirp estimator study. Synthetic data, NOT hardware validation.

Run: python -X utf8 sim/sbl_feasibility.py
Sound speed, bandwidth, noise, multipath and timing errors below are assumptions.
No TVR/RVS or actual transducer bandwidth is inferred from static capacitance.
"""
from pathlib import Path
import json
import math
import numpy as np
from scipy.signal import correlate
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / 'pcb/SPRESENSE_SBL/research'
C = 1500.0  # assumed uniform sound speed [m/s]; replace with measurements
FS = 192000.0  # Sony supported PCM sample rate, not analog bandwidth
RANGE = 20.0
BASELINE = 1.0  # maximum pair separation; equilateral triangle side length
TARGET = 0.1
RX = BASELINE * np.array([[0, 1/np.sqrt(3), 0],
                          [-.5, -1/(2*np.sqrt(3)), 0], [.5, -1/(2*np.sqrt(3)), 0]])
# The fourth analog channel observes attenuated actual TX electrical waveform.
# That creates an ADC-domain epoch; acoustic TX delay still needs calibration.
TX = np.zeros(3)


def travel_time(p):
    """Two-way propagation to child then to each receiver; zero child offset.
    Child turnaround delay is assumed measured and subtracted, not inferred here.
    """
    return (np.linalg.norm(p - TX) + np.linalg.norm(p - RX, axis=1)) / C


def jacobian(p):
    a = (p - TX) / np.linalg.norm(p - TX)
    b = (p - RX) / np.linalg.norm(p - RX, axis=1)[:, None]
    return (a + b) / C


def geometry(rng):
    """Local linear Gaussian error propagation, conditional on correct path ID.
    Common turnaround/TX-reference error is correlated across all 3 RX channels.
    This deliberately excludes bias from geometry, sound speed, motion and echoes.
    """
    rows = []
    for tilt in (0, 30, 60, 80):
        theta = np.deg2rad(tilt)
        p = RANGE * np.array([np.sin(theta), 0, np.cos(theta)])
        j = jacobian(p)
        # Independently check analytical Jacobian against central differences.
        h = 1e-4
        numeric = np.column_stack([(travel_time(p + np.eye(3)[k]*h) -
                                   travel_time(p - np.eye(3)[k]*h))/(2*h) for k in range(3)])
        assert np.allclose(j, numeric, atol=1e-10, rtol=1e-6)
        for ch_us in (.5, 1.0, 2.0):
            common_us = 10.0
            count = len(RX)
            cov_t = (ch_us*1e-6)**2*np.eye(count) + (common_us*1e-6)**2*np.ones((count, count))
            cov_p = np.linalg.inv(j.T @ np.linalg.solve(cov_t, j))
            assert np.linalg.eigvalsh(cov_p).min() > 0
            samples = rng.multivariate_normal(np.zeros(3), cov_p, size=50000)
            rows.append(dict(tilt_deg=tilt, channel_sigma_us=ch_us,
                             common_sigma_us=common_us,
                             position_error_p95_m=float(np.quantile(np.linalg.norm(samples, axis=1), .95)),
                             sigma_xyz_m=np.sqrt(np.diag(cov_p)).tolist()))
    # A flat array alone cannot disambiguate the two half-spaces.
    assert np.allclose(travel_time(np.array([3., 2., 19.])), travel_time(np.array([3., 2., -19.])))
    return rows


def chirp_at(t, bw, phase=0.0):
    """Hypothetical analytic LFM signal, 8 ms, 47 kHz center, 10% Tukey edges.
    Carrier phase is unknown. Complex correlation magnitude cannot use absolute
    carrier phase as an unrealistically perfect delay reference.
    """
    duration = .008
    ramp = .0004
    w = np.ones_like(t)
    left = t < ramp
    right = t > duration-ramp
    w[left] = .5 * (1-np.cos(np.pi*np.clip(t[left]/ramp, 0, 1)))
    w[right] = .5 * (1-np.cos(np.pi*np.clip((duration-t[right])/ramp, 0, 1)))
    w[(t < 0) | (t >= duration)] = 0
    f0 = 47000-bw/2
    assert f0 > 0 and f0+bw < FS/2
    return w*np.exp(1j*(2*np.pi*(f0*t + .5*bw/duration*t*t) + phase))


def peak_delay(y, template):
    a = np.abs(correlate(y, template, mode='valid', method='fft'))
    k = int(np.argmax(a))
    if k == 0 or k == len(a)-1:
        return float(k)
    den = a[k-1] - 2*a[k] + a[k+1]
    offset = .5*(a[k-1]-a[k+1])/den if den < 0 else 0
    return k + float(np.clip(offset, -.5, .5))


def chirp_trials(rng):
    results = []
    template_t = np.arange(round(.008*FS))/FS
    t = np.arange(len(template_t)+220)/FS
    for bw in (2000., 8000., 16000.):
        template = chirp_at(template_t, bw)
        energy = float(np.mean(np.abs(template)**2))
        for snr_db in (0., 10., 20.):
            for echo in (False, True):
                errors = []
                for _ in range(160):
                    delays = [70 + rng.uniform(-.5, .5), 71.3 + rng.uniform(-.5, .5)]
                    estimated = []
                    for delay in delays:
                        phase = rng.uniform(-np.pi, np.pi)
                        y = chirp_at(t-delay/FS, bw, phase)
                        if echo:
                            # Unknown path for each channel, fixed relative amplitude.
                            # No claim these delays describe the intended field site.
                            tau = rng.uniform(20e-6, 150e-6)
                            y += .6*chirp_at(t-delay/FS-tau, bw, rng.uniform(-np.pi, np.pi))
                        sigma = np.sqrt(energy / 10**(snr_db/10) / 2)
                        y += sigma*(rng.normal(size=len(t)) + 1j*rng.normal(size=len(t)))
                        estimated.append(peak_delay(y, template))
                    errors.append(((estimated[1]-estimated[0]) - (delays[1]-delays[0]))/FS)
                values = np.array(errors)
                results.append(dict(bandwidth_hz=bw, per_sample_snr_db=snr_db,
                                    echo=echo, trials=len(errors),
                                    tdoa_rmse_us=float(np.sqrt(np.mean(values**2))*1e6),
                                    tdoa_abs_error_p95_us=float(np.quantile(np.abs(values), .95)*1e6)))
    # A noiseless fractional delay is resolved without supplying the true delay to estimator.
    d = 70.37
    estimate = peak_delay(chirp_at(t-d/FS, 16000., 1.2), chirp_at(template_t, 16000.))
    assert abs(estimate-d) < .05, (estimate, d)
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260914)
    g = geometry(rng)
    s = chirp_trials(rng)
    q = dict(sound_speed_assumed_m_s=C, range_m=RANGE, maximum_baseline_m=BASELINE,
             receiver_coordinates_m=RX.tolist(),
             sample_period_us=1e6/FS,
             broadside_tdoa_full_budget_us=TARGET*BASELINE/(RANGE*C)*1e6,
             one_sample_crossrange_m=RANGE*C/(BASELINE*FS),
             roundtrip_ms=2*RANGE/C*1000,
             full_budget_sound_speed_error_m_s=TARGET*C/RANGE,
             full_budget_baseline_scale_error_mm=TARGET*BASELINE/RANGE*1000,
             full_budget_attitude_error_deg=math.degrees(TARGET/RANGE),
             parts_for_one_parent_and_one_child=6, purchased_if_two_per_pack=6,
             transducer_only_total_usd=round(3*32.84, 2), evaluation_pair_usd=32.84,
             sample_count_8ms=round(.008*FS), pcm_4ch_16bit_MB_s=FS*4*2/1e6,
             pcm_4ch_24bit_MB_s=FS*4*3/1e6, pcm_4ch_int32_MB_s=FS*4*4/1e6,
             max_tdoa_us=BASELINE/C*1e6, carrier_cycle_57k_us=1e6/57000)
    assert q['broadside_tdoa_full_budget_us'] < q['sample_period_us']
    report = dict(status='SYNTHETIC_STUDY_ONLY', hardware_validation=False,
                  selected_transducer_bandwidth_hz=None, verified_20m_range=False,
                  verified_10cm_accuracy=False, quantities=q, geometry=g, chirp_estimator=s,
                  caveats=['No measured TVR/RVS, impedance, acoustic noise, or waterproofing data.',
                           'Estimator uses hypothetical bandlimited chirps, not SMC20D17H5 response.',
                           'Geometry assumes correct path detection, stationary nodes, uniform sound speed.',
                           'Geometry covariance excludes systematic errors; it is not a total accuracy budget.',
                           'Receiver calibration and actual ADC transfer response remain unmeasured.'])
    (OUT/'feasibility.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    for sigma in (.5, 1., 2.):
        rows = [x for x in g if x['channel_sigma_us'] == sigma]
        axs[0].plot([x['tilt_deg'] for x in rows], [x['position_error_p95_m']*100 for x in rows],
                    'o-', label=f'{sigma:g} us/channel')
    axs[0].axhline(10, color='black', ls='--', label='10 cm target')
    axs[0].set(xlabel='Angle from array normal (degrees)', ylabel='3D position error P95 (cm)',
               title='Local geometry: 20 m, 1 m triangle + TX monitor')
    axs[0].legend(fontsize=8)
    for echo in (False, True):
        rows = [x for x in s if x['per_sample_snr_db'] == 10 and x['echo'] == echo]
        axs[1].plot([x['bandwidth_hz']/1000 for x in rows], [x['tdoa_abs_error_p95_us'] for x in rows],
                    'o-', label='Assumed echo' if echo else 'AWGN only')
    axs[1].axhline(q['broadside_tdoa_full_budget_us'], color='black', ls='--', label='Full 10 cm timing budget')
    axs[1].set(xlabel='Hypothetical chirp bandwidth (kHz)', ylabel='Pairwise TDOA error P95 (us)',
               title='Synthetic correlation: SNR 10 dB/sample', yscale='log')
    axs[1].legend(fontsize=8)
    fig.suptitle('Feasibility study - NOT a hardware performance claim')
    fig.savefig(OUT/'feasibility.png', dpi=170)
    plt.close(fig)
    print(json.dumps(q, indent=2))
    for row in g:
        if row['channel_sigma_us'] == 1:
            print('GEOMETRY', row)
    for row in s:
        if row['per_sample_snr_db'] == 10:
            print('SYNTHETIC CHIRP', row)
    print('PASS: numerical checks; hardware/range/accuracy remain UNVERIFIED.')


if __name__ == '__main__':
    main()
