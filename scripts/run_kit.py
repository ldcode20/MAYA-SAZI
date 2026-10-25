"""Run 24 reproducible-but-resampled event-level cases through MAYA's live stack.

This is an authored policy/robustness kit, not a prevalence-weighted accuracy test.
Every feature is recomputed from the generated event history for this run.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from online_features import numeric, snapshot  # noqa: E402
from simulator_service import LiveModel, apply_policy  # noqa: E402
from simulation import EPOCH, generate_world  # noqa: E402


def add_payment(world, sender, receiver, amount, seconds_ago, label):
    when = world['now'] - seconds_ago
    world['events'].append(dict(id=f'kit-{label}-{len(world["events"])}', kind='payment',
        sender=sender, receiver=receiver, amount_paise=amount, event_at=when,
        available_at=when, provenance='authored synthetic kit event'))


def prepare(kind, seed):
    world = generate_world(seed, 'everyday')
    recipient, amount, context, expected = 1, 250_000, 'none', 'no_hold'
    if kind == 'familiar_payment':
        recipient, amount = 1, 350_000
    elif kind == 'large_family_payment':
        recipient, amount = 1, 15_000_000
    elif kind == 'wedding_gifts':
        for i in range(12): add_payment(world, 1 + i % 2, 0, 150_000 + i * 100, 7200 + i * 100, kind)
        recipient, amount = 3, 900_000
    elif kind == 'rent_increase':
        for i, days in enumerate((32, 62, 92)):
            add_payment(world, 0, 2, (2_000_000 + i * 100_000), days * 86400, kind)
        recipient, amount = 2, 3_000_000
    elif kind == 'first_time_merchant':
        recipient, amount = 72, 880_000
    elif kind == 'refund_credit_history':
        add_payment(world, 3, 0, 225_000, 3600, kind)
        recipient, amount = 1, 120_000
    elif kind == 'split_10':
        recipient, amount, expected = 4, 250_000, 'interrupt'
        for i in range(9): add_payment(world, 0, recipient, 250_000, 1800 - i * 30, kind)
    elif kind == 'fresh_mule':
        recipient, amount, expected = 4, 1_200_000, 'no_hold'
        world['events'] = [e for e in world['events'] if e['kind'] != 'payment' or recipient not in (e['sender'], e['receiver'])]
    elif kind == 'spaced_probes':
        recipient, amount, expected = 4, 500_000, 'interrupt'
        for i, days in enumerate((21, 14, 7)):
            add_payment(world, 0, recipient, (100, 200, 500)[i], days * 86400, kind)
    elif kind == 'slow_drip':
        recipient, amount, expected = 4, 350_000, 'interrupt'
        for i in range(8): add_payment(world, 0, recipient, 80_000, (28 - i * 3) * 86400, kind)
    elif kind == 'warmed_mule':
        recipient, amount, expected = 4, 1_000_000, 'interrupt'
        for i in range(16):
            add_payment(world, 6 + i, recipient, 50_000 + i * 100, (20 - i) * 86400, kind)
            add_payment(world, recipient, 30 + i, 45_000 + i * 100, (19 - i) * 86400, kind)
    elif kind == 'reported_payee_only':
        recipient, amount, expected = 4, 100_000, 'no_hold'
        when = world['now'] - 86400
        world['events'].append(dict(id=f'kit-report-{seed}', kind='report', account=recipient,
            event_at=when, available_at=when, provenance='synthetic direct report'))
    elif kind == 'text_pressure_only':
        recipient, amount, context, expected = 1, 400_000, 'withdrawal', 'no_hold'
    else:
        raise ValueError(f'Unknown kit case: {kind}')
    world['events'].sort(key=lambda e: (e['event_at'], e['id']))
    return world, recipient, amount, context, expected


def run(model_dir, seed):
    model = LiveModel(model_dir / 'xgb_model.json', model_dir / 'conformal.json')
    names = ('familiar_payment', 'large_family_payment', 'wedding_gifts', 'rent_increase',
             'first_time_merchant', 'refund_credit_history', 'split_10', 'fresh_mule',
             'spaced_probes', 'slow_drip', 'warmed_mule', 'reported_payee_only')
    rows = []
    for index, kind in enumerate(names):
        for offset in range(2):
            case_seed = (seed + index * 97 + offset) % (2**32)
            world, recipient, amount, context, expected = prepare(kind, case_seed)
            features = snapshot(world, 0, recipient, amount, world['now'])
            scored = model.score(numeric(features['values']))
            payment = dict(text={
                'none': '', 'withdrawal': 'Pay 1 to release your investment withdrawal'
            }.get(context, ''), consent=context != 'none', context=context,
                amount_paise=amount, recipient=recipient)
            decision, _, _, groups = apply_policy(payment, features, scored)
            action = decision['action']
            passed = (action != 'hold') if expected == 'no_hold' else (action != 'release')
            rows.append(dict(case=kind, seed=case_seed, expected=expected, actual=action,
                pass_invariant=bool(passed), score=scored['score'], prediction_set=scored['uncertainty'],
                groups=groups, amount_paise=amount, recipient=recipient,
                features=features['values'], reasons=decision['reasons']))
    return dict(schema='maya-authored-kit-v1', run_seed=seed, model_version=model.version,
        cases=rows, summary=dict(total=len(rows), pass_count=sum(r['pass_invariant'] for r in rows),
            misses=[dict(case=r['case'], seed=r['seed'], expected=r['expected'], actual=r['actual'])
                    for r in rows if not r['pass_invariant']]),
        provenance='Synthetic generated event histories; expected labels are authored invariants, not real-world ground truth.',
        limits=['No population accuracy claim', 'Fresh payee/direct report alone should not trigger a hold',
                'A warning counts as interruption for attack cases; it is not proof of prevented loss'])


def main():
    parser = argparse.ArgumentParser(description='Run the 24-case MAYA event-history kit')
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'models/wallet')
    parser.add_argument('--seed', type=int, default=None, help='default: random run seed; provide one to reproduce')
    parser.add_argument('--out', type=Path, default=ROOT / 'reports/kit.json')
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else secrets.randbelow(2**32)
    report = run(args.model_dir, seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"MAYA authored kit: {report['summary']['pass_count']}/{report['summary']['total']} invariants passed; seed={seed}")
    for row in report['cases']:
        print(f"{'PASS' if row['pass_invariant'] else 'MISS'}  {row['case']:<24} expect={row['expected']:<9} actual={row['actual']:<7} p={row['score']:.4f} seed={row['seed']}")
    print(f"Report: {args.out}")
    return 0 if not report['summary']['misses'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
