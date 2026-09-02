"""
Степень урбанизации общин Сербии по GHS-SMOD + GHS-POP,
и проверка: не она ли объясняет разрыв «учёба минус труд».

ГЛАВНЫЙ УРОК ЭТОГО СКРИПТА — про взвешивание.

Сначала я считала долю ПЛОЩАДИ общины в городских классах SMOD.
Получалось, что самодостаточность по труду падает с урбанизацией
(корреляция −0,28), и это красиво ложилось на гипотезу о дефекте
сербского определения дневного мигранта.

Вывод был ложный. Городские классы занимают ничтожную долю площади:
у половины общин городских пикселей по площади не было вовсе, медиана
доли — 0,006. То есть мера почти всюду ноль, и корреляция считалась
по шуму.

Правильная мера — доля НАСЕЛЕНИЯ в городских классах, это и есть
определение degree of urbanisation. Медиана становится 0,44, нулей 56
из 168. И корреляция с самодостаточностью схлопывается до −0,02.

Итог: дефект определения НЕ размазан градиентом по всем общинам,
он заперт в восьми однопунктовых. Это лучше для доклада, чем градиент:
артефакт локализован и его видно поимённо.

ОГРАНИЧЕНИЕ: растры взяты в редакции E2030 — это ПРОГНОЗ на 2030 год,
а перепись 2022-я. Суммарное население GHSL по 168 общинам 6,87 млн
против примерно 6,65 млн по переписи, расхождение +3 %. Для нулевого
результата это некритично, но для публикации нужна редакция E2020.

Запуск: python talk2/ghsl_urbanisation.py
"""
import sys, numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.windows import from_bounds
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
sys.path.insert(0,'/sessions/practical-upbeat-brown/mnt/outputs/foss4g2026/src')
from adapters.serbia_census import read_daily_migration, add_self_containment
from adapters.serbia_geo import load_municipalities, join_census

URBAN={30,23,22,21}; CITY={30}
U='/sessions/practical-upbeat-brown/mnt/uploads/'
w=add_self_containment(read_daily_migration(U+'dnevne_migracije_aktivnog_stanovnistva_koje_obavlja_zanimanje_po_polu_i_tipu_naselja.xlsx'))
s=add_self_containment(read_daily_migration(U+'dnevne_migracije_učenika_i_studenata_po_polu_i_tipu_naselja.xlsx'))
g=load_municipalities('/tmp/rs/Op_tina.shp')
jw=join_census(g,w); js=join_census(g,s)
jw['rbsc_s']=js.set_index('matched').rbsc.reindex(jw.matched).values
jw['gap']=jw.rbsc_s-jw.rbsc
jw=jw.to_crs('ESRI:54009').reset_index(drop=True)

POP='/tmp/ghsl/GHS_POP_E2030_GLOBE_R2023A_54009_100_V1_0_R4_C20.tif'
SM ='/tmp/ghsl/GHS_SMOD_E2030_GLOBE_R2023A_54009_1000_V2_0.tif'
with rasterio.open(POP) as rp:
    b=jw.total_bounds
    # окно POP пересекаем с самим растром: тайл обрезает юг Сербии
    x0,y0=max(b[0]-500,rp.bounds.left), max(b[1]-500,rp.bounds.bottom)
    x1,y1=min(b[2]+500,rp.bounds.right), min(b[3]+500,rp.bounds.top)
    win=from_bounds(x0,y0,x1,y1,rp.transform)
    pop=rp.read(1,window=win).astype('float32')
    trp=rp.window_transform(win)
pop[pop<0]=0
print(f"POP окно {pop.shape}, суммарное население в окне {pop.sum():,.0f}")

# SMOD 1 км -> сетка POP 100 м, ближайшим соседом (классы, не значения)
with rasterio.open(SM) as rs:
    smod_on_pop=np.zeros(pop.shape,dtype='int16')
    reproject(source=rasterio.band(rs,1),destination=smod_on_pop,
              dst_transform=trp,dst_crs='ESRI:54009',resampling=Resampling.nearest)

zones=rasterize([(geom,i+1) for i,geom in enumerate(jw.geometry)],
                out_shape=pop.shape,transform=trp,fill=0,dtype='int32')
is_urb=np.isin(smod_on_pop,list(URBAN)); is_city=np.isin(smod_on_pop,list(CITY))
n=len(jw)+1
tot=np.bincount(zones.ravel(),weights=pop.ravel(),minlength=n)
urb=np.bincount(zones.ravel(),weights=(pop*is_urb).ravel(),minlength=n)
cit=np.bincount(zones.ravel(),weights=(pop*is_city).ravel(),minlength=n)
px =np.bincount(zones.ravel(),minlength=n)

jw['pop_ghsl']=tot[1:]; jw['pop_urban']=urb[1:]; jw['pop_city']=cit[1:]; jw['px']=px[1:]
jw['deg_urb']=(jw.pop_urban/jw.pop_ghsl).where(jw.pop_ghsl>0)
jw['deg_city']=(jw.pop_city/jw.pop_ghsl).where(jw.pop_ghsl>0)

# кого обрезал тайл: полигон выходит южнее нижней границы растра
with rasterio.open(POP) as rp: ybot=rp.bounds.bottom
jw['clipped']=jw.geometry.bounds.miny < ybot
print(f"общин, задетых обрезкой тайла: {jw.clipped.sum()}  -> {list(jw[jw.clipped].name)}")
jw.drop(columns='geometry').to_csv('/tmp/rs_ghsl_pop.csv',index=False)

d=jw[(~jw.single_settlement.astype(bool)) & (~jw.clipped) & (jw.pop_ghsl>0)]
print(f"\nв анализе {len(d)} общин")
print(f"степень урбанизации: медиана {d.deg_urb.median():.2f}, "
      f"общин с нулём {int((d.deg_urb==0).sum())}")
print("\n=== КОРРЕЛЯЦИИ (взвешивание по населению) ===")
for c,lab in [('deg_urb','доля населения в городских классах'),
              ('deg_city','доля населения в городских центрах')]:
    print(f"  {lab:36s} RBSC труд {d.rbsc.corr(d[c]):+.2f}  "
          f"RBSC учёба {d.rbsc_s.corr(d[c]):+.2f}  разрыв {d.gap.corr(d[c]):+.2f}")
q=pd.qcut(d.deg_urb.rank(method='first'),4,labels=['сельские','ниже сред.','выше сред.','городские'])
print(f"\n{'квартиль':22s} {'n':>4s} {'степ.урб':>9s} {'RBSC труд':>10s} {'RBSC учёба':>11s} {'разрыв':>8s}")
for lab,gr in d.groupby(q,observed=True):
    print(f"  {str(lab):20s} {len(gr):4d} {gr.deg_urb.mean():9.2f} {gr.rbsc.mean():10.3f} {gr.rbsc_s.mean():11.3f} {gr.gap.mean():+8.3f}")
def partial(x,y,z):
    rx=x-np.poly1d(np.polyfit(z,x,1))(z); ry=y-np.poly1d(np.polyfit(z,y,1))(z)
    return np.corrcoef(rx,ry)[0,1]
lz=np.log(d.total.values)
print(f"\nразрыв ~ урбанизация:                      {d.gap.corr(d.deg_urb):+.2f}")
print(f"  при контроле размера общины:             {partial(d.deg_urb.values,d.gap.values,lz):+.2f}")
print(f"RBSC труд ~ урбанизация:                   {d.rbsc.corr(d.deg_urb):+.2f}")
print(f"  при контроле размера общины:             {partial(d.deg_urb.values,d.rbsc.values,lz):+.2f}")
