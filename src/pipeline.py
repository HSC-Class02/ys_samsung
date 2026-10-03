import csv, json, math, os, re, time
from datetime import date, datetime
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATA, RAW = ROOT / "data", ROOT / "data" / "raw"
API = "https://opendart.fss.or.kr/api"
CORP_CODE, STOCK_CODE, COMPANY = "00126380", "005930", "Samsung Electronics"
START_YEAR = 2010
REPORTS = {"annual":("11011","사업보고서"), "half":("11012","반기보고서"),
           "q1":("11013","분기보고서"), "q3":("11014","3분기보고서")}

KEYS = {
 "total_assets":["자산총계"], "current_assets":["유동자산"], "current_liabilities":["유동부채"],
 "cash":["현금및현금성자산"], "receivables":["매출채권"], "inventory":["재고자산"], "ppe":["유형자산"],
 "total_liabilities":["부채총계"], "debt":["이자부차입금","차입금"], "equity":["자본총계"],
 "revenue":["매출액"], "gross_profit":["매출총이익"], "sga":["판매비와관리비","판매비 및 관리비"],
 "operating_income":["영업이익","영업이익(손실)"], "pretax_income":["법인세비용차감전순이익","세전이익"],
 "net_income":["당기순이익","당기순이익(손실)"], "controlling_net_income":["지배기업의 소유주에게 귀속되는 당기순이익","지배기업 소유주지분 순이익"],
 "interest_expense":["이자비용","금융비용"], "income_tax":["법인세비용"],
 "depreciation":["감가상각비"], "amortization":["무형자산상각비","무형자산 상각비"],
 "cfo":["영업활동으로 인한 현금흐름","영업활동현금흐름"], "cfi":["투자활동으로 인한 현금흐름","투자활동현금흐름"],
 "cff":["재무활동으로 인한 현금흐름","재무활동현금흐름"]
}
BS_KEYS={"total_assets","current_assets","current_liabilities","cash","receivables","inventory","ppe","total_liabilities","debt","equity"}
CF_KEYS={"cfo","cfi","cff","depreciation","amortization"}

def require_key():
    k=os.getenv("OPENDART_API_KEY","").strip()
    if not k: raise RuntimeError("OPENDART_API_KEY environment variable is missing.")
    if len(k)!=40: raise RuntimeError(f"OPENDART_API_KEY must be 40 characters; got {len(k)}.")
    return k

def api_get(path, params, key, retries=4):
    p=dict(params); p["crtfc_key"]=key
    last=None
    for attempt in range(retries):
        try:
            r=requests.get(f"{API}/{path}.json",params=p,timeout=45); r.raise_for_status()
            x=r.json(); status=str(x.get("status",""))
            if status=="000": return x
            last=RuntimeError(f"DART {status}: {x.get('message','unknown error')}")
            if status in {"020","800","900"} and attempt<retries-1: time.sleep(2**attempt); continue
            raise last
        except (requests.RequestException,ValueError) as exc:
            last=exc
            if attempt<retries-1: time.sleep(2**attempt); continue
            raise RuntimeError(f"DART request failed: {exc}")
    raise last

def parse_number(v):
    if v is None: return None
    s=str(v).strip().replace(",","")
    if not s or s in {"-","N/A","nan","None"}: return None
    neg=s.startswith("(") and s.endswith(")")
    if neg: s=s[1:-1]
    s=re.sub(r"[^0-9.\-]","",s)
    if not s or s=="-": return None
    try:
        x=float(s); return -x if neg else x
    except ValueError: return None

def choose(rows, patterns):
    exact={p:[] for p in patterns}; candidates=[]
    for row in rows:
        n=str(row.get("account_nm","")).strip()
        for p in patterns:
            if n==p: exact[p].append(row)
        if any(p in n for p in patterns): candidates.append(row)
    for p in patterns:
        if exact[p]: return exact[p][0]
    return next((r for r in candidates if parse_number(r.get("thstrm_amount")) is not None), candidates[0] if candidates else None)

def val(row, field="thstrm_amount"): return parse_number(row.get(field)) if row else None

def rows_of(payload, sj): return [r for r in payload.get("list",[]) if r.get("sj_div")==sj]

def build_record(payload, fs_div):
    bs, is_, cf = rows_of(payload,"BS"), (rows_of(payload,"IS") or rows_of(payload,"CIS")), rows_of(payload,"CF")
    out={"fs_div":fs_div,"rcept_no":next((r.get("rcept_no") for r in payload.get("list",[]) if r.get("rcept_no")),""),"currency":"KRW","unit":"원"}
    for k,pats in KEYS.items():
        src=bs if k in BS_KEYS else cf if k in CF_KEYS else is_
        row=choose(src,pats); out[k]=val(row); out[k+"__cum"]=val(row,"thstrm_add_amount")
    capex=0; found=False
    for row in cf:
        n=str(row.get("account_nm",""))
        if "유형자산의 취득" in n or "무형자산의 취득" in n:
            v=val(row)
            if v is not None: capex+=abs(v); found=True
    out["capex"]=capex if found else None
    return out

def fetch_filings(key):
    all_items=[]
    for y in range(START_YEAR,date.today().year+1):
        try:
            p=api_get("list",{"corp_code":CORP_CODE,"bgn_de":f"{y}0101","end_de":f"{y}1231","pblntf_ty":"A",
                              "sort":"date","sort_mth":"asc","page_no":1,"page_count":100},key)
        except RuntimeError as e:
            if "DART 013" in str(e): continue
            raise
        all_items += p.get("list",[])
        for page in range(2,int(p.get("total_page",1) or 1)+1):
            try:
                q=api_get("list",{"corp_code":CORP_CODE,"bgn_de":f"{y}0101","end_de":f"{y}1231","pblntf_ty":"A",
                                   "sort":"date","sort_mth":"asc","page_no":page,"page_count":100},key)
            except RuntimeError as e:
                if "DART 013" in str(e): break
                raise
            all_items += q.get("list",[])
    seen={x.get("rcept_no"):x for x in all_items if x.get("rcept_no")}
    out=[]
    for x in seen.values():
        n=str(x.get("report_nm",""))
        if any(t in n for t in ["사업보고서","반기보고서","분기보고서"]):
            y=dict(x); y["dart_url"]=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x['rcept_no']}"
            y["english_dart_url"]=f"https://englishdart.fss.or.kr/dsbh001/main.do?rcpNo={x['rcept_no']}"
            out.append(y)
    return sorted(out,key=lambda z:(z.get("rcept_dt",""),z.get("rcept_no","")))

def fetch_financials(key):
    payloads={}
    for y in range(2015,date.today().year+1):
        for cat,(code,_) in REPORTS.items():
            try:
                p=api_get("fnlttSinglAcntAll",{"corp_code":CORP_CODE,"bsns_year":str(y),"reprt_code":code,"fs_div":"CFS"},key)
                fs="CFS"
            except RuntimeError as e:
                if "DART 013" in str(e): continue
                try:
                    p=api_get("fnlttSinglAcntAll",{"corp_code":CORP_CODE,"bsns_year":str(y),"reprt_code":code,"fs_div":"OFS"},key); fs="OFS"
                except RuntimeError as e2:
                    if "DART 013" in str(e2): continue
                    raise
            payloads[(y,cat)]=(p,fs)
            d=RAW/str(y); d.mkdir(parents=True,exist_ok=True)
            (d/f"{cat}_{fs}.json").write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding="utf-8")
    return payloads

def rec(payloads,y,cat):
    if (y,cat) not in payloads: return None
    p,fs=payloads[(y,cat)]
    return build_record(p,fs)

def div(a,b): return a/b if a is not None and b not in (None,0) else None

def add(r,k,v): r[k]=round(v,6) if v is not None and math.isfinite(v) else None

def calc(r,prev,days):
    rev,gp,op,ni=r.get("revenue"),r.get("gross_profit"),r.get("operating_income"),r.get("net_income")
    if op is not None and (r.get("depreciation") is not None or r.get("amortization") is not None):
        r["ebitda"]=op+(r.get("depreciation") or 0)+(r.get("amortization") or 0)
    else: r["ebitda"]=None
    r["fcf"]=r.get("cfo")-r.get("capex") if r.get("cfo") is not None and r.get("capex") is not None else None
    r["net_debt"]=r.get("debt")-r.get("cash") if r.get("debt") is not None and r.get("cash") is not None else None
    avg_assets=((r.get("total_assets") or 0)+(prev or {}).get("total_assets",r.get("total_assets") or 0))/2 if r.get("total_assets") is not None else None
    avg_eq=((r.get("equity") or 0)+(prev or {}).get("equity",r.get("equity") or 0))/2 if r.get("equity") is not None else None
    vals={"gross_margin":div(gp,rev),"operating_margin":div(op,rev),"net_margin":div(ni,rev),
          "ebitda_margin":div(r.get("ebitda"),rev),"current_ratio":div(r.get("current_assets"),r.get("current_liabilities")),
          "quick_ratio":div((r.get("current_assets")-r.get("inventory")) if r.get("current_assets") is not None and r.get("inventory") is not None else None,r.get("current_liabilities")),
          "debt_ratio":div(r.get("total_liabilities"),r.get("equity")),"equity_ratio":div(r.get("equity"),r.get("total_assets")),
          "debt_dependency":div(r.get("debt"),r.get("total_assets")),"interest_coverage":div(op,r.get("interest_expense")),
          "net_debt_ebitda":div(r.get("net_debt"),r.get("ebitda")),"asset_turnover":div(rev,avg_assets),
          "roa":div(ni,avg_assets),"roe":div(ni,avg_eq),"cfo_to_net_income":div(r.get("cfo"),ni)}
    pretax,tax=r.get("pretax_income"),r.get("income_tax")
    invested=(r.get("debt")+r.get("equity")-r.get("cash")) if None not in (r.get("debt"),r.get("equity"),r.get("cash")) else None
    nopat=op*(1-div(tax,pretax)) if op is not None and div(tax,pretax) is not None else None
    vals["roic"]=div(nopat,invested)
    for k,v in vals.items(): add(r,k,v)
    avg_ar=((r.get("receivables") or 0)+(prev or {}).get("receivables",r.get("receivables") or 0))/2 if r.get("receivables") is not None else None
    avg_inv=((r.get("inventory") or 0)+(prev or {}).get("inventory",r.get("inventory") or 0))/2 if r.get("inventory") is not None else None
    cogs=rev-gp if rev is not None and gp is not None else None
    add(r,"dso",avg_ar/rev*days if avg_ar is not None and rev not in (None,0) else None)
    add(r,"dio",avg_inv/cogs*days if avg_inv is not None and cogs not in (None,0) else None)
    r["dpo"]=None; r["ccc"]=None
    if r["dso"] is not None and r["dio"] is not None and r["dpo"] is not None: r["ccc"]=r["dso"]+r["dio"]-r["dpo"]
    cur=r.get("revenue__cum") if r.get("period_type") in {"half","quarterly"} and r.get("revenue__cum") is not None else rev
    prv=(prev or {}).get("revenue__cum") if r.get("period_type") in {"half","quarterly"} and (prev or {}).get("revenue__cum") is not None else (prev or {}).get("revenue")
    add(r,"revenue_growth",div(cur,prv)-1 if cur is not None and prv not in (None,0) else None)

def annual_rows(payloads):
    out=[]
    for y in range(2015,date.today().year+1):
        x=rec(payloads,y,"annual")
        if x:
            r=dict(x); r.update(period_type="annual",period=f"FY{y}",year=y,quarter=None,report_code="11011")
            calc(r,rec(payloads,y-1,"annual"),365); out.append(r)
    return out

def half_rows(payloads):
    out=[]
    for y in range(2015,date.today().year+1):
        x=rec(payloads,y,"half")
        if x:
            r=dict(x); r.update(period_type="half",period=f"{y}-H1",year=y,quarter=2,report_code="11012")
            r["revenue__cum"]=r.get("revenue__cum") or r.get("revenue")
            calc(r,rec(payloads,y-1,"half"),181); out.append(r)
    return out

def quarterly_rows(payloads):
    out=[]
    for y in range(2015,date.today().year+1):
        q1,h,q3,a=[rec(payloads,y,k) for k in ["q1","half","q3","annual"]]
        prevq={q:rec(payloads,y-1,q) for q in ["q1","half","q3","annual"]}
        if q1:
            r=dict(q1); r.update(period_type="quarterly",period=f"{y}-Q1",year=y,quarter=1,report_code="11013"); r["revenue__cum"]=r.get("revenue")
            calc(r,prevq["q1"],90); out.append(r)
        if h:
            r=dict(h); r.update(period_type="quarterly",period=f"{y}-Q2",year=y,quarter=2,report_code="11012")
            for k in ["cfo","cfi","cff","capex"]:
                if r.get(k) is not None and q1 and q1.get(k) is not None: r[k]-=q1[k]
            r["revenue__cum"]=h.get("revenue__cum") or h.get("revenue"); calc(r,q1 or prevq["half"],91); out.append(r)
        if q3:
            r=dict(q3); r.update(period_type="quarterly",period=f"{y}-Q3",year=y,quarter=3,report_code="11014")
            r["revenue__cum"]=r.get("revenue__cum") or r.get("revenue"); calc(r,h or prevq["q3"],92); out.append(r)
        if a:
            r=dict(a); r.update(period_type="quarterly",period=f"{y}-Q4",year=y,quarter=4,report_code="11011")
            income=["revenue","gross_profit","sga","operating_income","pretax_income","net_income","controlling_net_income","interest_expense","income_tax","depreciation","amortization"]
            for k in income:
                if r.get(k) is not None and h and h.get(k+"__cum") is not None and q3 and q3.get(k+"__cum") is not None:
                    r[k]=r[k]-h[k+"__cum"]-q3[k+"__cum"]
            for k in ["cfo","cfi","cff","capex"]:
                if r.get(k) is not None and q3 and q3.get(k) is not None: r[k]-=q3[k]
            r["revenue__cum"]=r.get("revenue"); calc(r,q3 or prevq["annual"],92); out.append(r)
    return out

def write_csv(rows):
    fields=["period_type","period","year","quarter","report_code","fs_div","currency","unit",
      "total_assets","current_assets","current_liabilities","cash","receivables","inventory","ppe","total_liabilities","debt","equity",
      "revenue","gross_profit","sga","operating_income","pretax_income","net_income","controlling_net_income","depreciation","amortization",
      "ebitda","cfo","cfi","cff","capex","fcf","net_debt","gross_margin","operating_margin","net_margin","ebitda_margin","roa","roe","roic",
      "current_ratio","quick_ratio","debt_ratio","equity_ratio","debt_dependency","interest_coverage","net_debt_ebitda","asset_turnover",
      "dso","dio","dpo","ccc","revenue_growth","cfo_to_net_income","rcept_no"]
    with (DATA/"financials.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader()
        for r in sorted(rows,key=lambda x:(x.get("year",0),x.get("period_type",""),x.get("quarter") or 0)):
            w.writerow({k:"" if r.get(k) is None else r.get(k) for k in fields})

def main():
    key=require_key(); DATA.mkdir(parents=True,exist_ok=True); RAW.mkdir(parents=True,exist_ok=True)
    filings=fetch_filings(key)
    (DATA/"filings.json").write_text(json.dumps({"company":COMPANY,"corp_code":CORP_CODE,"filings":filings},ensure_ascii=False,indent=2),encoding="utf-8")
    payloads=fetch_financials(key); rows=annual_rows(payloads)+half_rows(payloads)+quarterly_rows(payloads); write_csv(rows)
    annual=sorted([r for r in rows if r["period_type"]=="annual"],key=lambda x:x["year"])
    half=sorted([r for r in rows if r["period_type"]=="half"],key=lambda x:x["period"])
    quarter=sorted([r for r in rows if r["period_type"]=="quarterly"],key=lambda x:(x["year"],x["quarter"]))
    latest=annual[-1] if annual else None
    metrics={"company":COMPANY,"stock_code":STOCK_CODE,"corp_code":CORP_CODE,"generated_at":datetime.utcnow().isoformat()+"Z",
             "latest_annual":latest,"annual":annual,"half":half,"quarterly":quarter,"filings":filings,
             "limitations":{"structured_financials":"OpenDART fnlttSinglAcntAll is documented for 2015 onward.",
                            "legacy":"2010–2014 filing indexes are preserved; structured financial amounts need original-file/XBRL recovery outside this API range.",
                            "market_ratios":"PER/PBR/EV-EBITDA are excluded because they need a market-price feed.",
                            "dpo":"DPO is blank unless purchases/payment inputs are reliably available."}}
    (DATA/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding="utf-8")
    (DATA/"last_update.txt").write_text(datetime.now().astimezone().isoformat(),encoding="utf-8")
    print(f"OK: {len(rows)} structured rows; {len(filings)} regular filings")

if __name__=="__main__": main()
