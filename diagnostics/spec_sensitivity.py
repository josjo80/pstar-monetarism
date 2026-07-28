import os, sys
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get('CFS_XLSX', 'data/Divisia.xlsx')
from pstar_replication import fetch_fred, load_cfs, price_gap, _fred_series

base = fetch_fred().join(load_cfs(CFS), how='left')
base = base.dropna(subset=['rgdp','p_gdp','M2'])
base['p_gdp_ct'] = _fred_series('GDPCTPI')/100.0
base['npce_direct'] = _fred_series('PCEC')

paper = {'M2/GDP':-0.25,'DM2/GDP':0.41,'DM4/GDP':0.79,'M2/PCE':-0.36}

def gaps(df, pcol='p_gdp', rcol='rgdp'):
    out={}
    for m in ['M2','DM2','DM4']:
        g = price_gap(df,m,rcol,pcol)['gap']
        out[m]=g.loc['2025-01-01':'2026-01-01'].round(2).tolist()
    return out

for start in ['1959-01-01','1967-01-01']:
    d = base.loc[start:'2026-03-31']
    print(f"\n--- filter start {start}  (GDP deflator = GDP/GDPC1) ---")
    for k,v in gaps(d).items(): print(f"  {k:4s} 2025Q1..2026Q1: {v}")

d = base.loc['1967-01-01':'2026-03-31']
print("\n--- filter start 1967, GDP price = GDPCTPI (chain-type) ---")
for k,v in gaps(d, pcol='p_gdp_ct').items(): print(f"  {k:4s} 2025Q1..2026Q1: {v}")

# PCE: nominal from PCEC directly instead of PCECC96*PCECTPI
d2 = d.copy(); d2['p_pce_impl'] = d2['npce_direct']/d2['rpce']
print("\n--- PCE spec: implicit PCE deflator (PCEC/PCECC96) vs chain index ---")
for m in ['M2','DM2','DM4']:
    a = price_gap(d,m,'rpce','p_pce')['gap'].loc['2026-01-01']
    b = price_gap(d2,m,'rpce','p_pce_impl')['gap'].loc['2026-01-01']
    print(f"  {m:4s} 2026Q1  chain={a:6.2f}  implicit={b:6.2f}")
print("\npaper 2026Q1:", paper)
