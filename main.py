import urllib.request
import urllib.parse
import json
import datetime
import time
import xml.etree.ElementTree as ET

# 👑 세계 최고 권위 소화기/간 저널 리스트
TOP_JOURNALS = [
    "gastroenterology", "gut", "hepatology", "endoscopy", 
    "clinical gastroenterology and hepatology", "journal of hepatology", 
    "american journal of gastroenterology", "gastrointestinal endoscopy", 
    "lancet gastroenterology & hepatology", "nature reviews gastroenterology & hepatology"
]

# [기능 1] 트렌드 분석용 제목 수집 (JSON)
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
    except:
        return []

# [기능 2] 실전용: 초록(Abstract) 포함 XML 데이터 수집
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
            xml_data = res.read()
            root = ET.fromstring(xml_data)
            
        papers = []
        for article in root.findall('.//PubmedArticle'):
            pmid = article.find('.//PMID').text if article.find('.//PMID') is not None else ""
            title = article.find('.//ArticleTitle').text if article.find('.//ArticleTitle') is not None else "No Title"
            
            journal_node = article.find('.//Title')
            journal = journal_node.text if journal_node is not None else "Unknown Journal"
            
            abstract_parts = []
            for abs_text in article.findall('.//AbstractText'):
                label = abs_text.get('Label', '')
                text = abs_text.text if abs_text.text else ''
                if label:
                    abstract_parts.append(f"<b style='color:#3498db;'>{label}:</b> {text}")
                else:
                    abstract_parts.append(text)
            
            abstract_full = "<br><br>".join(abstract_parts) if abstract_parts else "<span style='color:#7f8c8d; font-style:italic;'>초록(Abstract)이 원문에 제공되지 않은 논문입니다.</span>"
            
            pub_date = article.find('.//PubDate')
            year = pub_date.find('Year').text if pub_date is not None and pub_date.find('Year') is not None else "Recent"
            
            papers.append({
                "pmid": pmid, "title": title, "journal": journal, 
                "abstract": abstract_full, "year": year
            })
        return papers
    except Exception as e:
        print(f"Error XML: {e}")
        return []

# --- 데이터 수집 실행 ---
big_titles = get_pubmed_json("Gastroenterology OR Hepatology OR Pancreas OR Endoscopy", limit=100)
time.sleep(1)

categories = {
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas)": "Pancreas OR Biliary Tract"
}

sections_html = ""
for name, query in categories.items():
    papers = get_pubmed_xml_with_abstract(query, limit=5)
    papers_html = ""
    for p in papers:
        is_top = any(top in p['journal'].lower() for top in TOP_JOURNALS)
        top_badge = "<span style='background:#f1c40f; color:#2c3e50; padding:3px 8px; border-radius:12px; font-size:0.7em; margin-right:10px; font-weight:bold; box-shadow:0 1px 3px rgba(0,0,0,0.1);'>👑 Top Journal</span>" if is_top else ""
        
        # 화이트 테마용 아코디언 스타일 적용
        papers_html += f"""
        <details style="background:#fff; border: 1px solid #e0e0e0; margin-bottom:15px; border-radius:12px; border-left:4px solid #3498db; overflow:hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">
            <summary style="padding:15px; cursor:pointer; font-weight:bold; color:#2c3e50; font-size:1.05em; outline:none; display:flex; flex-direction:column;">
                <div style="margin-bottom:8px; font-size:0.85em; color:#7f8c8d; font-weight:normal;">
                    {top_badge} 📅 {p['year']} &nbsp;|&nbsp; 📖 <i style="color:#3498db;">{p['journal']}</i>
                </div>
                <div style="line-height:1.4;">
                    <span style="color:#3498db; font-size:0.9em; margin-right:8px;">▶</span>{p['title']}
                </div>
            </summary>
            <div style="padding:20px; background:#f8f9fa; border-top: 1px solid #eee; font-size:0.95em; color:#555; line-height:1.7;">
                {p['abstract']}<br><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" style="display:inline-block; background:#3498db; color:white; padding:6px 15px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:0.9em; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">🔗 PubMed 원문 보기</a>
            </div>
        </details>
        """
    sections_html += f"<div style='margin-bottom: 35px;'><h3 style='color:#2c3e50; margin-top:0; border-bottom:2px solid #eee; padding-bottom:10px; font-size:1.3em;'>{name}</h3>{papers_html}</div>"
    time.sleep(1)

time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
big_titles_json = json.dumps(big_titles)

# --- HTML (화이트 테마 적용) ---
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Abstract Scanner</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', sans-serif; background-color:#f5f7fa; color:#333; margin:0; padding:20px; }}
        .container {{ max-width: 1000px; margin: auto; }}
        /* 화이트 카드 스타일 */
        .card {{ background: #fff; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }}
        header {{ text-align:center; margin-bottom:30px; }}
        h1 {{ margin:0; font-size:2.2em; color:#2c3e50; }}
        h2 {{ color:#2c3e50; font-size:1.2em; margin-top:0; }}
        details > summary::-webkit-details-marker {{ display: none; }}
        details[open] summary span {{ transform: rotate(90deg); display: inline-block; transition: 0.2s; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="card">
            <h1>🏥 GI Abstract Scanner</h1>
            <p style="color:#7f8c8d; font-size:1.1em; margin-top:5px;">의료 현장을 위한 초고속 논문 초록 판독기</p>
            <div style="margin-top:15px;"><span style="background:#ebf5ff; color:#3498db; padding:6px 18px; border-radius:20px; font-weight:bold; font-size:0.9em;">Update: {time_label} (KST)</span></div>
        </header>

        <div class="card" style="margin-bottom:30px; display:flex; flex-wrap:wrap; gap:30px;">
            <div style="flex:1; min-width:300px;">
                <h2>📊 Keyword Radar (Last 100)</h2>
                <div style="position:relative; height:200px; width:100%;"><canvas id="barChart"></canvas></div>
            </div>
            <div style="flex:1; min-width:300px; padding-left:20px; border-left:2px solid #eee;">
                <h2>💡 How to use</h2>
                <ul style="line-height:1.8; color:#666; font-size:0.95em;">
                    <li>제목을 <b>클릭</b>하면 페이지 이동 없이 즉시 <b style="color:#3498db;">초록(Abstract)</b>이 펼쳐집니다.</li>
                    <li><span style="background:#f1c40f; color:#2c3e50; padding:2px 6px; border-radius:4px; font-size:0.8em; font-weight:bold;">👑 Top Journal</span> 마크는 주요 학술지에만 자동 부여됩니다.</li>
                    <li>바쁜 회진 전, 핵심 논문의 결론만 빠르게 스캔하세요.</li>
                </ul>
            </div>
        </div>

        <div class="card">
            <h2 style="color:#2c3e50; font-size:1.4em; margin-top:0; border-bottom:2px solid #eee; padding-bottom:15px; margin-bottom:30px;">📑 Today's Clinical Papers</h2>
            {sections_html}
        </div>
    </div>

    <script>
        const titles = {big_titles_json};
        const stopWords = ["the","of","and","a","in","to","for","with","on","as","by","an","is","at","from","study","clinical","trial","patient","patients","treatment","analysis","results","using","versus","vs","comparing","compared","comparison","relation","relationship","between","among","after","during","before","diagnostic","diagnosis","probe","targeted","target","healthy","accuracy","specific","quantitative","implications","evidence","predict","predicting","predictive","takes","fractions","methodological","interpretative","considerations","retrospective","prospective","cohort","multicenter","impact","yield","survival","outcomes","outcome","associated","association","risk","factors","factor","development","validation","model","models","efficacy","safety","systematic","review","meta-analysis","disease","diseases","case","report","system","role","effect","effects","evaluation","evaluating","based","new","novel","approach","approaches","management","use","utility","changes","expression","levels","level","related","group","groups","high","low","significant","significance","increase","decreased","increased","decrease","activity","therapy","therapies","characteristics","features","human","mice","mouse","cell","cells","protein","proteins","gene","genes","pathway","pathways","mechanism","mechanisms","type","types","data","methods","method","conclusion","conclusions","background","objective","aim","introduction","through","which","that","this","these","those"];
        const words = titles.join(" ").toLowerCase().replace(/[.,/#!$%^&*;:{{}}==_`~()?'"]/g,"").split(/\s+/);
        const freqMap = {{}};
        words.forEach(w => {{ if(w.length > 3 && !stopWords.includes(w)) freqMap[w] = (freqMap[w] || 0) + 1; }});
        
        const sortedWords = Object.entries(freqMap).sort((a,b) => b[1] - a[1]).slice(0, 5);
        
        Chart.defaults.font.family = "'Apple SD Gothic Neo', sans-serif";
        Chart.defaults.color = '#666';

        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: sortedWords.map(item => item[0].toUpperCase()),
                datasets: [{{
                    data: sortedWords.map(item => item[1]),
                    backgroundColor: 'rgba(52, 152, 219, 0.7)', // 파란색 계열로 변경
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ x: {{ display: false }}, y: {{ grid: {{ display: false }} }} }}
            }}
        }});
    </script>
</body>
</html>
"""

이제 눈이 편안한 흰색 배경에 파란색 포인트 컬러로 정리된 깔끔한 화면을 보실 수 있습니다. 제목을 클릭해서 초록이 잘 펼쳐지는지 확인해 주세요!
