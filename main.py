import urllib.request
import urllib.parse
import json
import datetime
import time
import re
import xml.etree.ElementTree as ET

# 👑 설정 및 저널 데이터
HEADERS = {'User-Agent': 'GI-Intel-Bot/1.0'}
JOURNAL_IF = {
    "nature reviews gastroenterology & hepatology": 65.1,
    "lancet gastroenterology & hepatology": 35.7,
    "gastroenterology": 29.4,
    "journal of hepatology": 26.8,
    "gut": 24.5,
    "hepatology": 13.5,
    "clinical gastroenterology and hepatology": 11.6,
    "american journal of gastroenterology": 10.2,
    "endoscopy": 9.3,
    "gastrointestinal endoscopy": 7.7
}

# ---------------------------
# 🧠 선생님의 고도화된 핵심 로직
# ---------------------------
def extract_conclusion(text):
    parts = text.split("<br><br>")
    for p in parts[::-1]:
        if len(p) > 50: return p
    return text[:300]

def detect_negative(text):
    return any(k in text.lower() for k in ["no significant", "no difference", "not effective"])

def clinical_impact(text):
    t, s = text.lower(), 0
    if "mortality" in t: s += 5
    if "survival" in t: s += 5
    if "first-line" in t: s += 4
    return s

def is_low_value(text):
    t = text.lower()
    return any(k in t for k in ["case report", "protocol", "letter", "in vitro", "mouse", "rat", "mice", "retrospective", "single center"])

def gi_translation(text):
    t = text.lower()
    if "anti-tnf" in t or "infliximab" in t: return "👉 Anti-TNF 유지/TDM 고려"
    if "jak" in t or "tofacitinib" in t: return "👉 JAK safety 모니터링"
    if "ustekinumab" in t: return "👉 IL-12/23 반응 평가"
    if "vedolizumab" in t: return "👉 Gut-selective biologic 고려"
    if "ascites" in t: return "👉 Paracentesis + Albumin 고려"
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
    if "cirrhosis" in t: return "📌 USG 6개월 간격"
    if "varices" in t: return "📌 EGD follow-up"
    if "biologic" in t: return "📌 Dose escalation 고려"
    return "📌 환자 맞춤 판단"

def score_paper(title, abstract, journal):
    t, s = (title + abstract).lower(), 0
    if "randomized" in t or "rct" in t: s += 10
    if "meta-analysis" in t: s += 8
    if "guideline" in t: s += 15
    for jn, val in JOURNAL_IF.items():
        if jn in journal.lower(): s += (val / 2)
    s += clinical_impact(abstract)
    return s

def is_practice_changing(p):
    t = (p['title'] + p['abstract']).lower()
    return any(k in t for k in ["guideline", "phase 3", "first-line", "standard of care"])

# ---------------------------
# 🛠️ 통합 Render 함수
# ---------------------------
def render_paper(p, is_top=False):
    t_low = p['title'].lower()
    core = p['core']
    badges = ""
    if "randomized" in t_low: badges += "<span class='badge rct'>RCT</span>"
    if "guideline" in t_low: badges += "<span class='badge gl badge-guideline'>GL</span>"
    if detect_negative(core): badges += " ⚠️"
    if any(k in p['abstract'].lower() for k in ["superior", "survival"]): badges += " 🔥"
    
    if_val = next((val for jn, val in JOURNAL_IF.items() if jn in p['journal'].lower()), None)
    if_badge = f"<span class='badge if'>IF {if_val}</span>" if if_val else ""
    
    clinical_note = f"""
    <div class='clinical-note'>
        <div><b>👨‍⚕️ Clinical:</b> {gi_translation(core)}</div>
        <div><b>⚡ Action:</b> {tomorrow_action(core)}</div>
        <div><b>📌 Order:</b> {one_liner(core)}</div>
    </div>"""

    border = "border-left:5px solid #e74c3c;" if is_top else "border-left:4px solid #3498db;"
    bg = "background:#fffafa;" if is_top else "background:#fff;"
    
    share_text = f"📄 GI Intel\\n📌 {p['title']}\\n🏥 {p['journal']}\\n⚡ {tomorrow_action(core)}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"

    return f"""
    <details class="paper-item" style="{border}{bg}">
        <summary>
            <div class="meta">{if_badge} <b>{p['journal']}</b> {badges}</div>
            <div class="title-row"><span class="arrow-icon">▶</span>{p['title']}</div>
        </summary>
        <div class="content">
            {clinical_note}
            <div class='btm-box'><b>💡 Conclusion</b><br>{core}</div>
            <div class="abs">{p['abstract']}</div>
            <div class="btns">
                <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" class="btn pub">🔗 PubMed</a>
                <button onclick="copyShare('{p['pmid']}')" class="btn shr">📤 공유</button>
            </div>
            <textarea id="s_{p['pmid']}" style="display:none;">{share_text}</textarea>
        </div>
    </details>"""

# ---------------------------
# 📡 Fetch 및 분석
# ---------------------------
def fetch_pubmed(query, limit=10):
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&sort=date&retmode=json"
        with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS)) as res:
            ids = json.loads(res.read().decode())["esearchresult"]["idlist"]
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

# 🎯 실행
categories = {
    "🍎 GI Track": "(IBD OR GERD OR colorectal cancer) AND (randomized OR phase 3 OR guideline)",
    "🍺 Liver Track": "(cirrhosis OR HCC) AND (randomized OR phase 3 OR guideline)",
    "🧬 Biliary/Pancreas": "(pancreatitis OR pancreatic cancer OR cholangitis) AND (randomized OR phase 3 OR guideline)"
}

sections_html, all_collected, cat_counts = "", [], {}
for name, q in categories.items():
    papers = fetch_pubmed(q)
    all_collected.extend(papers)
    cat_counts[name.split(" ")[1]] = len(papers)
    sections_html += f"<div class='sec-group'><h3>{name}</h3>" + "".join([render_paper(p) for p in papers]) + "</div>"

top3 = sorted([p for p in all_collected if is_practice_changing(p)], key=lambda x: x["score"], reverse=True)[:3]
top3_html = "".join([render_paper(p, True) for p in top3])

time_label = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

# 📱 최종 HTML (막대그래프 삭제 및 UI 최적화)
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
        
        /* 🍩 도표 중앙 배치 스타일 */
        .chart-container {{ background: #fff; border-radius: 12px; padding: 12px; border: 1px solid #e0e0e0; height: 160px; display: flex; justify-content: center; margin-bottom: 12px; }}
        
        .paper-item {{ margin-bottom: 8px; border-radius: 10px; overflow: hidden; list-style: none; border: 1px solid #eee; }}
        summary {{ padding: 12px; cursor: pointer; outline: none; list-style: none; }}
        summary::-webkit-details-marker {{ display: none; }}
        .meta {{ font-size: 0.7rem; color: #7f8c8d; margin-bottom: 4px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
        .title-row {{ font-weight: bold; font-size: 0.9rem; line-height: 1.4; display: flex; align-items: flex-start; }}
        .arrow-icon {{ display: inline-block; transition: transform 0.2s; color: var(--primary); margin-right: 6px; flex-shrink: 0; }}
        details[open] .arrow-icon {{ transform: rotate(90deg); }}
        .badge {{ padding: 1px 4px; border-radius: 3px; font-size: 0.6rem; font-weight: bold; color: #fff; }}
        .rct {{ background: #e74c3c; }} .gl {{ background: var(--success); }} .if {{ background: #8e44ad; }}
        .content {{ padding: 12px; background: #f9f9f9; border-top: 1px solid #eee; font-size: 0.85rem; }}
        .clinical-note {{ background: #fff8e1; border-left: 3px solid var(--warning); padding: 10px; border-radius: 6px; margin-bottom: 10px; font-size: 0.8rem; color: #5d4037; }}
        .btm-box {{ background: #ebf5ff; padding: 10px; border-radius: 6px; margin-bottom: 10px; border-left: 3px solid var(--primary); font-weight: bold; }}
        .btn {{ flex: 1; padding: 8px; border-radius: 6px; text-align: center; text-decoration: none; font-weight: bold; cursor: pointer; font-size: 0.8rem; border: none; color: #fff; }}
        .pub {{ background: var(--primary); }} .shr {{ background: var(--success); }}
        h3 {{ font-size: 1.1rem; margin: 15px 0 10px 0; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
    </style>
</head>
<body>
    <div class="card" style="text-align:center;">
        <h1 style="margin:0; font-size:1.4rem;">🏥 GI Intel Terminal</h1>
        <small style="font-size:0.75rem;">Updated: {time_label} KST</small>
    </div>
    
    <div class="card" style="border-top: 5px solid #e74c3c;">
        <h2 style="margin-top:0; font-size:1rem; color:#e74c3c;">🔥 Weekly Top 3 (Practice-Changing)</h2>
        {top3_html}
    </div>

    <div class="chart-container">
        <canvas id="c2"></canvas>
    </div>

    <div class="card">
        <button id="fBtn" onclick="toggleF()" style="width:100%; padding:10px; border-radius:20px; border:1px solid var(--success); background:#fff; color:var(--success); font-weight:bold; cursor:pointer; font-size: 0.85rem;">📋 가이드라인만 보기</button>
        {sections_html}
    </div>

    <footer style="text-align:center; padding:15px; color:#95a5a6; font-size:0.75rem;">🚀 Project: MedProductive Clinical AI</footer>

    <script>
        function toggleF() {{
            const btn = document.getElementById('fBtn'); btn.classList.toggle('active');
            const isF = btn.classList.contains('active');
            btn.style.background = isF ? 'var(--success)' : '#fff';
            btn.style.color = isF ? '#fff' : 'var(--success)';
            document.querySelectorAll('.paper-item').forEach(p => {{
                p.style.display = isF ? (p.querySelector('.badge-guideline') ? 'block' : 'none') : 'block';
            }});
        }}
        function copyShare(id) {{
            const el = document.getElementById('s_'+id);
            navigator.clipboard.writeText(el.value.replace(/\\\\n/g, '\\n')).then(() => alert("✅ 복사 완료!"));
        }}
        
        // 도넛 차트만 렌더링
        new Chart(document.getElementById('c2'), {{ 
            type:'doughnut', 
            data:{{ labels:{json.dumps(list(cat_counts.keys()))}, datasets:[{{data:{json.dumps(list(cat_counts.values()))}, backgroundColor:['#e74c3c','#f1c40f','#2ecc71']}}] }}, 
            options: {{ 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: {{ 
                    legend: {{ position: 'right', labels: {{ font: {{ size: 10 }} }} }} 
                }} 
            }} 
        }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_output)
