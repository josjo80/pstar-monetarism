import os, sys
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get('CFS_XLSX', 'data/Divisia.xlsx')
from pstar_replication import fetch_fred, load_cfs, price_gap, pstar_regression

df = fetch_fred().join(load_cfs(CFS),how='left').dropna(subset=['rgdp','p_gdp','M2'])
df = df.loc['1967-01-01':'2026-03-31']

for pcol,mcol,tag in [('p_pce','DM2','PCE / Divisia M2'),('p_gdp','DM2','GDP / Divisia M2')]:
    g = price_gap(df,mcol,'rpce' if tag.startswith('PCE') else 'rgdp',pcol)['gap']
    res,d = pstar_regression(df,pcol,g)
    pi = 400*np.log(df[pcol]).diff()
    b = res.params
    fit = (b['const'] + sum(b[f'dpi_l{i}']*d[f'dpi_l{i}'] for i in range(1,5))
           + b['gap_l1']*d['gap_l1'])
    contrib = b['gap_l1']*d['gap_l1']          # the money part alone
    out = pd.DataFrame({
        'inflation': pi,
        'actual dInfl': d['dpi'],
        'model predicts dInfl': fit,
        'of which money(gap)': contrib,
    }).loc['2024-07-01':]
    print(f"\n===== {tag} =====  (all annualized pp)")
    print(out.round(2).to_string())
