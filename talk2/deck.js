const pptxgen = require("pptxgenjs");
const A = "/sessions/practical-upbeat-brown/mnt/outputs/deck2_assets/";
const BG="1A1033", PANEL="241A44", CY="4FE3E0", VI="B57BFF", CO="FF6B6B",
      GR="3DD68C", YE="FFD166", TXT="FFFFFF", MUT="9C8FB8", DIM="6A5D85";
const p = new pptxgen();
p.layout = "LAYOUT_WIDE";                    // 13.33 x 7.5
p.defineSlideMaster({ title:"D", background:{ color:BG } });

const W=13.33;
function S(){ return p.addSlide({ masterName:"D" }); }
function T(s,t,o={}){ s.addText(t,{ fontFace:"Arial", color:TXT, isTextBox:true, margin:0, ...o }); }
function title(s,t,sub){ T(s,t,{x:0.55,y:0.32,w:W-1.1,h:0.75,fontSize:30,bold:true});
  if(sub) T(s,sub,{x:0.55,y:1.02,w:W-1.1,h:0.4,fontSize:14,color:MUT}); }
function foot(s,t){ T(s,t,{x:0.55,y:7.02,w:W-1.1,h:0.35,fontSize:10,color:DIM}); }
function statf(s,x,y,w,fs,big,label,c=CY){
  s.addShape("roundRect",{x,y,w,h:1.9,fill:{color:PANEL},line:{color:"3A2D5A",width:1},rectRadius:0.08});
  T(s,big,{x:x+0.25,y:y+0.18,w:w-0.5,h:0.95,fontSize:fs,bold:true,color:c});
  T(s,label,{x:x+0.25,y:y+1.12,w:w-0.5,h:0.68,fontSize:12.5,color:MUT});
}
function stat(s,x,y,w,big,label,c=CY){
  s.addShape("roundRect",{x,y,w,h:1.9,fill:{color:PANEL},line:{color:"3A2D5A",width:1},rectRadius:0.08});
  T(s,big,{x:x+0.25,y:y+0.18,w:w-0.5,h:0.95,fontSize:40,bold:true,color:c});
  T(s,label,{x:x+0.25,y:y+1.12,w:w-0.5,h:0.68,fontSize:12.5,color:MUT});
}

// ---------- 1 · title
let s=S(); s.addNotes("Hook: two years ago this analysis needed a paid operator feed. Today: how far do we get on fully open data, and where exactly is the wall.");
T(s,"Eurostat vs OSM vs Census",{x:0.9,y:2.05,w:11.5,h:1.0,fontSize:48,bold:true});
T(s,"Choosing Open Mobility Data for Urban Function Maps",{x:0.9,y:3.05,w:11.5,h:0.6,fontSize:24,color:CY});
T(s,"What survives when the paid mobile-operator feed is gone — and where exactly the boundary runs",
  {x:0.9,y:3.85,w:11.0,h:0.6,fontSize:15,color:MUT,italic:true});
T(s,"Marija Ercegovac · Senior Geospatial Analyst, Rockup · URBAN_MASH",{x:0.9,y:5.7,w:10,h:0.4,fontSize:14});
T(s,"FOSS4G 2026 Hiroshima · Sep 3, 14:00 · Room 2 · CC BY 4.0",{x:0.9,y:6.15,w:10,h:0.4,fontSize:12,color:DIM});

// ---------- 2 · the three sources in 2026
s=S(); s.addNotes("Reality check vs spring abstract. Eurostat: Multi-MNO standard AND open reference pipeline shipped 2025; EU dataset not yet — but Spain has published hourly MNO OD weekly since 2020. Japan flagship is app-GPS (Agoop), not MNO. Punchline: Europe wrote the standard, Spain shipped the data, Japan shipped the clock I could join to a census — and none of the three is what its label says."); title(s,"Three open sources. The 2026 reality check.","What the abstract promised in spring — and what each source turned out to be when I pulled it");
const cards=[
 ["Eurostat MNO statistics","A standard — and one country shipping.","Multi-MNO standard + open reference pipeline (github.com/eurostat/multimno) shipped 2025; EU-wide data not yet. Spain publishes hourly MNO OD weekly since 2020 (MITMA). Japan's flagship is app-GPS, not MNO.",VI],
 ["OSM public GPS traces","A behaviour sample of contributors.","Three city windows, each capped at 200k points by API paging — yet only 2.4–10k unique minutes each; Belgrade median trace year: 2014.",CY],
 ["Census commuting flows","The anchor — with traps.","Full OD pairs: UK, France, Germany, Japan's census, NL register. Nested rings only: Serbia — and Japan's MLIT product. Free, total-population, no clock.",GR]];
cards.forEach((c,i)=>{ const x=0.55+i*4.18;
 s.addShape("roundRect",{x,y:1.7,w:3.95,h:4.6,fill:{color:PANEL},line:{color:"3A2D5A",width:1},rectRadius:0.08});
 T(s,c[0],{x:x+0.3,y:2.0,w:3.35,h:0.5,fontSize:17,bold:true,color:c[3]});
 T(s,c[1],{x:x+0.3,y:2.6,w:3.35,h:0.8,fontSize:15,bold:true});
 T(s,c[2],{x:x+0.3,y:3.5,w:3.35,h:2.6,fontSize:12.5,color:MUT,lineSpacing:17});
});
T(s,"Renegotiated since spring: Urban Atlas → GHS-SMOD · intraday → day/night · HDBSCAN → declared thresholds · UMAP dropped",{x:0.55,y:6.45,w:12.2,h:0.35,fontSize:11,color:MUT,italic:true,isTextBox:true,margin:0});
foot(s,"KS-FT-23-001 · github.com/eurostat/multimno · MITMA via spanishoddata (CRAN) · api.openstreetmap.org/api/0.6/trackpoints · nomisweb.co.uk");


// ---------- 2b · OSM vs Overture
s=S(); s.addNotes("Two open communities, same streets. The decisive rank test is underpowered: n=11 shared cells, rho +0.81 vs MLIT presence, +0.61 vs Overture — indistinguishable. The evidence for contributor bias is sample structure: 51% of points in ONE cell, 2,395 unique minutes in 200k points, Belgrade median year 2014. A bright line is one logger. Nielsen 90-9-1.");
title(s,"Same streets, two communities","Overture Places density (purple) vs OSM public GPS traces (cyan) · H3 res 8");
s.addImage({path:A+"osm_overture.png",x:1.15,y:1.5,w:11.0,h:5.35});
foot(s,"© OpenStreetMap contributors (ODbL) · Overture Maps Foundation (CDLA-P-2.0) · 200k = 40-page API cap · decisive rank test vs MLIT presence is underpowered at n=11 shared cells (+0.81 vs +0.61)");

// ---------- 3 · three dimensions
s=S(); s.addNotes("The core claim of the talk. Read the table slowly. ISO 19157 passes on all of these — the defect metadata cannot express: right data, different question."); title(s,"Every source sacrifices one of three dimensions","and the sacrifice is silent — the metadata look perfect");
const rows=[[{text:"source",options:{bold:true,color:TXT}},{text:"origin→destination pairs",options:{bold:true,color:TXT}},{text:"trip purpose",options:{bold:true,color:TXT}},{text:"time of day / week",options:{bold:true,color:TXT}}],
 [{text:"UK · FR · DE · JP census OD"},{text:"full matrix",options:{color:GR}},{text:"work only",options:{color:YE}},{text:"none",options:{color:CO}}],
 [{text:"Serbia census 2022"},{text:"4 nested admin rings",options:{color:YE}},{text:"work + education (merged)",options:{color:YE}},{text:"none",options:{color:CO}}],
 [{text:"Japan MLIT app-GPS (Agoop)"},{text:"4 nested admin rings",options:{color:YE}},{text:"none — all presence",options:{color:CO}},{text:"month × day/night × wd/hol",options:{color:GR}}],
 [{text:"NL ODiN survey"},{text:"residence only",options:{color:CO}},{text:"full purpose set",options:{color:GR}},{text:"yes",options:{color:GR}}],
 [{text:"NL register OD (CBS)"},{text:"pairs: 40 regions to 2014 → municipalities since 2021",options:{color:YE}},{text:"work only",options:{color:YE}},{text:"none",options:{color:CO}}]];
s.addTable(rows,{x:0.55,y:1.85,w:12.2,colW:[3.0,3.3,3.1,2.8],fontFace:"Arial",fontSize:13,color:MUT,
  fill:{color:PANEL},border:{type:"solid",color:"3A2D5A",pt:0.75},rowH:0.56,valign:"middle"});
T(s,"Five computable ISO 19157 elements pass on every file here. The sixth — usability, fitness for a stated purpose — is the one nobody computes. This talk is element six.",
  {x:0.55,y:5.7,w:12.2,h:0.5,fontSize:14,color:CY,italic:true,isTextBox:true,margin:0});
T(s,"Spain and Japan publish the clock. Nobody publishes all three dimensions at once.",{x:0.55,y:6.35,w:12.2,h:0.45,fontSize:16,bold:true,color:CY,isTextBox:true,margin:0});

// ---------- 4 · UK map
s=S(); s.addNotes("UK: the only case with true pairs. 15.1M commuters, 7264 zones. This is what delimitation needs."); title(s,"Where pairs exist, functional areas fall out","England & Wales, census 2021 home→work matrix · 7,264 MSOA · 15.1 M commuters with a fixed workplace");
s.addImage({path:A+"uk_areas.png",x:1.7,y:1.55,w:9.9,h:5.35});
foot(s,"my own 2-rule delimitation, NOT the TTWA algorithm · cores at q95 external inflow, iterative 15 % attachment · coral = fragments cut off from their area");

// ---------- 5 · trap 1: WFH
s=S(); s.addNotes("Trap 1 killed my own first comparison. ONS user guide, verbatim: residents with no fixed place or working from home have been counted at their usual residence as place of work. Census day was 21 March 2021 — mid-lockdown, ONS itself says keep using 2011 TTWAs. And the remaining 15.1M are not a random subsample — selection towards key workers. The code list plus the date together flip the story."); title(s,"Trap 1 · one code category flips the story","Census 2021 place-of-work coding, England & Wales");
stat(s,0.55,1.8,3.95,"12.6 M","coded “mainly at home / no fixed place” on census day — 21 March 2021, mid-lockdown. Their workplace equals their residence: all land on the diagonal.",CO);
statf(s,4.7,1.8,3.95,32,"0.103 → 0.506","the naive 2011→2021 self-containment jump if you keep them. “Britain quintupled its localism.” It did not.",YE);
statf(s,8.85,1.8,3.95,32,"0.103 → 0.093","the real change once category 1 is excluded. The geometry barely moved — what exploded is who had a fixed workplace on census day.",GR);
T(s,"Fixed-workplace commuting: 21.6 M → 15.1 M journeys (−30 %).  Home / no-fixed-base: 4.9 M (19 %) → 12.6 M (45 %).",
 {x:0.55,y:4.3,w:12.2,h:0.5,fontSize:15,bold:true,isTextBox:true,margin:0});
T(s,"One glance at the code list catches it. Nothing in the file format warns you.",
 {x:0.55,y:4.9,w:12.2,h:0.4,fontSize:13,color:MUT,isTextBox:true,margin:0});
foot(s,"ODWP01EW category 1 vs 3 · 2011: WU01EW codes OD0000001/3 · both matrices cleaned the same way before any comparison");

// ---------- 6 · trap 2: null model
s=S(); s.addNotes("Trap 2 killed my second result. All three pairs computed identically, home-workers excluded. Districts: random gets 0.657 of 0.947 — bigger boxes catch more trips by chance. MSOA: random floor 0.130, excess +0.57 — real. Line to land: the number that looks worse is the correct one. MAUP, Openshaw 1984."); title(s,"Trap 2 · aggregation flatters you for free","the null model: same units, same area sizes, assignment random — 60 runs");
s.addChart(p.ChartType.bar,[
 {name:"Delimited areas",labels:["Districts 2021","MSOA 2011","MSOA 2021"],values:[0.947,0.740,0.695]},
 {name:"Random same-size areas",labels:["Districts 2021","MSOA 2011","MSOA 2021"],values:[0.657,0.157,0.130]}],
 {x:0.7,y:1.7,w:6.6,h:4.6,barDir:"col",chartColors:[CY,CO],
  showValue:true,dataLabelPosition:"outEnd",dataLabelColor:TXT,dataLabelFontSize:12,dataLabelFormatCode:"0.000",valAxisLabelFormatCode:"0.0",
  valAxisMaxVal:1,valAxisMinVal:0,catAxisLabelColor:MUT,valAxisLabelColor:MUT,
  valGridLine:{color:"3A2D5A",size:0.5},catGridLine:{style:"none"},
  showLegend:true,legendPos:"b",legendColor:MUT,showTitle:false,
  showValAxisTitle:true,valAxisTitle:"self-containment",valAxisTitleColor:MUT,valAxisTitleFontSize:11});
T(s,"At district level random already scores 0.657 of 0.947 — bigger boxes catch more trips by pure chance. At MSOA the random floor collapses to 0.130.",
 {x:7.6,y:1.9,w:5.2,h:1.7,fontSize:14,color:MUT,lineSpacing:19,isTextBox:true,margin:0});
T(s,"At MSOA the excess over random is +0.58. The number that looks worse is the correct one.",
 {x:7.6,y:3.7,w:5.2,h:1.2,fontSize:15,bold:true,color:CY,lineSpacing:20,isTextBox:true,margin:0});
T(s,"Run the shuffle before you believe your own map.",{x:7.6,y:5.1,w:5.2,h:0.6,fontSize:14,italic:true,isTextBox:true,margin:0});
foot(s,"self-containment = trips staying inside their area / all trips · random keeps the exact size distribution · sd over 200 runs ≤ 0.007 (thinner than these bars) · MAUP: Openshaw 1984");

// ---------- 7 · trap 3: criterion vs algorithm
s=S(); s.addNotes("Trap 3 refined: the criterion is open, the PRODUCTION CODE is not. A published description is not a runnable artefact — my faithful rule + naive merge order gives 67 areas, London eats 6.1M. If asked about Coombes-Bond being published: yes, and Istat ships LabourMarketAreas on CRAN for the EU variant — running it against the ONS map is my next step, not a refutation."); title(s,"Trap 3 · the criterion is open — the production code is not","reproducing official Travel-to-Work Areas from the same open matrix");
stat(s,0.55,1.8,3.95,"167","official TTWAs in England & Wales (2011). The validity rule is published: ≥3,500 workers, self-containment on a sliding scale.",GR);
stat(s,4.7,1.8,3.95,"235","areas my delimitation finds before the size rule — close, looks great, means little: several parameter sets hit ≈230 with different maps.",YE);
stat(s,8.85,1.8,3.95,"67","areas after enforcing the official rule with a naive merge — London swallows 6.1 M workers. A published description is not a runnable artefact.",CO);
T(s,"ONS publishes the validity rule; the production implementation with its merge order and tie-breaks is what draws the map. An open reimplementation of the EU variant exists — Istat’s LabourMarketAreas on CRAN — and running it here is the natural next step.",
 {x:0.55,y:4.35,w:12.2,h:0.85,fontSize:15,bold:true,isTextBox:true,margin:0,lineSpacing:21});
foot(s,"sliding scale: 3,500 @ 75 % → 25,000 @ 66.7 % · two-sided self-containment · fragments repaired by queen contiguity on MSOA BGC polygons");

// ---------- 8 · Serbia map
s=S(); s.addNotes("Serbia has no matrix at all — four distance bands. You can still do self-containment honestly."); title(s,"Serbia · bands instead of pairs","census 2022 daily migrations · 168 municipalities · 795,779 workers");
s.addImage({path:A+"rs_selfcont.png",x:1.7,y:1.5,w:9.9,h:5.4});
foot(s,"no origin→destination matrix exists — self-containment is computable, delimitation is not");

// ---------- 9 · Serbia findings
s=S(); s.addNotes("Education is MORE local than work: +0.081 is the median of per-municipality gaps; the medians differ by 0.118 — different statistics, both true, say which one you show. Zeros are a definition artefact. Urbanisation does not explain the gap — and tell the area-vs-population weighting trap out loud, it is Trap-2 thinking in disguise. Source: SORS release Dnevne migracije, July 2024."); title(s,"What bands still buy you — if you respect the definition","three findings, one artefact");
stat(s,0.55,1.7,3.95,"50.3 %","of Serbian daily migrants stay inside their municipality. Median municipality: 0.53.",VI);
stat(s,4.7,1.7,3.95,"+0.081","median of per-municipality gaps: education is MORE local than work (medians 0.646 vs 0.528, r = 0.82). One open non-work purpose — pupils and students merged.",GR);
stat(s,8.85,1.7,3.95,"0.00","for 8 single-settlement municipalities: a daily migrant leaves the SETTLEMENT, so any migrant of theirs leaves. Artefact, not finding.",CO);
T(s,"Urbanisation does not explain the education–work gap: correlation +0.03 against GHS-SMOD degree-of-urbanisation (population-weighted, DEGURBA logic).",
 {x:0.55,y:4.15,w:12.2,h:0.6,fontSize:14,color:MUT,isTextBox:true,margin:0});
T(s,"RBSC = residence-based self-containment. First pass weighted urban share by AREA and “found” r = −0.28 — noise: half the municipalities have zero urban pixels. Weight by population.",
 {x:0.55,y:4.85,w:12.2,h:0.7,fontSize:13.5,color:YE,italic:true,isTextBox:true,margin:0,lineSpacing:18});
foot(s,"SORS Popis 2022 (Census does not cover Kosovo*; *UNSCR 1244) · GHS-SMOD/POP R2023A Mollweide · shapefile encoding destroyed Cyrillic names — match exact-first, pattern-second");


// ---------- 9b · Netherlands
s=S(); s.addNotes("NL is the fourth check. The 2006-14 table cages flows into COROP regions drawn as commuter basins in 1970 - basins that have dissolved: median 0.66, only 20 percent pass. Two areas out of delimitation is an artefact of 40 nodes, Trap 2 in disguise. And the twist: the successor table 85481NED publishes municipality pairs monthly since 2021 - I found it re-checking my own slide. Check the successor before you present the cage.");
title(s,"Netherlands · the fourth check: read the successor table","CBS register OD · 81252NED (2006–14, 40 COROP regions) → 85481NED (2021+, municipalities)");
stat(s,0.55,1.8,3.95,"0.66","median 2014 self-containment of COROP regions — drawn as commuter basins in 1970. Only 20 % still pass the 75 % test: the basins have dissolved.",YE);
stat(s,4.7,1.8,3.95,"2","areas my delimitation returns on top of 40 nodes — an artefact of the cage, not a map of Dutch labour markets: 40 units leave no degrees of freedom (Trap 2 in disguise).",CO);
stat(s,8.85,1.8,3.95,"419×419","the successor table I almost missed: since 2021 CBS quietly publishes municipality×municipality pairs, monthly. My own slide nearly told you the cage was permanent.",GR);
T(s,"Resolution is a policy choice — and it changes between table generations. The 2006–14 cage made 1970 boundaries unfalsifiable; the 2021+ successor quietly opened it. Check the successor before you present the cage.",
 {x:0.55,y:4.35,w:12.2,h:0.85,fontSize:15,bold:true,isTextBox:true,margin:0,lineSpacing:21});
foot(s,"opendata.cbs.nl 81252NED / 85481NED · Amsterdam→Utrecht, Dec 2023: 13,200 jobs — a pair the 2014 table could not express");

// ---------- 10 · Japan day/night
s=S(); s.addNotes("Japan gives the axis censuses lack: the clock. Naka-ku, between the delta rivers: 27% of daytime presence is local - three quarters come from outside by day. Say presence, not commuting - shoppers and tourists count too. And name the source honestly: Agoop smartphone-app GPS panel expanded to population, not operator network data. Their census, by the way, publishes full OD pairs - Japan is the one country in my sample with both dimensions."); title(s,"Japan · the clock censuses never see","MLIT people-flow = smartphone-app GPS panel (Agoop SDK, SoftBank group), expanded to population — not MNO");
s.addImage({path:A+"jp_daynight.png",x:1.35,y:1.5,w:10.6,h:5.4});
foot(s,"weekday October 2019 · Naka-ku 中区: 27 % of daytime presence is local residents — three quarters come from outside by day (presence, not commuting)");

// ---------- 11 · signatures
s=S(); s.addNotes("Honesty slide, now with the continuum visible. HDBSCAN at honest settings: 100% noise. Hopkins 0.93 does NOT contradict that — it rejects uniformity, not unimodality: density is concentrated in one mode, with no second mode to separate. If asked did you tune it: yes, swept min_cluster_size 40-60, min_samples 5-15 — one blob plus a thin office tail. k-means would happily cut 4 classes anyway. Declared thresholds beat discovered fictions."); title(s,"Temporal signatures — the honest version","the abstract promised HDBSCAN. HDBSCAN answered: one dense mode, no second cluster.");
s.addImage({path:A+"jp_signatures.png",x:0.85,y:1.55,w:11.6,h:5.35});
foot(s,"declared thresholds on two named axes — visible, criticisable, reproducible · Hopkins rejects uniformity, not unimodality (Adolfsson et al. 2019)");

// ---------- 12 · Japan caveats
s=S(); s.addNotes("Say all three caveats before Q&A does. Volumes: totals agree to 0.3% while population fell 0.7% — normalised by construction, its own proof. From-To is rings, not a matrix. And the panel: Agoop app users expanded to population — who is outside the panel is undisclosed. The clock is real; everyone is not."); title(s,"Three caveats that must be said from the stage","before someone says them from the floor");
stat(s,0.55,1.8,3.95,"±0.3 %","yearly presence totals 2019–21 agree to within ±0.3 % while Japan’s population fell ~0.7 % — the series is normalised by construction. Compare composition, never volume. (Composition does move: weekday local share 0.632 → 0.677.)",YE);
stat(s,4.7,1.8,3.95,"“From–To”","the file name promises an OD matrix. from_area is four nested administrative rings — same structure as the Serbian census. Read the 定義書 before the filename.",CO);
stat(s,8.85,1.8,3.95,"the panel","whose phones? Agoop SDK app users, expanded by 拡大係数 to population. No phones off, no children below app age, panel composition undisclosed. The clock is real; “everyone” is not.",VI);
foot(s,"MLIT データ定義書 p.6 & p.10 · 2019–2021 window includes COVID · values under 10 people suppressed");

// ---------- 13 · decision matrix
s=S(); s.addNotes("The promised takeaway. Pairs->census; clock->MNO; no matrix->bands with definition check; traces->contributor bias."); title(s,"The decision matrix","what to reach for first — and what to check before trusting it");
const dm=[[{text:"you need",options:{bold:true,color:TXT}},{text:"reach for",options:{bold:true,color:TXT}},{text:"before trusting, check",options:{bold:true,color:TXT}}],
 [{text:"commuting structure, delimitation"},{text:"census/register OD pairs: UK · FR MOBPRO · DE BA · JP census · NL 2021+ (EU Hub NUTS-2: too coarse to delimit)",options:{color:GR}},{text:"special place-of-work codes; null model; contiguity; successor tables"}],
 [{text:"intraday presence, day/night"},{text:"ES MITMA hourly MNO OD · JP MLIT app-GPS panel · Multi-MNO pipeline (open source) next",options:{color:VI}},{text:"volume normalisation; suppression; WHO is in the panel"}],
 [{text:"self-containment where no matrix exists"},{text:"census distance bands (RS, JP)",options:{color:YE}},{text:"the migrant DEFINITION — settlement vs municipality"}],
 [{text:"fine-grain routes / activity traces"},{text:"OSM GPS traces",options:{color:CY}},{text:"contributor bias: density follows mappers, not people"}]];
s.addTable(dm,{x:0.55,y:1.7,w:12.2,colW:[3.4,4.6,4.2],fontFace:"Arial",fontSize:13,color:MUT,
 fill:{color:PANEL},border:{type:"solid",color:"3A2D5A",pt:0.75},rowH:0.78,valign:"middle"});
T(s,"Where sources agree, classification is robust. Where they diverge, the divergence is the finding.",
 {x:0.55,y:6.15,w:12.2,h:0.45,fontSize:15,italic:true,color:CY,isTextBox:true,margin:0});

// ---------- 14 · checklist
s=S(); s.addNotes("Closing argument: three checks, one afternoon, each killed one of my results this month. Shuffle, read the code list, draw it."); title(s,"Four checks that cost an afternoon each","and each of them killed one of my own results this month");
const ck=[["1 · Shuffle","Rebuild your areas with random assignment of the same sizes. If random scores 70 % of your result, your result is the aggregation.",CY],
 ["2 · Read the code list","Every special category (home workers, offshore, no fixed place) — where does it land in YOUR denominator? 12.6 M people flipped a national trend.",YE],
 ["3 · Draw it","Join the geometry and look. An unmatched polygon silently inheriting another unit’s values, a mis-centred palette, a fragmented London — invisible in tables.",GR],
 ["4 · Find the successor","Datasets outgrow their cages. The Dutch 40-region OD closed in 2014; its successor publishes municipal pairs. I nearly presented the cage as permanent.",VI]];
ck.forEach((c,i)=>{ const x=0.55+i*3.13;
 s.addShape("roundRect",{x,y:1.75,w:2.93,h:4.3,fill:{color:PANEL},line:{color:"3A2D5A",width:1},rectRadius:0.08});
 T(s,c[0],{x:x+0.25,y:2.0,w:2.45,h:0.85,fontSize:15,bold:true,color:c[2]});
 T(s,c[1],{x:x+0.25,y:2.85,w:2.45,h:3.0,fontSize:11.5,color:MUT,lineSpacing:16});
});
foot(s,"pipeline: Python · GeoPandas · DuckDB · PostGIS-ready · code MIT, slides & figures CC BY 4.0 · repo goes public before this session ends");

// ---------- 15 · thanks
s=S(); s.addNotes("Repeat questions — no microphone in this room.");
T(s,"The blind spot is not missing data.",{x:0.9,y:2.3,w:11.5,h:0.8,fontSize:34,bold:true});
T(s,"It is the dimension your source silently sacrificed.",{x:0.9,y:3.15,w:11.5,h:0.8,fontSize:34,bold:true,color:CY});
T(s,"Marija Ercegovac · URBAN_MASH · talks.osgeo.org/foss4g-2026",{x:0.9,y:5.6,w:11,h:0.45,fontSize:15});
T(s,"slides & figures CC BY 4.0 · code MIT · questions welcome — the room has no microphone, I will repeat every question",{x:0.9,y:6.1,w:11.5,h:0.4,fontSize:12.5,color:MUT});

p.writeFile({ fileName:"/tmp/deck2/talk2.pptx" }).then(()=>console.log("written"));
