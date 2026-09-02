import sys, numpy as np, pandas as pd
sys.path.insert(0,'/sessions/practical-upbeat-brown/mnt/outputs/foss4g2026/src')
import fua.delimit as D
from fua.delimit import prepare_od, unit_stats, find_cores, fua_summary

d=pd.read_csv('/tmp/uk11/wu01ew_msoa.csv')
d.columns=['origin','dest','flow','m','f']
print(f"сырых пар {len(d):,}  поездок {d.flow.sum():,.0f}")
print(f"кодов назначения не-MSOA: {sorted(set(x for x in d.dest.unique() if not str(x).startswith(('E02','W02'))))[:8]}")
od=prepare_od(d,'origin','dest','flow')
keep=set(od.origin)&set(od.dest)
keep={k for k in keep if str(k)[:3] in ('E02','W02')}
od=od[od.origin.isin(keep)&od.dest.isin(keep)]
print(f"после чистки: {len(od):,} пар, {od.origin.nunique():,} MSOA, {od.flow.sum():,.0f} поездок")
od.to_parquet('/tmp/uk11_od.parquet')
st=unit_stats(od); st.to_parquet('/tmp/uk11_stats.parquet')
print(f"базовый SC MSOA 2011: медиана {st.self_containment.median():.3f} взвеш {st.internal.sum()/st.out_total.sum():.3f}")

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
nm=null_sc(sz, units.get_indexer(a.unit.values))
print(f"\n=== 2011, те же параметры что и в 2021 (q=0.95, merge=0.10, commute=0.15) ===")
print(f"  ядер {len(cores)}   ареалов {len(sz)}   присвоено {len(a)}/{len(asg)}")
print(f"  SC {sc:.3f}   нуль {nm:.3f}   избыток {sc-nm:+.3f}")
print(f"  размеры: медиана {np.median(sz):.0f}  макс {sz.max()}  мин {sz.min()}")
asg.to_csv('/tmp/uk11_assign.csv',index=False); sm.to_csv('/tmp/uk11_summary.csv')
