import urllib.request
import urllib.parse
import json
import datetime
import time
import re
import xml.etree.ElementTree as ET

# 👑 설정 및 저널 데이터
HEADERS = {'User-Agent': 'GI-Intel-Bot/1.0'}
TOP_JOURNALS = ["gastroenterology", "gut", "hepatology", "endoscopy", "clinical gastroenterology and hepatology", "journal of hepatology", "american journal of gastroenterology", "gastrointestinal endoscopy", "lancet gastroenterology & hepatology", "nature reviews gastroenterology & hepatology"]
JOURNAL_IF = {"nature reviews gastroenterology & hepatology": 65.1, "lancet gastroenterology & hepatology": 35.7, "gastroenterology": 29.4, "journal of hepatology": 26.8, "gut": 24.5, "hepatology": 13.5, "clinical gastroenterology and hepatology": 11.6, "american journal of gastroenterology": 10.2, "endoscopy": 9.3, "gastrointestinal endoscopy": 7.7}

# ---------------------------
# 🧠 선생님의 고도화된 핵심 로직
# ---------------------------
def extract_conclusion(text):
    m = re.search(r'(?i)(conclusion[s]?:?\s*)(.*)', text)
    return m.group(2) if m else text[:300]

def detect_negative(text):
    return any(k in text.lower() for k in ["no significant", "no difference", "not effective"])

def clinical_impact(text):
    t = text.lower()
    s = 0
    if "mortality" in t: s += 5
    if "survival" in t: s += 5
    if "first-line" in t: s += 4
    return s

def is_low_value(text):
    return any(k in text.lower() for k in ["case report", "animal", "protocol", "letter", "in vitro"])

def gi_translation(text):
    t = text.lower()
    if "anti-tnf" in t: return "👉 Anti-TNF 유지/TDM 고려"
    if "jak" in t: return "👉 JAK 부작용 모니터링"
    if "ustekinumab" in t: return "👉 IL-12/23 반응 평가"
    if "hcc" in t: return "👉 HCC surveillance 재설정"
    if "ppi" in t: return "👉 PPI 전략 재평가"
    return "👉 임상 판단 필요"

def tomorrow_action(text):
    t = text.lower()
    if "superior" in t: return "✅ 우선 적용 고려"
    if "noninferior" in t: return "🔄 대체 가능"
    if detect_negative(t): return "⚠️ 기존 유지 권장"
    return "🧐 추가 판단 필요"

def one_liner(text):
    t = text.lower()
    if "cirrhosis" in t: return "📌 USG 6개월 간격 세팅"
    if "varices" in t: return "📌 EGD follow-up 계획"
    if "biologic" in t: return "📌 Dose escalation 고려"
    return "📌 환자 맞춤형 판단"

def score_paper(title, abstract, journal):
    t = (title + abstract).lower()
    s = 0
    if "randomized" in t or "rct" in t: s += 10
    if "meta-analysis" in t: s += 8
    if "guideline" in t: s += 15
    for jn, val in JOURNAL_IF.items():
        if jn in journal.lower(): s += (val / 2)
    s += clinical_impact(abstract)
    return s

# ---------------------------
# 📡 PubMed 수집 및 데이터 가공
# ---------------------------
def fetch_pubmed(query, limit=10):
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={urllib.parse.quote(query)}&retmax={limit}&sort=date&retmode=json"
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as res:
            ids = json.loads(res.read().decode("utf-8")).get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        
        time.sleep(1)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
        with urllib.request.urlopen(urllib.request.Request(fetch_url, headers=HEADERS)) as res:
            root = ET.fromstring(res.read())
        
        papers = []
        for a in root.findall(".//PubmedArticle"):
            title = a.findtext(".//ArticleTitle", "")
            if is_low_value(title): continue
            
            pmid = a.findtext(".//PMID", "")
            journal = a.findtext(".//Title", "")
            abs_list = [x.text or "" for x in a.findall(".//AbstractText")]
            full_abs = "<br><br>".join(abs_list)
            
            papers.append({
                "pmid": pmid, "title": title, "journal": journal, "abstract": full_abs,
                "core": extract_conclusion(full_abs),
                "score": score_paper(title, full_abs, journal)
            })
        return sorted(papers, key=lambda x: x["score"], reverse=True)
    except: return []

# 🎯 실행 및 카테고리화
categories = {"🍎 GI Track": "GI diseases randomized", "🍺 Liver Track": "cirrhosis OR HCC trial", "🧬 Biliary/Pancreas": "pancreatitis OR pancreas trial"}
sections_html, category_counts, all_collected = "", {}, []

for name, q in categories.items():
    papers = fetch_pubmed(q)
    all_collected.extend(papers)
    category_counts[name.split(" ")[1]] = len(papers)
    p_html = ""
    for p in papers:
        t_low = p['title'].lower()
        badges = ""
        if "randomized" in t_low: badges += "<span class='badge rct'>RCT</span>"
        if detect_negative(p['core']): badges += " ⚠️"
        if any(k in p['abstract'].lower() for k in ["superior", "survival"]): badges += " 🔥"
        
        if_val = next((val for jn, val in JOURNAL_IF.items() if jn in p['journal'].lower()), None)
        if_badge = f"<span class='badge if'>IF {if_val}</span>" if if_val else ""
        
        clinical_note = f"""
        <div class='clinical-note'>
            <div><b>👨‍⚕️ Clinical:</b> {gi_translation(p['core'])}</div>
            <div><b>⚡ Action:</b> {tomorrow_action(p['core'])}</div>
            <div><b>📌 Order:</b> {one_liner(p['core'])}</div>
        </div>"""

        p_html += f"""
        <details class="paper-item">
            <summary>
                <div class="meta">{if_badge} <b>{p['journal']}</b> {badges}</div>
                <div class="title-row"><span class="arrow-icon">▶</span>{p['title']}</div>
            </summary>
            <div class="content">
                {clinical_note}
                <div class="abs">{p['abstract']}</div>
                <div class="btns">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" class="btn pub">🔗 PubMed</a>
                    <button onclick="copyShare('{p['pmid']}')" class="btn shr">📤 공유</button>
                </div>
                <textarea id="s_{p['pmid']}" style="display:none;">📄 GI Intel\\n📌 {p['title']}\\n⚡ Action: {tomorrow_action(p['core'][:50])}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/</textarea>
            </div>
        </details>"""
    sections_html += f"<div class='sec-group'><h3>{name}</h3>{p_html}</div>"

# 🔥 Top 3 산출
top3_list = sorted(all_collected, key=lambda x: x["score"], reverse=True)[:3]
top3_html = "".join([f"<li style='margin-bottom:8px;'><b>{p['title']}</b> <small style='color:#3498db;'>({p['journal']})</small></li>" for p in top3_list])

# 📱 최종 HTML (UI 복구)
time_label = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
html_output = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>GI Intelligence Terminal</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, sans-serif; background:#f5f7fa; color:#2c3e50; margin:0; padding:10px; }}
        .card {{ background:#fff; border-radius:12px; padding:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); margin-bottom:15px; border:1px solid #e0e0e0; }}
        .paper-item {{ background:#fff; border:1px solid #eee; margin-bottom:8px; border-radius:10px; border-left:4px solid #3498db; overflow:hidden; }}
        summary {{ padding:12px; cursor:pointer; list-style:none; outline:none; }}
        .title-row {{ font-weight:bold; font-size:0.95rem; line-height:1.4; display:flex; align-items:flex-start; }}
        .arrow-icon {{ display:inline-block; transition:0.2s; color:#3498db; margin-right:8px; flex-shrink:0; }}
        details[open] .arrow-icon {{ transform:rotate(90deg); }}
        .badge {{ padding:2px 5px; border-radius:4px; font-size:0.65rem; font-weight:bold; color:#fff; }}
        .rct {{ background:#e74c3c; }} .if {{ background:#8e44ad; }}
        .content {{ padding:15px; background:#f9f9f9; border-top:1px solid #eee; font-size:0.9rem; }}
        .clinical-note {{ background:#fff8e1; border-left:4px solid #ffb300; padding:10px; border-radius:8px; margin-bottom:12px; font-size:0.85rem; }}
        .btn {{ flex:1; padding:10px; border-radius:6px; text-align:center; text-decoration:none; font-weight:bold; cursor:pointer; font-size:0.85rem; border:none; color:#fff; }}
        .pub {{ background:#3498db; }} .shr {{ background:#2ecc71; }}
    </style>
</head>
<body>
    <div class="card" style="text-align:center;">
        <h1 style="margin:0; font-size:1.6rem;">🏥 GI Intel Terminal</h1>
        <small>Updated: {time_label} KST</small>
    </div>
    <div class="card" style="border-top: 4px solid #e74c3c;">
        <h2 style="margin-top:0; font-size:1.1rem;">🔥 Weekly Top 3</h2>
        <ul style="padding-left:18px; margin-bottom:0; font-size:0.9rem;">{top3_html}</ul>
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
        <div class="card"><canvas id="c1" style="height:120px;"></canvas></div>
        <div class="card"><canvas id="c2" style="height:120px;"></canvas></div>
    </div>
    <div class="card">{sections_html}</div>
    <script>
        function copyShare(id) {{
            const el = document.getElementById('s_'+id);
            navigator.clipboard.writeText(el.value.replace(/\\\\n/g, '\\n')).then(() => alert("✅ 복사 완료!"));
        }}
        new Chart(document.getElementById('c1'), {{ type:'bar', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:'#3498db'}}] }}, options:{{indexAxis:'y', plugins:{{legend:{{display:false}}}}}} }});
        new Chart(document.getElementById('c2'), {{ type:'doughnut', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:['#e74c3c','#f1c40f','#2ecc71']}}] }}, options:{{plugins:{{legend:{{position:'bottom'}}}}}} }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_output)
