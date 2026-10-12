# bboxes estimados manualmente (x, y, w, h) em px da imagem original
P1 = {  # 750x1200, divisa de painel em y~548
 "きめたよ!":(590,110,50,125), "おれも":(505,265,40,75), "だれかを しあわせにするひと":(205,50,265,80),
 "──誰よりも何よりも":(100,285,95,205), "とくだ さきこ":(490,590,145,35), "しあわせにするん":(590,710,65,105),
 "あべかわ さくら":(490,895,145,35), "みやた ゆき":(490,1148,145,34), "君のおかげだから":(375,590,95,425),
 "はせがわ ごうた":(65,615,235,35), "にしかわ じろう":(65,865,235,35), "くぼ りょうじ":(65,1135,235,35)}
B1 = {  # 750x166
 "連載50回記念企画♡":(20,20,215,50), "幸福喫茶3丁目":(240,10,195,60),
 "上位5名に続く人気キャラは誰かな…!?":(440,5,210,65), "キャラクターコンテスト結果発表!!":(20,95,590,55)}

def overlap(a,b):
    lo=max(a[0],b[0]); hi=min(a[0]+a[2],b[0]+b[2]); return max(0,hi-lo)/min(a[2],b[2])

def column_rtl(items):
    cols=[]
    for k,b in items.items():
        for c in cols:
            if any(overlap(b,items[o])>=0.5 for o in c): c.append(k); break
        else: cols.append([k])
    cols.sort(key=lambda c:-max(items[k][0]+items[k][2] for k in c))
    return [k for c in cols for k in sorted(c,key=lambda k:items[k][1])]

def tiered(items, page_w, gutters=()):
    # 1) faixas por divisas de painel; 2) blocos largos (>60% da largura) viram sub-faixa própria
    bounds=[0,*gutters,10**9]; out=[]
    for top,bot in zip(bounds,bounds[1:]):
        tier={k:b for k,b in items.items() if top<=b[1]+b[3]/2<bot}
        wide=sorted((k for k,b in tier.items() if b[2]>0.6*page_w), key=lambda k:tier[k][1])
        cuts=[tier[k][1] for k in wide]+[10**9]; y0=0
        for cut,wk in zip(cuts,wide+[None]):
            band={k:b for k,b in tier.items() if k not in wide and y0<=b[1]<cut}
            out+=column_rtl(band) if band else []
            if wk: out.append(wk)
            y0=cut
    return out

for name,items,w,g in [("pagina_01",P1,750,(548,)),("banner_01",B1,750,())]:
    print(f"== {name}\n  column_rtl puro:", " | ".join(column_rtl(items)))
    print("  faixas + column_rtl:", " | ".join(tiered(items,w,g)))
