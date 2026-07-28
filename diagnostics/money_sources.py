import os, sys
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFS = os.environ.get('CFS_XLSX', 'data/Divisia.xlsx')
from pstar_replication import _fred_series, _cfs_monthly

def S(n): return _fred_series(n)
m2=S('M2SL'); m1=S('M1SL'); dd=S('DEMDEPSL'); std=S('STDSL'); rmf=S('RMFSL'); cur=S('CURRCIR')
liq = m1 - dd - cur   # other liquid deposits (savings/MMDA) folded into M1 since May 2020
comp = pd.DataFrame({'Currency':cur,'Demand deposits':dd,'Other liquid deposits (savings/MMDA)':liq,
                     'Small time deposits':std,'Retail money funds':rmf}).dropna()
tot = comp.sum(axis=1)
print("M2 components: contribution to the last 12 months of M2 growth")
last, prev = comp.index[-1], comp.index[-1]-pd.DateOffset(months=12)
d = (comp.loc[last]-comp.loc[prev])
print(f"  M2 level {tot.loc[prev]:,.0f} -> {tot.loc[last]:,.0f}  ({100*(tot.loc[last]/tot.loc[prev]-1):.2f}% YoY)\n")
res=pd.DataFrame({'$bn change':d,'pp of M2 growth':100*d/tot.loc[prev],
                  'own growth %':100*(comp.loc[last]/comp.loc[prev]-1)})
print(res.sort_values('pp of M2 growth',ascending=False).round(2).to_string())

print("\n\nDivisia M4 breakdown (CFS): which layer is growing?")
dm2,dm4=_cfs_monthly(CFS)
raw=pd.read_excel(CFS,'Broad',header=None)
hdr=raw.iloc[1].astype(str)
def col(k):
    i=[j for j,h in enumerate(hdr) if h.strip().lower().startswith(k)][0]
    d=raw.iloc[2:,[0,i]].copy(); d.columns=['date','v']; d['date']=pd.to_datetime(d['date'],errors='coerce')
    return d.dropna().set_index('date')['v'].astype(float)
dm4_=col('divisia m4- level'); dm3=col('divisia m3 level')
b=pd.DataFrame({'Divisia M2 (households)':dm2,'Divisia M3 (+ instl MMF, large time, repo)':dm3,
                'Divisia M4- (+ commercial paper)':dm4_,'Divisia M4 (+ Treasury bills)':dm4}).dropna()
print("\nYoY growth %, last 5 months:")
print((100*(b/b.shift(12)-1)).tail(5).round(2).to_string())
print("\n6m annualized %, last 3 months:")
print((100*((b/b.shift(6))**2-1)).tail(3).round(2).to_string())

print("\n\nBANK CREDIT (money creation via lending), YoY % and 6m annualized %")
bk=pd.DataFrame({'Total bank credit':S('TOTBKCR'),'C&I (business) loans':S('BUSLOANS'),
                 'Real estate loans':S('REALLN'),'Consumer loans':S('CONSUMER')})
bk=bk.resample('MS').last().dropna()
print("\nYoY %:"); print((100*(bk/bk.shift(12)-1)).tail(4).round(2).to_string())
print("\n6m ann %:"); print((100*((bk/bk.shift(6))**2-1)).tail(4).round(2).to_string())

print("\n\nFED BALANCE SHEET (weekly, $mn)")
w=pd.DataFrame({'Total assets':S('WALCL'),'Reserve balances':S('WRESBAL')}).dropna()
print(w.tail(3).round(0).to_string())
print(f"\nWALCL 12m change: {100*(w['Total assets'].iloc[-1]/w['Total assets'].asof(w.index[-1]-pd.DateOffset(months=12))-1):.2f}%")
print(f"Reserves 12m change: {100*(w['Reserve balances'].iloc[-1]/w['Reserve balances'].asof(w.index[-1]-pd.DateOffset(months=12))-1):.2f}%")
