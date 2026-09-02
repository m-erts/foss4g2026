import sys, numpy as np, pandas as pd
sys.path.insert(0,'/sessions/practical-upbeat-brown/mnt/outputs/foss4g2026/src')
import fua.delimit as D
from fua.delimit import prepare_od, unit_stats, find_cores, fua_summary
parts=[]
for c in pd.read_csv('/tmp/uk/ODWP01EW_MSOA.csv',chunksize=2_000_000):
    c.columns=['o','olab','d','dlab','pw','pwlab','n']
    # ТОЛЬКО категория 3: работает в Британии и НЕ из дома.
    # Категория 1 (12,59 млн) — надомники, им место работы проставлено
    # равным месту жительства, и они целиком уходят в числитель.
    parts.append(c[(c.pw==3)&(c.n>0)][['o','d','n']])
d=pd.concat(parts,ignore_index=True)
od=prepare_od(d,'o','d','n')
keep=set(od.origin)&set(od.dest); keep={k for k in keep if str(k)[:3] in ('E02','W02')}
od=od[od.origin.isin(keep)&od.dest.isin(keep)]
print(f"2021, только категория 3: {len(od):,} пар, {od.origin.nunique():,} MSOA, {od.flow.sum():,.0f} поездок")
od.to_parquet('/tmp/uk21_od_fixed.parquet')
st=unit_stats(od); st.to_parquet('/tmp/uk21_stats_fixed.parquet')
print(f"базовый SC: медиана {st.self_containment.median():.3f}  взвеш {st.internal.sum()/st.out_total.sum():.3f}")
units=pd.Index(sorted(set(od.origin)|set(od.dest)))
oi=units.get_indexer(od.origin.values); di=units.get_indexer(od.dest.values)
f=od.flow.values.astype(float); n=len(units); rng=np.random.default_rng(0)
def null_sc(sizes, idx, it=60):
    r=np.empty(it); lab=np.full(n,-1,np.int32); s=np.concatenate([[0],np.cumsum(sizes)])
    for k in range(it):
        p=rng.permutation(idx); lab[:]=-1
        for gi in range(len(sizes)): lab[p[s[gi]:s[gi+1]]]=gi
        ol=lab[oi]; dl=lab[di]; m=ol>=0
        r[k]=f[m&(ol==dl)].sum()/f[m].sum()
    return r.mean()
_o=D.merge_cores
cores=find_cores(st,inflow_quantile=0.95)
D.merge_cores=lambda o_,c_,merge_thr=0.10: _o(o_,c_,merge_thr=0.10)
asg=D.build_fua(od,cores,commute_thr=0.15); D.merge_cores=_o
a=asg.dropna(subset=['fua']); sz=np.array(sorted(a.groupby('fua').size(),reverse=True))
sm=fua_summary(od,asg); sc=sm.internal.sum()/sm.departures.sum()
nm=null_sc(sz,units.get_indexer(a.unit.values))
print(f"\nядер {len(cores)}  ареалов {len(sz)}  присвоено {len(a)}/{len(asg)}")
print(f"SC {sc:.3f}  нуль {nm:.3f}  избыток {sc-nm:+.3f}")
print(f"размеры: медиана {np.median(sz):.0f} макс {sz.max()} мин {sz.min()}")
asg.to_csv('/tmp/uk21_assign_fixed.csv',index=False)
