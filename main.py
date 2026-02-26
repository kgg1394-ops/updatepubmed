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
            
            abstract_full = "<br><br>".join(abstract_parts) if abstract_parts else "<span style='color:#999; font-style:italic;'>초록(Abstract)이 원문에 제공되지 않은 논문입니다.</span>"
            
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

# 1. 빅데이터 트렌드 수집
big_titles = get_pubmed_json("Gastroenterology OR Hepatology OR Pancreas OR Endoscopy", limit=100)
time.sleep(1)

# 2. 데일리 브리핑 수집
categories = {
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas)": "Pancreas OR Biliary Tract"
}

sections_html = ""
category_counts = {}

for name, query in categories.items():
    papers = get_pubmed_xml_with_abstract(query, limit=5)
    category_counts[name.split(" ")[1]] = len(papers)
    papers_html = ""
    for p in papers:
        badge = ""
        t_lower = p['title'].lower()
        if "randomized" in t_lower or "rct" in t_lower: 
            badge = "<span style='background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>RCT</span>"
        elif "meta-analysis" in t_lower or "systematic" in t_lower:
            badge = "<span style='background:#9b59b6; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Meta-Analysis</span>"
        elif "guideline" in t_lower or "consensus" in t_lower:
            badge = "<span style='background:#2ecc71; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Guideline</span>"
        elif "review" in t_lower:
            badge = "<span style='background:#3498db; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Review</span>"

        is_top = any(top in p['journal'].lower() for top in TOP_JOURNALS)
        top_badge = "<span style='background:#f1c40f; color:#2c3e50; padding:3px 8px; border-radius:12px; font-size:0.7em; margin-right:10px; font-weight:bold; box-shadow:0 1px 3px rgba(0,0,0,0.1);'>👑 Top Journal</span>" if is_top else ""
        
        papers_html += f"""
        <details style="background:#fff; border: 1px solid #e0e0e0; margin-bottom:15px; border-radius:12px; border-left:4px solid #3498db; overflow:hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.02); transition: all 0.2s;">
            <summary style="padding:15px; cursor:pointer; font-weight:bold; color:#2c3e50; font-size:1.05em; outline:none; display:flex; flex-direction:column;">
                <div style="margin-bottom:8px; font-size:0.85em; color:#7f8c8d; font-weight:normal;">
                    {top_badge} 📅 {p['year']} &nbsp;|&nbsp; 📖 <i style="color:#3498db;">{p['journal']}</i> {badge}
                </div>
                <div style="line-height:1.4;">
                    <span style="color:#3498db; font-size:0.9em; margin-right:8px;">▶</span>{p['title']}
                </div>
            </summary>
            <div style="padding:20px; background:#f8f9fa; border-top: 1px solid #eee; font-size:0.95em; color:#555; line-height:1.7;">
                {p['abstract']}<br><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" target="_blank" style="display:inline-block; background:#3498db; color:white; padding:6px 15px; border-radius:6px; text-decoration:none; font-weight:bold; font-size:0.9em;">🔗 PubMed 원문 보기</a>
            </div>
        </details>
        """
    sections_html += f"<div style='margin-bottom: 35px;'><h3 style='color:#2c3e50; margin-top:0; border-bottom:2px solid #eee; padding-bottom:10px; font-size:1.3em;'>{name}</h3>{papers_html}</div>"
    time.sleep(1)

time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
big_titles_json = json.dumps(big_titles)
category_counts_json = json.dumps(category_counts)

# --- HTML ---
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Intelligence Terminal</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', sans-serif; background-color:#f5f7fa; color:#333; margin:0; padding:20px; }}
        .container {{ max-width: 1050px; margin: auto; }}
        .card {{ background: #fff; border-radius: 16px; padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.04); border: 1px solid #e0e0e0; margin-bottom: 25px; }}
        header {{ text-align:center; margin-bottom:30px; }}
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 25px; margin-bottom: 25px; }}
        h1 {{ margin:0; font-size:2.2em; color:#2c3e50; }}
        h2 {{ color:#2c3e50; font-size:1.2em; margin-top:0; border-bottom: 2px solid #f0f4f7; padding-bottom: 12px; }}
        details > summary::-webkit-details-marker {{ display: none; }}
        details[open] summary span:first-child {{ transform: rotate(90deg); display: inline-block; transition: 0.2s; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header class="card">
            <h1>🏥 GI Intelligence Terminal</h1>
            <p style="color:#7f8c8d; font-size:1.1em; margin-top:5px;">의료 현장을 위한 초고속 논문 스캐너 & 트렌드 분석기</p>
            <div style="margin-top:15px;"><span style="background:#ebf5ff; color:#3498db; padding:6px 18px; border-radius:20px; font-weight:bold; font-size:0.9em;">Update: {time_label} (KST)</span></div>
        </header>

        <div class="grid">
            <div class="card" style="margin-bottom: 0;">
                <h2>📈 Keyword Frequency (Last 100)</h2>
                <div style="position:relative; height:250px; width:100%;"><canvas id="barChart"></canvas></div>
            </div>
            
            <div class="card" style="margin-bottom: 0;">
                <h2>🍩 Sector Activity</h2>
                <div style="position:relative; height:250px; width:100%; display:flex; justify-content:center;"><canvas id="doughnutChart"></canvas></div>
            </div>
        </div>

        <div class="card">
            <h2>📑 Today's Clinical Papers</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                {sections_html}
            </div>
        </div>

        <footer class="card" style="text-align:center;">
            <h3 style="color:#2c3e50; margin-top:0; margin-bottom:10px;">🚀 Project: MedProductive</h3>
            <p style="color:#7f8c8d; margin:0; font-size:0.95em;">의료 현장의 비효율을 AI로 해결합니다.</p>
        </footer>
    </div>

    <script>
        const titles = {big_titles_json};
        const categoryCounts = {category_counts_json};
        
        const stopWords = ["the","of","and","a","in","to","for","with","on","as","by","an","is","at","from","study","clinical","trial","patient","patients","treatment","analysis","results","using","versus","vs","comparing","compared","comparison","relation","relationship","between","among","after","during","before","diagnostic","diagnosis","probe","targeted","target","healthy","accuracy","specific","quantitative","implications","evidence","predict","predicting","predictive","takes","fractions","methodological","interpretative","considerations","retrospective","prospective","cohort","multicenter","impact","yield","survival","outcomes","outcome","associated","association","risk","factors","factor","development","validation","model","models","efficacy","safety","systematic","review","meta-analysis","disease","diseases","case","report","system","role","effect","effects","evaluation","evaluating","based","new","novel","approach","approaches","management","use","utility","changes","expression","levels","level","related","group","groups","high","low","significant","significance","increase","decreased","increased","decrease","activity","therapy","therapies","characteristics","features","human","mice","mouse","cell","cells","protein","proteins","gene","genes","pathway","pathways","mechanism","mechanisms","type","types","data","methods","method","conclusion","conclusions","background","objective","aim","introduction","through","which","that","this","these","those"];
        
        const words = titles.join(" ").toLowerCase().replace(/[.,/#!$%^&*;:{{}}==_`~()?'"]/g,"").split(/\\s+/);
        const freqMap = {{}};
        words.forEach(w => {{ if(w.length > 3 && !stopWords.includes(w)) freqMap[w] = (freqMap[w] || 0) + 1; }});
        
        const sortedWords = Object.entries(freqMap).sort((a,b) => b[1] - a[1]).slice(0, 10);
        
        Chart.defaults.font.family = "'Apple SD Gothic Neo', sans-serif";
        Chart.defaults.color = '#7f8c8d';

        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: sortedWords.map(item => item[0].toUpperCase()),
                datasets: [{{
                    data: sortedWords.map(item => item[1]),
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
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

        new Chart(document.getElementById('doughnutChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(categoryCounts),
                datasets: [{{
                    data: Object.values(categoryCounts),
                    backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71'], 
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {{ legend: {{ position: 'bottom' }} }}
            }}
        }});
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
