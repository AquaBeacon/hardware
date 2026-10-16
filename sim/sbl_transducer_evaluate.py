"""Evaluate measured sweep data without inventing transducer parameters.

Input columns: unit_id,frequency_hz,z_real_ohm,z_imag_ohm,
transfer_real,transfer_imag,tx_vrms,noise_vrms,noise_bandwidth_hz

Transfer is complex V_received / V_at_transmitting_transducer, NOT TVR/RVS.
Use the same fixed transmitter, distance, geometry, receiver gain, cable and
noise bandwidth for all units. Phase comparisons include uncorrected geometry.
Measurements alone do not establish maximum safe voltage or a depth rating.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

FIELDS = ('unit_id', 'frequency_hz', 'z_real_ohm', 'z_imag_ohm',
          'transfer_real', 'transfer_imag', 'tx_vrms', 'noise_vrms', 'noise_bandwidth_hz')


def assess(rows):
    if not rows:
        raise ValueError('No measurements. A header-only template is not measured data.')
    groups = {}
    for row in rows:
        if set(FIELDS) - set(row):
            raise ValueError('Missing CSV columns: ' + ', '.join(set(FIELDS)-set(row)))
        unit = str(row['unit_id']).strip()
        if not unit:
            raise ValueError('unit_id is empty')
        values = [float(row[k]) for k in FIELDS[1:]]
        if not np.isfinite(values).all():
            raise ValueError('NaN/Inf is not valid measurement data')
        groups.setdefault(unit, []).append(values)
    if len(groups) < 2:
        raise ValueError('At least two units are required to compare common bandwidth.')
    units = sorted(groups)
    arrays = [np.array(sorted(groups[u], key=lambda row: row[0])) for u in units]
    f = arrays[0][:, 0]
    if len(f) < 11 or np.any(np.diff(f) <= 0) or f[0] < 20000 or f[-1] > 80000:
        raise ValueError('Use at least 11 unique increasing frequency points in 20..80 kHz.')
    if np.max(np.diff(f)) > 100:
        raise ValueError('Sweep spacing must be <=100 Hz for this comparison workflow.')
    for a in arrays:
        if a.shape != arrays[0].shape or not np.array_equal(a[:, 0], f):
            raise ValueError('All units must use exactly the same frequency grid.')
        if np.any(a[:, 1] < 0) or np.any(a[:, 5:] <= 0):
            raise ValueError('Require nonnegative resistance and positive drive/noise/bandwidth.')
        if not np.all(a[:, 7] == arrays[0][0, 7]):
            raise ValueError('Noise bandwidth must be identical for every measurement.')
    z = np.stack([a[:, 1] + 1j*a[:, 2] for a in arrays])
    h = np.stack([a[:, 3] + 1j*a[:, 4] for a in arrays])
    if np.any(np.abs(z) <= 0) or np.any(np.abs(h) <= 0):
        raise ValueError('Zero impedance/transfer cannot be used in this analysis.')
    gain = 20*np.log10(np.abs(h))
    rel = gain-gain.max(axis=1)[:, None]
    snr = np.stack([20*np.log10(np.abs(h[i])*a[:, 5]/a[:, 6]) for i, a in enumerate(arrays)])
    # Engineering screening thresholds, NOT sufficient conditions for 10 cm accuracy.
    mask = np.all((rel >= -6) & (snr >= 10), axis=0)
    idx = np.flatnonzero(mask)
    runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1)+1) if len(idx) else []
    segments = [dict(f_low_hz=float(f[r[0]]), f_high_hz=float(f[r[-1]]),
                     width_hz=float(f[r[-1]]-f[r[0]])) for r in runs if len(r) >= 2]
    best = max(segments, key=lambda s: s['width_hz']) if segments else None
    # Relative phase cancels common flight time; it does not cancel position error.
    # Rejecting phase-wrap ambiguity still requires a controlled equal-path fixture.
    ratios = h/h[0]
    relative_delay = -np.gradient(np.unwrap(np.angle(ratios), axis=1), f, axis=1)/(2*np.pi)
    summaries = []
    for i, unit in enumerate(units):
        row = dict(unit_id=unit, minimum_impedance_ohm=float(np.abs(z[i]).min()),
                   maximum_current_per_drive_volt_A_per_V=float((1/np.abs(z[i])).max()))
        if best:
            in_band = (f >= best['f_low_hz']) & (f <= best['f_high_hz'])
            d = relative_delay[i, in_band]
            row.update(relative_group_delay_median_us=float(np.median(d)*1e6),
                       relative_group_delay_span_us=float(np.ptp(d)*1e6),
                       minimum_measured_snr_db=float(snr[i, in_band].min()))
        summaries.append(row)
    return dict(status='MEASURED_SWEEP_SCREEN_ONLY', reference_unit=units[0],
                noise_bandwidth_hz=float(arrays[0][0, 7]),
                common_band_segments=segments, preferred_measured_band=best,
                meets_provisional_8khz_bandwidth_screen=bool(best and best['width_hz'] >= 8000),
                units=summaries, safe_transmit_voltage_vrms=None,
                verified_20m_range=False, verified_10cm_accuracy=False,
                caveats=['Transfer includes transmitter, propagation and receiver; it is not absolute sensitivity.',
                         'Relative delay includes residual cable/electronic/position errors.',
                         '100 Hz spacing assumes controlled small relative delays; check phase unwrap.',
                         'A bandwidth screen pass is not a ranging or waterproofing qualification.'])


def self_test():
    rows = []
    for i, delay in enumerate((0, .3e-6, .7e-6, -.2e-6)):
        for f in np.arange(30000., 60001., 100.):
            h = .01*np.exp(-2j*np.pi*f*(.001+delay))
            z = 100+1/(2j*np.pi*f*2.4e-9)
            rows.append(dict(zip(FIELDS, [str(i), f, z.real, z.imag, h.real, h.imag, .01, 1e-6, 8000])))
    result = assess(rows)
    assert result['preferred_measured_band']['width_hz'] == 30000
    assert result['meets_provisional_8khz_bandwidth_screen']
    assert abs(result['units'][2]['relative_group_delay_median_us']-.7) < 1e-8
    assert result['safe_transmit_voltage_vrms'] is None
    assert result['verified_20m_range'] is False
    cases = [[], rows[:10], [dict(rows[0], frequency_hz=float('nan'))],
             [dict(r, noise_vrms=0) for r in rows],
             [rows[0]] + rows, [dict(r, noise_bandwidth_hz=4000) if r['unit_id']=='1' else r for r in rows]]
    for bad in cases:
        try:
            assess(bad)
        except ValueError:
            continue
        raise AssertionError('Invalid or incomplete measurements were accepted')
    print('PASS: synthetic flat response, fractional delay, invalid/missing data rejection.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='?', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.csv is None:
        parser.error('Provide measured CSV or --self-test')
    try:
        with args.csv.open(encoding='utf-8-sig', newline='') as stream:
            result = assess(list(csv.DictReader(stream)))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    out = args.out or args.csv.with_suffix('.assessment.json')
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
