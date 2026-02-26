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
# 🧠 핵심 임상 로직
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
    low_keywords = ["case report", "protocol", "letter", "in vitro"]
    return any(k in text.lower() for k in low_keywords)

def gi_translation(text):
    t = text.lower()
    if any(k in t for k in ["anti-tnf", "infliximab"]): return "👉 Anti-TNF 유지/TDM 고려"
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
# 🛠️ 논문 렌더링 함수 (UI 통합)
# ---------------------------
def render_paper(p, is_top=False):
    t_low = p['title'].lower()
    core = p['core']
    badges = ""
    if "randomized" in t_low: badges += "<span class='badge rct'>RCT</span>"
    if detect_negative(core): badges += " ⚠️"
    if any(k in p['abstract'].lower() for k in ["superior", "survival"]): badges += " 🔥"
    if_val = next((val for jn, val in JOURNAL_IF.items() if jn in p['journal'].lower()), None)
    if_badge = f"<span class='badge if'>IF {if_val}</span>" if if_val else ""
    clinical_note = f"""
    <div class='clinical-note'>
        <div style='margin-bottom:6px;'><b>👨‍⚕️ Clinical:</b> {gi_translation(core)}</div>
        <div style='margin-bottom:6px;'><b>⚡ Action:</b> {tomorrow_action(core)}</div>
        <div><b>📌 Order:</b> {one_liner(core)}</div>
    </div>"""
    border_style = "border-left: 5px solid #e74c3c;" if is_top else "border-left: 4px solid #3498db;"
    bg_style = "background: #fffafa;" if is_top else "background: #fff;"
    return f"""
    <details class="paper-item" style="{border_style} {bg_style}">
        <summary>
            <div class="meta">{if_badge} <b>{p['journal']}</b> {badges}</div>
            <div class="title-row"><span class="arrow-icon">▶</span>{p['title']}</div>
        </summary>
        <div class="content">
            {clinical_note}
            {f"<div class='btm-box'><b>💡 Conclusion</b><br>{core}</div>" if core else ""}
            <div class="abs">{p['abstract']}</div>
            <div class="btns">
                <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" class="btn pub">🔗 PubMed</a>
                <button onclick="copyShare('{p['pmid']}')" class="btn shr">📤 공유</button>
            </div>
            <textarea id="s_{p['pmid']}" style="display:none;">📄 GI Intel\\n📌 {p['title']}\\n⚡ Action: {tomorrow_action(core[:50])}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/</textarea>
        </div>
    </details>"""

# ---------------------------
# 📡 PubMed 수집 함수
# ---------------------------
def fetch_pubmed(query, limit=10):
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmax={limit}&sort=date&retmode=json"
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
                "core": extract_conclusion(full_abs), "score": score_paper(title, full_abs, journal)
            })
        return sorted(papers, key=lambda x: x["score"], reverse=True)
    except: return []

# ---------------------------
# 🎯 데이터 수집 및 HTML 생성
# ---------------------------
categories = {
    "🍎 GI Track": "(IBD OR GERD OR colorectal cancer) AND (randomized OR trial OR guideline)",
    "🍺 Liver Track": "(cirrhosis OR HCC OR 'liver cancer') AND (randomized OR trial OR guideline)",
    "🧬 Biliary/Pancreas": "(pancreatitis OR 'pancreatic cancer' OR cholangitis) AND (randomized OR trial OR guideline)"
}
sections_html, category_counts, all_collected = "", {}, []
for name, q in categories.items():
    papers = fetch_pubmed(q)
    all_collected.extend(papers)
    category_counts[name.split(" ")[1]] = len(papers)
    p_html = "".join([render_paper(p) for p in papers]) if papers else "<p style='padding:15px; color:#7f8c8d;'>최근 논문이 없습니다.</p>"
    sections_html += f"<div class='sec-group'><h3>{name}</h3>{p_html}</div>"

top3_papers = sorted(all_collected, key=lambda x: x["score"], reverse=True)[:3]
top3_html = "".join([render_paper(p, is_top=True) for p in top3_papers])

time_label = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

# 📱 최종 HTML (도표 나란히 배치 최적화)
html_output = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>GI Intelligence Terminal</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --primary: #3498db; --success: #2ecc71; --warning: #ffb300; --bg: #f5f7fa; --text: #2c3e50; }}
        body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 8px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 12px; border: 1px solid #e0e0e0; }}
        
        /* 📊 도표 나란히 배치용 그리드 */
        .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
        .chart-card {{ background: #fff; border-radius: 12px; padding: 8px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }}
        
        .paper-item {{ margin-bottom: 8px; border-radius: 10px; overflow: hidden; list-style: none; border: 1px solid #eee; }}
        summary {{ padding: 12px; cursor: pointer; outline: none; list-style: none; }}
        summary::-webkit-details-marker {{ display: none; }}
        .meta {{ font-size: 0.7rem; color: #7f8c8d; margin-bottom: 4px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
        .title-row {{ font-weight: bold; font-size: 0.9rem; line-height: 1.4; display: flex; align-items: flex-start; }}
        .arrow-icon {{ display: inline-block; transition: transform 0.2s; color: var(--primary); margin-right: 6px; flex-shrink: 0; }}
        details[open] .arrow-icon {{ transform: rotate(90deg); }}
        .badge {{ padding: 1px 4px; border-radius: 3px; font-size: 0.6rem; font-weight: bold; color: #fff; }}
        .rct {{ background: #e74c3c; }} .if {{ background: #8e44ad; }}
        .content {{ padding: 12px; background: #f9f9f9; border-top: 1px solid #eee; font-size: 0.85rem; }}
        .clinical-note {{ background: #fff8e1; border-left: 3px solid var(--warning); padding: 10px; border-radius: 6px; margin-bottom: 10px; font-size: 0.8rem; color: #5d4037; }}
        .btm-box {{ background: #ebf5ff; padding: 10px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid var(--primary); font-weight: bold; }}
        .btn {{ flex: 1; padding: 8px; border-radius: 6px; text-align: center; text-decoration: none; font-weight: bold; cursor: pointer; font-size: 0.8rem; border: none; color: #fff; }}
        .pub {{ background: var(--primary); }} .shr {{ background: var(--success); }}
        .filter-btn {{ width: 100%; padding: 10px; border-radius: 20px; border: 1px solid var(--success); background: #fff; color: var(--success); font-weight: bold; cursor: pointer; margin-bottom: 12px; font-size: 0.85rem; }}
        .filter-btn.active {{ background: var(--success); color: #fff; }}
        h3 {{ font-size: 1.1rem; margin: 15px 0 10px 0; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
    </style>
</head>
<body>
    <div class="card" style="text-align:center;">
        <h1 style="margin:0; font-size:1.4rem;">🏥 GI Intel Terminal</h1>
        <small style="font-size:0.75rem;">Updated: {time_label} KST</small>
    </div>
    
    <div class="card" style="border-top: 5px solid #e74c3c;">
        <h2 style="margin-top:0; font-size:1rem; color:#e74c3c;">🔥 Weekly Top 3 Analysis</h2>
        {top3_html}
    </div>

    <div class="chart-grid">
        <div class="chart-card"><canvas id="c1" style="height:100px; width:100%;"></canvas></div>
        <div class="chart-card"><canvas id="c2" style="height:100px; width:100%;"></canvas></div>
    </div>

    <div class="card">
        <button id="fBtn" class="filter-btn" onclick="toggleF()">📋 가이드라인만 보기</button>
        {sections_html}
    </div>

    <footer style="text-align:center; padding:15px; color:#95a5a6; font-size:0.75rem;">🚀 MedProductive Clinical Terminal</footer>

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
            navigator.clipboard.writeText(el.value.replace(/\\\\n/g, '\\n')).then(() => alert("✅ 복사 완료!"));
        }}
        
        // 차트 폰트 및 설정 모바일 최적화
        const chartOptions = {{
            responsive: true, maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }} }},
            scales: {{ x: {{ display: false }}, y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 9 }} }} }} }}
        }};

        new Chart(document.getElementById('c1'), {{ 
            type:'bar', 
            data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:'#3498db'}}] }}, 
            options: chartOptions
        }});
        
        new Chart(document.getElementById('c2'), {{ 
            type:'doughnut', 
            data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:['#e74c3c','#f1c40f','#2ecc71']}}] }}, 
            options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }} }} 
        }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_output)
