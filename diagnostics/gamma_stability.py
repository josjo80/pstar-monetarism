import os, sys
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get('CFS_XLSX', 'data/Divisia.xlsx')
from pstar_replication import fetch_fred, load_cfs, price_gap, pstar_regression, OLSResult

df = fetch_fred().join(load_cfs(CFS),how='left').dropna(subset=['rgdp','p_gdp','M2'])
df = df.loc['1967-01-01':'2026-03-31']
g = price_gap(df,'DM2','rgdp','p_gdp')['gap']

print("=== Subsample stability of gamma (Divisia M2 / GDP) ===")
for a,b,nm in [('1967-01-01','2026-03-31','full sample'),
               ('1967-01-01','1983-12-31','1967-1983 monetarist era'),
               ('1984-01-01','2007-12-31','1984-2007 Great Moderation'),
               ('1990-01-01','2019-12-31','1990-2019 (pre-COVID)'),
               ('2008-01-01','2026-03-31','2008-2026 ZIRP+COVID'),
               ('1967-01-01','2019-12-31','excl. COVID onward')]:
    r,d = pstar_regression(df,'p_gdp',g,start=a,end=b)
    print(f"  {nm:28s} gamma={r.params['gap_l1']:+.3f}  t={r.tvalues['gap_l1']:5.2f}  "
          f"R2={r.rsquared:.3f}  n={int(r.nobs)}")

print("\n=== Rolling 15-year (60q) gamma ===")
r_all,d_all = pstar_regression(df,'p_gdp',g)
X = d_all[[f'dpi_l{i}' for i in range(1,5)]+['gap_l1']].copy(); X.insert(0,'const',1.0)
y = d_all['dpi']
roll=[]
for i in range(60,len(y)+1):
    rr = OLSResult(y.iloc[i-60:i], X.iloc[i-60:i])
    roll.append((y.index[i-1], rr.params['gap_l1'], rr.tvalues['gap_l1']))
roll = pd.DataFrame(roll, columns=['date','gamma','t']).set_index('date')
print(roll.resample('5AS').first().round(3).to_string())
print(f"\n  min {roll['gamma'].min():+.3f} ({roll['gamma'].idxmin().date()})   "
      f"max {roll['gamma'].max():+.3f} ({roll['gamma'].idxmax().date()})")
print(f"  share of rolling windows with t > 2: {100*(roll['t']>2).mean():.0f}%")

print("\n=== Pseudo out-of-sample: does the gap beat a plain AR(4)? ===")
print("    expanding window from 1990Q1, 1-quarter-ahead forecast of change in inflation")
e_full, e_ar = [], []
for i in range(len(y)):
    if y.index[i] < pd.Timestamp('1990-01-01'): continue
    Xtr, ytr = X.iloc[:i], y.iloc[:i]
    m_full = OLSResult(ytr, Xtr)
    m_ar   = OLSResult(ytr, Xtr.drop(columns=['gap_l1']))
    e_full.append(y.iloc[i] - float(m_full.params @ X.iloc[i]))
    e_ar.append(y.iloc[i] - float(m_ar.params @ X.iloc[i].drop('gap_l1')))
e_full, e_ar = np.array(e_full), np.array(e_ar)
r1, r2 = np.sqrt((e_full**2).mean()), np.sqrt((e_ar**2).mean())
d_dm = e_full**2 - e_ar**2
dm = d_dm.mean()/ (d_dm.std(ddof=1)/np.sqrt(len(d_dm)))
print(f"    RMSE with gap    {r1:.4f}")
print(f"    RMSE AR(4) only  {r2:.4f}   -> gap improves RMSE by {100*(1-r1/r2):+.2f}%")
print(f"    Diebold-Mariano t = {dm:+.2f}  (negative = gap helps; |t|>2 significant)  n={len(e_full)}")
