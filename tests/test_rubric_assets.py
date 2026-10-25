from dataclasses import replace

import numpy as np

from journey_generator import (Config, Ledger, add_normal, attach_cohort_tags, build_accounts,
    build_mule_network, build_transactions, generate_campaigns, generate_users, make_rng)
from risk_common import FEATURE_COLUMNS


def test_synthetic_cohorts_and_lookalikes_stay_outside_model_features():
    cfg=replace(Config(seed=19,write_csv=False),n_users=600,n_days=30,n_employers=20,
        n_landlords=40,n_merchants=60,n_aggregators=4,n_exits=2,mule_rate=.01,victim_rate=.03)
    accounts=build_accounts(cfg,make_rng(cfg.seed,'accounts'))
    users=generate_users(cfg,accounts,make_rng(cfg.seed,'users'))
    mule_rng=make_rng(cfg.seed,'mules')
    mule_count=max(cfg.n_aggregators+2,int(round(cfg.mule_rate*cfg.n_users)))
    mule_ids=mule_rng.permutation(cfg.n_users)[:mule_count]
    network=build_mule_network(cfg,accounts,mule_ids,mule_rng)
    ledger=Ledger();add_normal(cfg,accounts,users,make_rng(cfg.seed,'normal'),ledger)
    campaigns=generate_campaigns(cfg,accounts,users,network,make_rng(cfg.seed,'campaigns'),ledger)
    tx=build_transactions(cfg,ledger,accounts,len(campaigns))
    tx=attach_cohort_tags(tx,campaigns,users,cfg.n_users)
    assert {'cohort_age_band','cohort_language','cohort_phone_type','cohort_tenure_days','lookalike_type'} <= set(tx.columns)
    assert tx['cohort_age_band'].ne('not_applicable').any()
    assert {'wedding_festival','first_time_merchant','genuine_refund_credit'} <= set(tx['lookalike_type'])
    later_wedding = tx['day'].ge(int(cfg.n_days * cfg.split_fracs[0])) & tx['category'].astype(str).eq('wedding')
    assert later_wedding.any()
    assert 'cohort_age_band' not in FEATURE_COLUMNS and 'lookalike_type' not in FEATURE_COLUMNS
