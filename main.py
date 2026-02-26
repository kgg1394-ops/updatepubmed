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

# 🛠️ 분석 로직 (선생님의 아이디어 반영)
def compute_score(title, journal):
    t, j, score = title.lower(), journal.lower(), 0
    if "randomized" in t or "rct" in t: score += 10
    if "meta-analysis" in t or "systematic" in t: score += 8
    if any(k in t for k in ["guideline", "consensus", "recommendation"]): score += 15
    for jn, val in JOURNAL_IF.items():
        if jn in j: score += (val / 2)
    return score

def detect_practice_change(text):
    keywords = ["reduced mortality", "improved survival", "superior", "noninferior", "first-line", "significant improvement", "standard of care"]
    return any(k in text.lower() for k in keywords)

# 📡 PubMed 수집 함수
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
            pmid = article.findtext(".//PMID", default="")
            title = article.findtext(".//ArticleTitle", default="No Title")
            journal = article.findtext(".//Title", default="Unknown Journal")
            abstract_parts, bottom_line = [], ""
            for abs_text in article.findall(".//AbstractText"):
                label, text = abs_text.get("Label", ""), abs_text.text or ""
                if label:
                    abstract_parts.append(f"<b style='color:#3498db;'>{label}:</b> {text}")
                    if label.lower() in ["conclusion", "conclusions"]: bottom_line = text
                else:
                    abstract_parts.append(text)
                    match = re.search(r'(?i)(?:conclusion|conclusions)[:.]\s*(.*)', text)
                    if match: bottom_line = match.group(1)
            
            papers.append({
                "pmid": pmid, "title": title, "journal": journal,
                "abstract": "<br><br>".join(abstract_parts), "bottom_line": bottom_line,
                "score": compute_score(title, journal)
            })
        return sorted(papers, key=lambda x: x["score"], reverse=True)
    except: return []

# 🍎 카테고리별 데이터 생성
categories = {"🍎 GI": "Gastrointestinal Diseases", "🍺 Liver": "Hepatology", "🧬 Pancreas": "Pancreas OR Biliary Tract"}
sections_html, category_counts = "", {}

for name, query in categories.items():
    papers = fetch_pubmed(query)
    category_counts[name] = len(papers)
    p_html = ""
    for p in papers:
        t_low = p['title'].lower()
        badges = ""
        if "randomized" in t_low or "rct" in t_low: badges += "<span class='badge rct'>RCT</span>"
        if "guideline" in t_low or "consensus" in t_low: badges += "<span class='badge gl badge-guideline'>Guideline</span>"
        if detect_practice_change(p['bottom_line']): badges += " 🔥"
        
        j_low = p['journal'].lower()
        top_crown = "👑" if any(tj in j_low for tj in TOP_JOURNALS) else ""
        if_val = next((val for jn, val in JOURNAL_IF.items() if jn in j_low), None)
        if_badge = f"<span class='badge if'>IF {if_val}</span>" if if_val else ""
        
        share_txt = f"📄 [GI Intel]\\n📌 {p['title']}\\n📖 {p['journal']}{' (IF:'+str(if_val)+')' if if_val else ''}\\n💡 결론: {p['bottom_line'][:100] if p['bottom_line'] else '원문참조'}...\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"

        p_html += f"""
        <details class="paper-item">
            <summary>
                <div class="meta">{top_crown} {if_badge} <b>{p['journal']}</b> {badges}</div>
                <div class="title"><span class="arrow">▶</span>{p['title']}</div>
            </summary>
            <div class="content">
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

# 🎨 디자인 및 HTML 생성
time_label = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
html_output = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>GI Intelligence</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: -apple-system, sans-serif; background:#f5f7fa; color:#2c3e50; margin:0; padding:10px; }}
        .card {{ background:#fff; border-radius:12px; padding:15px; box-shadow:0 2px 8px rgba(0,0,0,0.05); margin-bottom:15px; border:1px solid #e0e0e0; }}
        .paper-item {{ background:#fff; border:1px solid #eee; margin-bottom:8px; border-radius:10px; border-left:4px solid #3498db; overflow:hidden; }}
        summary {{ padding:12px; cursor:pointer; list-style:none; outline:none; }}
        summary::-webkit-details-marker {{ display:none; }}
        .meta {{ font-size:0.75rem; color:#7f8c8d; margin-bottom:5px; display:flex; align-items:center; gap:5px; flex-wrap:wrap; }}
        .title {{ font-weight:bold; font-size:0.95rem; line-height:1.4; }}
        .arrow {{ display:inline-block; transition:0.2s; color:#3498db; margin-right:5px; }}
        details[open] .arrow {{ transform:rotate(90deg); }}
        .badge {{ padding:2px 5px; border-radius:4px; font-size:0.65rem; font-weight:bold; color:#fff; }}
        .rct {{ background:#e74c3c; }} .gl {{ background:#2ecc71; }} .if {{ background:#8e44ad; }}
        .content {{ padding:15px; background:#f9f9f9; border-top:1px solid #eee; font-size:0.9rem; }}
        .btm-box {{ background:#ebf5ff; padding:12px; border-radius:8px; margin-bottom:12px; border-left:4px solid #3498db; }}
        .btns {{ display:flex; gap:10px; margin-top:15px; }}
        .btn {{ flex:1; padding:10px; border-radius:6px; text-align:center; text-decoration:none; font-weight:bold; border:none; cursor:pointer; font-size:0.85rem; color:#fff; }}
        .pub {{ background:#3498db; }} .shr {{ background:#2ecc71; }}
        .filter-btn {{ width:100%; padding:10px; border-radius:20px; border:2px solid #2ecc71; background:#fff; color:#2ecc71; font-weight:bold; cursor:pointer; margin-bottom:15px; }}
        .filter-btn.active {{ background:#2ecc71; color:#fff; }}
    </style>
</head>
<body>
    <div class="card" style="text-align:center;"><h1>🏥 GI Intelligence</h1><small>SYS.UPDATE: {time_label}</small></div>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
        <div class="card"><canvas id="c1" style="height:150px;"></canvas></div>
        <div class="card"><canvas id="c2" style="height:150px;"></canvas></div>
    </div>
    <div class="card">
        <button id="fBtn" class="filter-btn" onclick="toggleF()">📋 가이드라인만 보기</button>
        {sections_html}
    </div>
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
            const val = el.value.replace(/\\\\n/g, '\\n');
            navigator.clipboard.writeText(val).then(() => alert("✅ 복사 완료! 단톡방에 붙여넣으세요."));
        }}
        new Chart(document.getElementById('c1'), {{ type:'bar', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:'#3498db'}}] }}, options:{{indexAxis:'y', plugins:{{legend:{{display:false}}}}}} }});
        new Chart(document.getElementById('c2'), {{ type:'doughnut', data:{{ labels:{json.dumps(list(category_counts.keys()))}, datasets:[{{data:{json.dumps(list(category_counts.values()))}, backgroundColor:['#e74c3c','#f1c40f','#2ecc71']}}] }}, options:{{plugins:{{legend:{{position:'bottom'}}}}}} }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_output)
