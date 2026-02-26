import urllib.request
import urllib.parse
import json
import datetime
import time
import re
import xml.etree.ElementTree as ET

# 👑 설정 및 저널 데이터 (Impact Factor 포함)
HEADERS = {'User-Agent': 'GI-Intel-Bot/1.0'}
TOP_JOURNALS = ["gastroenterology", "gut", "hepatology", "endoscopy", "clinical gastroenterology and hepatology", "journal of hepatology", "american journal of gastroenterology", "gastrointestinal endoscopy", "lancet gastroenterology & hepatology", "nature reviews gastroenterology & hepatology"]
JOURNAL_IF = {"nature reviews gastroenterology & hepatology": 65.1, "lancet gastroenterology & hepatology": 35.7, "gastroenterology": 29.4, "journal of hepatology": 26.8, "gut": 24.5, "hepatology": 13.5, "clinical gastroenterology and hepatology": 11.6, "american journal of gastroenterology": 10.2, "endoscopy": 9.3, "gastrointestinal endoscopy": 7.7}

# ---------------------------
# 🧠 고도화된 임상 판단 로직 (선생님 의견 반영)
# ---------------------------
def gi_translation(text):
    t = text.lower()
    # IBD 세분화
    if any(k in t for k in ["infliximab", "adalimumab", "anti-tnf"]): return "👉 Anti-TNF 유지 및 TDM 고려"
    if any(k in t for k in ["tofacitinib", "upadacitinib", "jak"]): return "👉 JAK inhibitor 부작용(대상포진 등) 모니터링"
    if "ustekinumab" in t: return "👉 IL-12/23 억제제 반응 평가"
    # Liver 세분화
    if any(k in t for k in ["propranolol", "carvedilol", "nsbb"]): return "👉 정맥류 예방 위한 NSBB 적정 용량 조절"
    if "rifaximin" in t or "lactulose" in t: return "👉 간성 뇌증 재발 방지 전략"
    if "hcc" in t: return "👉 HCC Surveillance 전략 재검토"
    # GI Common
    if "ppi" in t: return "👉 PPI 불응성인 경우 P-CAB 전환 검토"
    if "eradication" in t: return "👉 제균 치료 후 4주 뒤 UBT 확인"
    return "👉 개별 임상 판단 필요"

def tomorrow_action(text):
    t = text.lower()
    if "superior" in t: return "✅ 기존 치료보다 우수 (우선 고려)"
    if "noninferior" in t or "equivalent" in t: return "🔄 대체 가능 (상황별 적용)"
    if any(k in t for k in ["no significant", "not effective", "no difference"]): return "⚠️ 기존 치료 유지 권장"
    return "🧐 데이터 추가 확인 필요"

def one_liner_order(text):
    t = text.lower()
    if "flare" in t: return "📌 5-ASA 증량 및 Calprotectin 검사 추가"
    if "polypectomy" in t: return "📌 용종 크기/개수에 따른 1~3년 뒤 추적"
    if "variceal" in t: return "📌 6~12개월 간격 EGD follow-up"
    if "cirrhosis" in t: return "📌 AFP + Liver USG 6개월 간격 세팅"
    if "biologic" in t: return "📌 Biologics Escalation 고려"
    return "📌 처방 추가 판단 필요"

def is_low_value(text):
    return any(k in text.lower() for k in ["case report", "animal study", "protocol", "letter", "in vitro"])

def score_paper(title, abstract, journal):
    t = (title + abstract).lower()
    score = 0
    if "randomized" in t or "rct" in t: score += 10
    if "meta-analysis" in t: score += 8
    if any(k in t for k in ["guideline", "consensus", "recommendation"]): score += 15
    for jn, val in JOURNAL_IF.items():
        if jn in journal.lower(): score += (val / 2)
    return score

# ---------------------------
# 📡 PubMed 수집 및 분석
# ---------------------------
def fetch_pubmed(query, limit=10):
    try:
        encoded = urllib.parse.quote(query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&sort=date&retmode=json"
        with urllib.request.urlopen(urllib.request.Request(search_url, headers=HEADERS)) as res:
            ids = json.loads(res.read().decode("utf-8")).get("esearchresult", {}).get("idlist", [])
        if not ids: return []
        
        time.sleep(1)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
        with urllib.request.urlopen(urllib.request.Request(fetch_url, headers=HEADERS)) as res:
            root = ET.fromstring(res.read())
        
        papers = []
        for article in root.findall(".//PubmedArticle"):
            title = article.findtext(".//ArticleTitle", default="No Title")
            if is_low_value(title): continue # 저가치 논문 필터링
            
            pmid = article.findtext(".//PMID", default="")
            journal = article.findtext(".//Title", default="Unknown Journal")
            abstract_parts, bottom_line = [], ""
            
            for abs_text in article.findall(".//AbstractText"):
                label, text = abs_text.get("Label", ""), abs_text.text or ""
                if label:
                    abstract_parts.append(f"<b style='color:#3498db;'>{label}:</b> {text}")
                    if label.lower() in ["conclusion", "conclusions"]: bottom_line = text
                else:
                    abstract_parts.append(text)
            
            abstract_full = "<br><br>".join(abstract_parts)
            papers.append({
                "pmid": pmid, "title": title, "journal": journal,
                "abstract": abstract_full, "bottom_line": bottom_line,
                "score": score_paper(title, abstract_full, journal)
            })
        return sorted(papers, key=lambda x: x["score"], reverse=True)
    except: return []

# ---------------------------
# 🎨 데이터 가공 및 HTML 생성
# ---------------------------
categories = {"🍎 GI Track": "Gastrointestinal Diseases", "🍺 Liver Track": "Hepatology", "🧬 Biliary/Pancreas": "Pancreas OR Biliary Tract"}
sections_html, category_counts = "", {}

for name, query in categories.items():
    papers = fetch_pubmed(query)
    category_counts[name.split(" ")[1]] = len(papers)
    p_html = ""
    for p in papers:
        t_low = p['title'].lower()
        badges = ""
        if "randomized" in t_low or "rct" in t_low: badges += "<span class='badge rct'>RCT</span>"
        if any(k in t_low for k in ["guideline", "consensus"]): badges += "<span class='badge gl badge-guideline'>Guideline</span>"
        if any(k in p['abstract'].lower() for k in ["superior", "mortality", "survival"]): badges += " 🔥"
        if any(k in t_low for k in ["endoscopy", "colonoscopy", "egd", "ercp", "eus"]): badges += "<span class='badge endo'>Endo</span>"
        
        j_low = p['journal'].lower()
        top_crown = "👑" if any(tj in j_low for tj in TOP_JOURNALS) else ""
        if_val = next((val for jn, val in JOURNAL_IF.items() if jn in j_low), None)
        if_badge = f"<span class='badge if'>IF {if_val}</span>" if if_val else ""
        
        clinical_note = f"""
        <div class='clinical-note'>
            <div style='margin-bottom:6px;'><b>👨‍⚕️ Clinical:</b> {gi_translation(p['title'])}</div>
            <div style='margin-bottom:6px;'><b>⚡ Action:</b> {tomorrow_action(p['abstract'] if p['abstract'] else p['title'])}</div>
            <div><b>📌 Order:</b> {one_liner_order(p['abstract'] if p['abstract'] else p['title'])}</div>
        </div>"""

        share_txt = f"📄 [GI Intel]\\n📌 {p['title']}\\n📖 {p['journal']}\\n⚡ Action: {tomorrow_action(p['abstract'][:50])}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"

        p_html += f"""
        <details class="paper-item">
            <summary>
                <div class="meta">{top_crown} {if_badge} <b>{p['journal']}</b> {badges}</div>
                <div class="title-row"><span class="arrow-icon">▶</span>{p['title']}</div>
            </summary>
            <div class="content">
                {clinical_note}
                {f"<div class='btm-box'><b>💡 Bottom Line</b><br>{p['bottom_line']}</div>" if p['bottom_line'] else ""}
                <div class="abs">{p['abstract']}</div>
                <div class="btns">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" class="btn pub">🔗 PubMed</a>
                    <button onclick="copyShare('{p['pmid']}')" class="btn shr">📤 카톡공유</button>
                </div>
                <textarea id="s_{p['pmid']}" style="display:none;">{share_txt}</textarea>
            </div>
        </details>"""
    sections_html += f"<div class='sec-group'><h3>{name}</h3>{p_html}</div>"

# 📱 UI 최적화 디자인
time_label = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
html_output = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>GI Intelligence Terminal</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --primary: #3498db; --success: #2ecc71; --warning: #ffb300; --bg: #f5f7fa; --text: #2c3e50; }}
        body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 10px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e0e0e0; }}
        .paper-item {{ background: #fff; border: 1px solid #eee; margin-bottom: 8px; border-radius: 10px; border-left: 4px solid var(--primary); overflow: hidden; list-style: none; }}
        summary {{ padding: 12px; cursor: pointer; outline: none; list-style: none; }}
        summary::-webkit-details-marker {{ display: none; }}
        .meta {{ font-size: 0.75rem; color: #7f8c8d; margin-bottom: 5px; display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }}
        .title-row {{ font-weight: bold; font-size: 0.95rem; line-height: 1.4; display: flex; align-items: flex-start; }}
        .arrow-icon {{ display: inline-block; transition: transform 0.2s; color: var(--primary); margin-right: 8px; flex-shrink: 0; }}
        details[open] .arrow-icon {{ transform: rotate(90deg); }}
        .badge {{ padding: 2px 5px; border-radius: 4px; font-size: 0.65rem; font-weight: bold; color: #fff; }}
        .rct {{ background: #e74c3c; }} .gl {{ background: var(--success); }} .if {{ background: #8e44ad; }} .endo {{ background: #9b59b6; }}
        .content {{ padding: 15px; background: #f9f9f9; border-top: 1px solid #eee; font-size: 0.9rem; }}
        .clinical-note {{ background: #fff8e1; border-left: 4px solid var(--warning); padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 0.85rem; color: #5d4037; }}
        .btm-box {{ background: #ebf5ff; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid var(--primary); font-weight: bold; }}
        .btn {{ flex: 1; padding: 10px; border-radius: 6px; text-align: center; text-decoration: none; font-weight: bold; cursor: pointer; font-size: 0.85rem; border: none; color: #fff; }}
        .pub {{ background: var(--primary); }} .shr {{ background: var(--success); }}
        .filter-btn {{ width: 100%; padding: 12px; border-radius: 20px; border: 2px solid var(--success); background: #fff; color: var(--success); font-weight: bold; cursor: pointer; margin-bottom: 15px; }}
        .filter-btn.active {{ background: var(--success); color: #fff; }}
    </style>
</head>
<body>
    <div class="card" style="text-align:center;">
        <h1 style="margin:0; font-size:1.6rem;">🏥 GI Intel Terminal</h1>
        <div style="margin-top:8px;"><span style="background:#ebf5ff; color:var(--primary); padding:4px 12px; border-radius:15px; font-size:0.75rem; font-weight:bold;">Updated: {time_label} KST</span></div>
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
        <div class="card"><canvas id="c1" style="height:120px;"></canvas></div>
        <div class="card"><canvas id="c2" style="height:120px;"></canvas></div>
    </div>
    <div class="card">
        <button id="fBtn" class="filter-btn" onclick="toggleF()">📋 가이드라인만 보기</button>
        {sections_html}
    </div>
    <footer style="text-align:center; padding:20px; color:#95a5a6; font-size:0.8rem;">🚀 Project: MedProductive - Advanced Clinical Terminal</footer>
    <script>
        function toggleF() {{
            const btn = document.getElementById('fBtn'); btn.classList.toggle('active');
            const isF = btn.classList.contains('active');
            document.querySelectorAll('.paper-item').forEach(p => {{
                p.style.display = isF ? (p.querySelector('.badge-guideline') ? 'block' : 'none') : 'block';
            }});
        }}
        function copyShare(id) {{
            const el = document.getElementById('s_'+id);
            navigator.clipboard.writeText(el.value.replace(/\\\\n/g, '\\n')).then(() => alert("✅ 임상 판단 포함 텍스트 복사 완료!"));
        }}
        new Chart(document.getElementById('c1'), {{ type:'bar', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:'#3498db'}}] }}, options:{{indexAxis:'y', plugins:{{legend:{{display:false}}}}}} }});
        new Chart(document.getElementById('c2'), {{ type:'doughnut', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:['#e74c3c','#f1c40f','#2ecc71']}}] }}, options:{{plugins:{{legend:{{position:'bottom'}}}}}} }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_output)
