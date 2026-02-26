import urllib.request
import urllib.parse
import json
import datetime
import time
import re
import xml.etree.ElementTree as ET

# 👑 세계 최고 권위 저널 리스트 & IF 데이터 (그대로 유지)
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

# 1. 트렌드용 수집
big_titles = get_pubmed_json("Gastroenterology OR Hepatology OR Pancreas", limit=100)
time.sleep(1)

# 2. 메인 카테고리 설정 (가이드라인 전용 카테고리 '👑 Guidelines' 추가)
categories = {
    "👑 Recent Guidelines": "(Gastroenterology OR Hepatology) AND (Guideline[PT] OR Consensus Development Conference[PT] OR \"Practice Guideline\"[Title])",
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas)": "Pancreas OR Biliary Tract"
}

sections_html = ""
category_counts = {}

for name, query in categories.items():
    # 가이드라인 섹션은 좀 더 많이(10개) 긁어와서 필터링 때 확실히 보이게 합니다.
    limit_num = 10 if "Guideline" in name else 5
    papers = get_pubmed_xml_with_abstract(query, limit=limit_num)
    category_counts[name.split(" ")[-1]] = len(papers)
    
    papers_html = ""
    for p in papers:
        t_lower = p['title'].lower()
        # 가이드라인 뱃지 판독 로직 강화
        is_guideline = "guideline" in t_lower or "consensus" in t_lower or "recommendation" in t_lower
        badge = ""
        if "randomized" in t_lower or "rct" in t_lower: badge = "<span class='type-badge' style='background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>RCT</span>"
        elif "meta-analysis" in t_lower: badge = "<span class='type-badge' style='background:#9b59b6; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Meta-Analysis</span>"
        elif is_guideline: badge = "<span class='type-badge badge-guideline' style='background:#2ecc71; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Guideline</span>"
        
        j_lower = p['journal'].lower()
        is_top = any(top in j_lower for top in TOP_JOURNALS)
        top_badge = "<span style='background:#f1c40f; color:#2c3e50; padding:3px 8px; border-radius:12px; font-size:0.7em; margin-right:5px; font-weight:bold;'>👑 Top Journal</span>" if is_top else ""
        
        if_badge = ""
        if_score = ""
        for j_name, score in JOURNAL_IF.items():
            if j_name in j_lower:
                if_badge = f"<span style='background:#8e44ad; color:white; padding:2px 6px; border-radius:4px; font-size:0.75em; margin-right:10px; font-weight:bold;'>IF {score}</span>"
                if_score = f" (IF: {score})"
                break

        bottom_line_html = f"<div style='background:#ebf5ff; border-left:4px solid #3498db; padding:15px; margin-bottom:20px; border-radius:0 8px 8px 0;'><b style='color:#2c3e50;'>💡 Bottom Line</b><br><div style='font-weight:bold; margin-top:5px;'>{p['bottom_line']}</div></div>" if p['bottom_line'] else ""
        share_content = f"📄 [논문 공유]\\n📌 제목: {p['title']}\\n📖 저널: {p['journal']}{if_score}\\n💡 결론: {p['bottom_line'] if p['bottom_line'] else '원문 참조'}\\n🔗 https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"

        papers_html += f"""
        <details class="paper-item" style="background:#fff; border: 1px solid #e0e0e0; margin-bottom:15px; border-radius:12px; border-left:4px solid #3498db; overflow:hidden;">
            <summary style="padding:15px; cursor:pointer; outline:none; display:flex; flex-direction:column;">
                <div style="margin-bottom:8px; font-size:0.85em; color:#7f8c8d; display:flex; align-items:center; flex-wrap:wrap; gap:5px;">
                    {top_badge}{if_badge}<span>📖 <i style="color:#3498db;">{p['journal']}</i></span> {badge}
                </div>
                <div style="line-height:1.4; font-weight:bold; color:#2c3e50;">
                    <span class="arrow-icon" style="color:#3498db; margin-right:8px;">▶</span>{p['title']}
                </div>
            </summary>
            <div style="padding:20px; background:#f8f9fa; border-top:1px solid #eee; font-size:0.95em; color:#555; line-height:1.7;">
                {bottom_line_html} {p['abstract']}<br><br>
                <div style="display:flex; gap:10px;">
                    <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" style="background:#3498db; color:white; padding:8px 15px; border-radius:6px; text-decoration:none; font-weight:bold;">🔗 PubMed</a>
                    <button onclick="copyToClipboard('share_{p['pmid']}')" style="background:#2ecc71; color:white; padding:8px 15px; border-radius:6px; border:none; cursor:pointer; font-weight:bold;">📤 공유</button>
                </div>
                <textarea id="share_{p['pmid']}" style="display:none;">{share_content}</textarea>
            </div>
        </details>
        """
    sections_html += f"<div class='section-group' style='margin-bottom:35px;'><h3 style='color:#2c3e50; border-bottom:2px solid #eee; padding-bottom:10px;'>{name}</h3>{papers_html}</div>"

# --- HTML 템플릿 (JS 필터 로직 그대로 유지) ---
time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Intelligence Terminal</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: sans-serif; background-color:#f5f7fa; color:#333; padding:20px; }}
        .container {{ max-width: 1050px; margin: auto; }}
        .card {{ background: #fff; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #e0e0e0; margin-bottom: 25px; }}
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 25px; }}
        details > summary::-webkit-details-marker {{ display: none; }}
        .arrow-icon {{ display: inline-block; transition: transform 0.2s; }}
        details[open] summary .arrow-icon {{ transform: rotate(90deg); }}
        .filter-btn {{ background: #fff; border: 2px solid #2ecc71; color: #2ecc71; padding: 8px 20px; border-radius: 25px; cursor: pointer; font-weight: bold; }}
        .filter-btn.active {{ background: #2ecc71; color: #fff; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header class="card" style="text-align:center;">
            <h1>🏥 GI Intelligence Terminal</h1>
            <p style="color:#7f8c8d;">의료 현장을 위한 초고속 논문 스캐너 & 트렌드 분석기</p>
            <div style="margin-top:15px;"><span style="background:#ebf5ff; color:#3498db; padding:6px 18px; border-radius:20px; font-weight:bold;">Update: {time_label} KST</span></div>
        </header>
        <div class="grid">
            <div class="card"><canvas id="barChart" style="height:250px;"></canvas></div>
            <div class="card"><canvas id="doughnutChart" style="height:250px;"></canvas></div>
        </div>
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom:20px;">
                <h2 style="margin:0;">📑 Today's Clinical Papers</h2>
                <button id="btn-filter-guideline" class="filter-btn" onclick="toggleGuidelineFilter()">📋 가이드라인만 보기</button>
            </div>
            {sections_html}
        </div>
        <footer class="card" style="text-align:center;">
            <h3>🚀 Project: MedProductive</h3>
            <p style="color:#7f8c8d;">의료 현장의 비효율을 AI로 해결합니다.</p>
        </footer>
    </div>
    <script>
        let isGuidelineOnly = false;
        function toggleGuidelineFilter() {{
            isGuidelineOnly = !isGuidelineOnly;
            const btn = document.getElementById('btn-filter-guideline');
            const papers = document.querySelectorAll('.paper-item');
            const sections = document.querySelectorAll('.section-group');
            btn.classList.toggle('active');
            papers.forEach(p => {{
                p.style.display = isGuidelineOnly ? (p.querySelector('.badge-guideline') ? 'block' : 'none') : 'block';
            }});
            sections.forEach(sec => {{
                const visible = Array.from(sec.querySelectorAll('.paper-item')).some(p => p.style.display !== 'none');
                sec.style.display = visible ? 'block' : 'none';
            }});
        }}
        function copyToClipboard(id) {{
            const el = document.getElementById(id);
            const val = el.value.replace(/\\\\n/g, '\\n');
            navigator.clipboard.writeText(val).then(() => alert("✅ 복사되었습니다!"));
        }}
        // 차트 스크립트 (생략 - 기존과 동일)
        new Chart(document.getElementById('barChart'), {{ type: 'bar', data: {{ labels: {json.dumps([w.upper() for w in big_titles[:10]])}, datasets: [{{ data: [5,4,3,2,1], backgroundColor: 'rgba(52, 152, 219, 0.7)' }}] }}, options: {{ indexAxis: 'y', plugins: {{ legend: {{ display: false }} }} }} }});
        new Chart(document.getElementById('doughnutChart'), {{ type: 'doughnut', data: {{ labels: {json.dumps(list(category_counts.keys()))}, datasets: [{{ data: {json.dumps(list(category_counts.values()))}, backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71', '#3498db'] }}] }} }});
    </script>
</body>
</html>
"""
with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)
