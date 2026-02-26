import urllib.request
import urllib.parse
import json
import datetime
import time
import re
import xml.etree.ElementTree as ET

# 👑 메이저 저널 및 IF 데이터 (기본 유지)
TOP_JOURNALS = ["gastroenterology", "gut", "hepatology", "endoscopy", "clinical gastroenterology and hepatology", "journal of hepatology", "american journal of gastroenterology", "gastrointestinal endoscopy", "lancet gastroenterology & hepatology", "nature reviews gastroenterology & hepatology"]
JOURNAL_IF = {"nature reviews gastroenterology & hepatology": 65.1, "lancet gastroenterology & hepatology": 35.7, "gastroenterology": 29.4, "journal of hepatology": 26.8, "gut": 24.5, "hepatology": 13.5, "clinical gastroenterology and hepatology": 11.6, "american journal of gastroenterology": 10.2, "endoscopy": 9.3, "gastrointestinal endoscopy": 7.7}

def get_pubmed_json(query, limit=5):
    encoded = urllib.parse.quote(query)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&sort=date&retmode=json"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as res:
            ids = json.loads(res.read().decode('utf-8')).get('esearchresult', {}).get('idlist', [])
        if not ids: return []
        time.sleep(0.5)
        sum_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        with urllib.request.urlopen(urllib.request.Request(sum_url, headers={'User-Agent': 'Mozilla/5.0'})) as res:
            data = json.loads(res.read().decode('utf-8')).get('result', {})
            return [data.get(pid, {}).get('title', '') for pid in ids]
    except: return []

def get_pubmed_xml_with_abstract(query, limit=5):
    encoded = urllib.parse.quote(query)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded}&retmax={limit}&sort=date&retmode=json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            ids = json.loads(res.read().decode('utf-8')).get('esearchresult', {}).get('idlist', [])
        if not ids: return []
        time.sleep(1)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
        req_fetch = urllib.request.Request(fetch_url, headers=headers)
        with urllib.request.urlopen(req_fetch) as res:
            root = ET.fromstring(res.read())
        papers = []
        for article in root.findall('.//PubmedArticle'):
            pmid = article.find('.//PMID').text if article.find('.//PMID') is not None else ""
            title = article.find('.//ArticleTitle').text if article.find('.//ArticleTitle') is not None else "No Title"
            journal = article.find('.//Title').text if article.find('.//Title') is not None else "Unknown Journal"
            abstract_parts = []
            bottom_line = ""
            for abs_text in article.findall('.//AbstractText'):
                label = abs_text.get('Label', '')
                text = abs_text.text if abs_text.text else ''
                if label:
                    abstract_parts.append(f"<b style='color:#3498db;'>{label}:</b> {text}")
                    if label.lower() in ['conclusion', 'conclusions']: bottom_line = text
                else:
                    abstract_parts.append(text)
                    match = re.search(r'(?i)(?:conclusion|conclusions)s?[:.]\s*(.*)', text)
                    if match: bottom_line = match.group(1)
            papers.append({"pmid": pmid, "title": title, "journal": journal, "abstract": "<br><br>".join(abstract_parts), "bottom_line": bottom_line, "year": "Recent"})
        return papers
    except: return []

# 데이터 수집
big_titles = get_pubmed_json("Gastroenterology OR Hepatology", limit=100)
categories = {"🍎 GI": "Gastrointestinal Diseases", "🍺 Liver": "Hepatology", "🧬 Pancreas": "Pancreas OR Biliary Tract"}
sections_html = ""
category_counts = {}

for name, query in categories.items():
    # 필터 기능을 위해 조금 더 넉넉하게(10개) 가져옵니다.
    papers = get_pubmed_xml_with_abstract(query, limit=10)
    category_counts[name.split(" ")[1]] = len(papers)
    papers_html = ""
    for p in papers:
        t_lower = p['title'].lower()
        is_guideline = any(kw in t_lower for kw in ["guideline", "consensus", "recommendation"])
        badge = ""
        if "randomized" in t_lower or "rct" in t_lower: badge = "<span class='type-badge' style='background:#e74c3c; color:white;'>RCT</span>"
        elif "meta-analysis" in t_lower: badge = "<span class='type-badge' style='background:#9b59b6; color:white;'>Meta</span>"
        elif is_guideline: badge = "<span class='type-badge badge-guideline' style='background:#2ecc71; color:white;'>Guideline</span>"
        
        j_lower = p['journal'].lower()
        top_badge = "<span class='top-badge'>👑 Top</span>" if any(top in j_lower for top in TOP_JOURNALS) else ""
        if_badge = ""
        if_val = ""
        for j_n, score in JOURNAL_IF.items():
            if j_n in j_lower:
                if_badge = f"<span class='if-badge'>IF {score}</span>"
                if_val = f" (IF: {score})"
                break

        bottom_line_html = f"<div class='bottom-line-box'><b>💡 Bottom Line</b><br><div>{p['bottom_line']}</div></div>" if p['bottom_line'] else ""
        share_content = f"📄 [논문 공유]\\n📌 제목: {p['title']}\\n📖 저널: {p['journal']}{if_val}\\n💡 결론: {p['bottom_line'] if p['bottom_line'] else '원문 참조'}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"

        papers_html += f"""
        <details class="paper-item">
            <summary>
                <div class="meta-row">{top_badge}{if_badge}<span>📖 <i>{p['journal']}</i></span> {badge}</div>
                <div class="title-row"><span class="arrow-icon">▶</span>{p['title']}</div>
            </summary>
            <div class="content-box">
                {bottom_line_html} {p['abstract']}<br><br>
                <div class="btn-group">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" class="btn btn-pubmed">🔗 PubMed</a>
                    <button onclick="copyToClipboard('share_{p['pmid']}')" class="btn btn-share">📤 공유</button>
                </div>
                <textarea id="share_{p['pmid']}" style="display:none;">{share_content}</textarea>
            </div>
        </details>
        """
    sections_html += f"<div class='section-group'><h3>{name}</h3>{papers_html}</div>"

# --- HTML (모바일 최적화 CSS 탑재) ---
time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0">
    <title>GI Intelligence</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --primary: #3498db; --success: #2ecc71; --bg: #f5f7fa; --text: #2c3e50; }}
        body {{ font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 10px; }}
        .container {{ max-width: 1000px; margin: auto; }}
        .card {{ background: #fff; border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 15px; border: 1px solid #e0e0e0; }}
        header h1 {{ font-size: 1.5rem; margin: 0; color: var(--text); }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 15px; }}
        @media (min-width: 768px) {{ .grid {{ grid-template-columns: 2fr 1fr; }} .card {{ padding: 25px; }} header h1 {{ font-size: 2rem; }} }}
        
        /* 논문 아이템 스타일 */
        .paper-item {{ background: #fff; border: 1px solid #eee; margin-bottom: 10px; border-radius: 10px; border-left: 4px solid var(--primary); overflow: hidden; }}
        summary {{ padding: 12px; cursor: pointer; list-style: none; outline: none; }}
        summary::-webkit-details-marker {{ display: none; }}
        .meta-row {{ font-size: 0.75rem; color: #7f8c8d; display: flex; align-items: center; gap: 5px; margin-bottom: 5px; flex-wrap: wrap; }}
        .title-row {{ font-weight: bold; font-size: 0.95rem; line-height: 1.4; }}
        .arrow-icon {{ display: inline-block; transition: transform 0.2s; color: var(--primary); margin-right: 5px; }}
        details[open] .arrow-icon {{ transform: rotate(90deg); }}
        
        /* 뱃지 스타일 */
        .type-badge {{ padding: 2px 5px; border-radius: 4px; font-size: 0.65rem; }}
        .top-badge {{ background: #f1c40f; color: #000; padding: 2px 6px; border-radius: 10px; font-weight: bold; font-size: 0.65rem; }}
        .if-badge {{ background: #8e44ad; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.65rem; }}
        
        /* 내용 및 버튼 */
        .content-box {{ padding: 15px; background: #f9f9f9; border-top: 1px solid #eee; font-size: 0.9rem; line-height: 1.6; }}
        .bottom-line-box {{ background: #ebf5ff; padding: 12px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid var(--primary); font-weight: bold; }}
        .btn-group {{ display: flex; gap: 10px; margin-top: 15px; }}
        .btn {{ flex: 1; padding: 10px; border-radius: 6px; text-align: center; text-decoration: none; font-weight: bold; font-size: 0.85rem; border: none; cursor: pointer; }}
        .btn-pubmed {{ background: var(--primary); color: #fff; }}
        .btn-share {{ background: var(--success); color: #fff; }}
        
        /* 필터 버튼 */
        .filter-btn {{ width: 100%; padding: 10px; border-radius: 20px; border: 2px solid var(--success); background: #fff; color: var(--success); font-weight: bold; margin-bottom: 15px; cursor: pointer; }}
        .filter-btn.active {{ background: var(--success); color: #fff; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="card" style="text-align:center;">
            <h1>🏥 GI Intel Terminal</h1>
            <div style="margin-top:10px;"><span style="background:#ebf5ff; color:var(--primary); padding:4px 12px; border-radius:15px; font-size:0.8rem; font-weight:bold;">Update: {time_label}</span></div>
        </header>

        <div class="grid">
            <div class="card"><canvas id="barChart" style="max-height:200px;"></canvas></div>
            <div class="card"><canvas id="doughnutChart" style="max-height:200px;"></canvas></div>
        </div>

        <div class="card">
            <button id="btn-filter-guideline" class="filter-btn" onclick="toggleGuidelineFilter()">📋 가이드라인만 보기</button>
            <div id="sections-container">{sections_html}</div>
        </div>

        <footer style="text-align:center; padding: 20px; color: #95a5a6; font-size: 0.8rem;">
            <p>🚀 Project: MedProductive<br>의료 현장의 비효율을 AI로 해결합니다.</p>
        </footer>
    </div>

    <script>
        function toggleGuidelineFilter() {{
            const btn = document.getElementById('btn-filter-guideline');
            const papers = document.querySelectorAll('.paper-item');
            const sections = document.querySelectorAll('.section-group');
            btn.classList.toggle('active');
            const isFilter = btn.classList.contains('active');
            
            papers.forEach(p => {{
                const isG = p.querySelector('.badge-guideline');
                p.style.display = isFilter ? (isG ? 'block' : 'none') : 'block';
            }});
            sections.forEach(s => {{
                const hasVisible = Array.from(s.querySelectorAll('.paper-item')).some(p => p.style.display !== 'none');
                s.style.display = hasVisible ? 'block' : 'none';
            }});
        }}

        function copyToClipboard(id) {{
            const el = document.getElementById(id);
            const val = el.value.replace(/\\\\n/g, '\\n');
            navigator.clipboard.writeText(val).then(() => alert("✅ 공유용 텍스트가 복사되었습니다!"));
        }}

        const labels = {json.dumps(list(category_counts.keys()))};
        const counts = {json.dumps(list(category_counts.values()))};
        
        new Chart(document.getElementById('barChart'), {{ type: 'bar', data: {{ labels: labels, datasets: [{{ label: 'Papers', data: counts, backgroundColor: '#3498db' }}] }}, options: {{ indexAxis: 'y', plugins: {{ legend: {{ display: false }} }} }} }});
        new Chart(document.getElementById('doughnutChart'), {{ type: 'doughnut', data: {{ labels: labels, datasets: [{{ data: counts, backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71'] }}] }}, options: {{ plugins: {{ legend: {{ position: 'bottom' }} }} }} }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)
