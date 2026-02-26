import urllib.request
import urllib.parse
import json
import datetime
import time

def get_pubmed_data(query, limit=5):
    encoded_query = urllib.parse.quote(query)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmax={limit}&sort=date&retmode=json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as res:
            ids = json.loads(res.read().decode('utf-8')).get('esearchresult', {}).get('idlist', [])
        
        if not ids: return [], {}
        time.sleep(0.5)

        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        req_sum = urllib.request.Request(summary_url, headers=headers)
        with urllib.request.urlopen(req_sum) as res:
            result = json.loads(res.read().decode('utf-8')).get('result', {})
            return ids, result
    except:
        return [], {}

# 1. 빅데이터 트렌드용 (100개)
big_trend_ids, big_trend_data = get_pubmed_data("Gastroenterology OR Hepatology OR Pancreas OR Endoscopy", limit=100)
big_titles = [big_trend_data.get(pid, {}).get('title', '') for pid in big_trend_ids]
time.sleep(1)

# 2. 분과별 데일리 브리핑
categories = {
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas & Biliary)": "Pancreas OR Biliary"
}

sections_html = ""
# 인포그래픽(도넛 차트)을 위한 분과별 논문 수 카운트
category_counts = {} 

for name, query in categories.items():
    ids, data = get_pubmed_data(query, limit=5)
    category_counts[name.split(" ")[1]] = len(ids) 
    
    papers_html = ""
    for pid in ids:
        info = data.get(pid, {})
        t_en = info.get('title', 'No Title')
        d = info.get('pubdate', 'Recent')
        papers_html += f"""
        <div style="background:white; margin-bottom:12px; padding:15px; border-radius:10px; border-left:4px solid #3498db; box-shadow:0 2px 5px rgba(0,0,0,0.03); transition: transform 0.2s;">
            <small style="color:#3498db; font-weight:bold;">📅 {d}</small><br>
            <a href="https://pubmed.ncbi.nlm.nih.gov/{pid}/" target="_blank" style="text-decoration:none; color:#2c3e50; font-weight:bold; font-size:1em; line-height:1.4; display:inline-block; margin-top:5px;">{t_en}</a>
        </div>"""
    sections_html += f"<div style='margin-bottom: 20px;'><h3 style='color:#2c3e50; margin-top:30px;'><span style='background:#ebf5ff; padding:5px 10px; border-radius:8px;'>{name}</span></h3>{papers_html}</div>"
    time.sleep(1)

time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
big_titles_json = json.dumps(big_titles)
category_counts_json = json.dumps(category_counts)

# --- HTML 시작 ---
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Professional Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', sans-serif; background:#f5f7fa; color:#333; margin:0; padding:20px; line-height:1.6; }}
        .container {{ max-width: 1100px; margin: auto; }}
        header {{ text-align:center; padding:40px; background:white; border-radius:20px; box-shadow:0 4px 15px rgba(0,0,0,0.05); margin-bottom:30px; }}
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
        .card {{ background:white; padding:25px; border-radius:20px; box-shadow:0 4px 15px rgba(0,0,0,0.03); }}
        h2 {{ color:#2c3e50; border-bottom:2px solid #f0f4f7; padding-bottom:15px; font-size:1.3em; margin-top:0; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1 style="margin:0; font-size:2.2em; color:#2c3e50;">🏥 GI/Liver/Biliary Intelligence Board</h1>
            <p style="color:#7f8c8d; font-size:1.1em; margin-top:10px;">데이터 기반 소화기내과 최신 트렌드 인포그래픽</p>
            <div style="margin-top:20px;"><span style="background:#3498db; color:white; padding:6px 18px; border-radius:20px; font-weight:bold; font-size:0.9em;">Update: {time_label} KST</span></div>
        </header>

        <div class="grid">
            <div class="card">
                <h2>📊 Top 10 Research Keywords (Last 100 Papers)</h2>
                <div style="position: relative; height:300px; width:100%;">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2>🍩 Today's Publication Ratio</h2>
                <div style="position: relative; height:300px; width:100%; display:flex; justify-content:center;">
                    <canvas id="doughnutChart"></canvas>
                </div>
            </div>
        </div>

        <div class="card" style="margin-top:20px;">
            <h2>📑 Latest Research Briefing</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                {sections_html}
            </div>
        </div>

        <footer style="margin-top:40px; text-align:center; padding:40px; background:linear-gradient(135deg, #2c3e50, #34495e); color:white; border-radius:20px;">
            <h3 style="color:#3498db; margin-top:0;">🚀 Project: MedProductive</h3>
            <p style="opacity:0.9;">의료 현장의 비효율을 AI로 해결합니다.</p>
        </footer>
    </div>

    <script>
        const titles = {big_titles_json};
        const categoryCounts = {category_counts_json};
        
        const stopWords = ["the","of","and","a","in","to","for","with","on","as","by","an","is","at","from","study","clinical","trial","patient","patients","treatment","analysis","results","using","versus","vs","comparing","compared","comparison","relation","relationship","between","among","after","during","before","diagnostic","diagnosis","probe","targeted","target","healthy","accuracy","specific","quantitative","implications","evidence","predict","predicting","predictive","takes","fractions","methodological","interpretative","considerations","retrospective","prospective","cohort","multicenter","impact","yield","survival","outcomes","outcome","associated","association","risk","factors","factor","development","validation","model","models","efficacy","safety","systematic","review","meta-analysis","disease","diseases","case","report","system","role","effect","effects","evaluation","evaluating","based","new","novel","approach","approaches","management","use","utility","changes","expression","levels","level","related","group","groups","high","low","significant","significance","increase","decreased","increased","decrease","activity","therapy","therapies","characteristics","features","human","mice","mouse","cell","cells","protein","proteins","gene","genes","pathway","pathways","mechanism","mechanisms","type","types","data","methods","method","conclusion","conclusions","background","objective","aim","introduction","through","which","that","this","these","those"];
        
        const words = titles.join(" ").toLowerCase().replace(/[.,/#!$%^&*;:{{}}==_`~()?'"]/g,"").split(/\s+/);
        const freqMap = {{}};
        words.forEach(w => {{ if(w.length > 3 && !stopWords.includes(w)) freqMap[w] = (freqMap[w] || 0) + 1; }});
        
        const sortedWords = Object.entries(freqMap).sort((a,b) => b[1] - a[1]).slice(0, 10);
        const labels = sortedWords.map(item => item[0].toUpperCase());
        const dataValues = sortedWords.map(item => item[1]);

        Chart.defaults.font.family = "'Apple SD Gothic Neo', sans-serif";
        Chart.defaults.color = '#7f8c8d';

        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Mention Frequency',
                    data: dataValues,
                    backgroundColor: 'rgba(52, 152, 219, 0.7)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 1,
                    borderRadius: 5
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ x: {{ grid: {{ display: false }} }}, y: {{ grid: {{ borderDash: [5, 5] }} }} }}
            }}
        }});

        const donutLabels = Object.keys(categoryCounts);
        const donutData = Object.values(categoryCounts);
        
        new Chart(document.getElementById('doughnutChart'), {{
            type: 'doughnut',
            data: {{
                labels: donutLabels,
                datasets: [{{
                    data: donutData,
                    backgroundColor: ['#e74c3c', '#f1c40f', '#2ecc71'], 
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {{
                    legend: {{ position: 'bottom' }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

# HTML 파일 쓰기 (이 부분이 잘리면 안 됩니다!)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
