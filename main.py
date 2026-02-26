import urllib.request
import urllib.parse
import json
import datetime
import time

def get_pubmed_data(query, limit=7): # 뱃지 달린 걸 찾기 위해 7개로 여유있게 가져옵니다
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

# 1. 빅데이터 트렌드
big_trend_ids, big_trend_data = get_pubmed_data("Gastroenterology OR Hepatology OR Pancreas OR Endoscopy", limit=100)
big_titles = [big_trend_data.get(pid, {}).get('title', '') for pid in big_trend_ids]
time.sleep(1)

# 2. 분과별 데일리 브리핑 (스마트 태깅 포함)
categories = {
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas)": "Pancreas OR Biliary"
}

sections_html = ""
category_counts = {} 

for name, query in categories.items():
    ids, data = get_pubmed_data(query, limit=5)
    category_counts[name.split(" ")[1]] = len(ids) 
    
    papers_html = ""
    for pid in ids:
        info = data.get(pid, {})
        t_en = info.get('title', 'No Title')
        d = info.get('pubdate', 'Recent')
        
        # [핵심] 임상 중요도 자동 태깅 (뱃지 생성)
        badge = ""
        t_lower = t_en.lower()
        if "randomized" in t_lower or "rct" in t_lower: 
            badge = "<span style='background:#e74c3c; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle; box-shadow:0 0 5px #e74c3c;'>RCT</span>"
        elif "meta-analysis" in t_lower or "systematic" in t_lower:
            badge = "<span style='background:#9b59b6; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle; box-shadow:0 0 5px #9b59b6;'>Meta-Analysis</span>"
        elif "guideline" in t_lower or "consensus" in t_lower:
            badge = "<span style='background:#f1c40f; color:#2c3e50; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle; font-weight:bold; box-shadow:0 0 5px #f1c40f;'>Guideline</span>"
        elif "review" in t_lower:
            badge = "<span style='background:#3498db; color:white; padding:2px 6px; border-radius:4px; font-size:0.7em; margin-left:8px; vertical-align:middle;'>Review</span>"

        papers_html += f"""
        <div style="background:rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); margin-bottom:12px; padding:15px; border-radius:10px; border-left:4px solid #00d2ff; transition: all 0.3s ease;">
            <small style="color:#00d2ff; font-weight:bold;">📅 {d}</small> {badge}<br>
            <a href="https://pubmed.ncbi.nlm.nih.gov/{pid}/" target="_blank" style="text-decoration:none; color:#e0e0e0; font-weight:bold; font-size:1.05em; line-height:1.4; display:inline-block; margin-top:8px;">{t_en}</a>
        </div>"""
    sections_html += f"<div style='margin-bottom: 25px;'><h3 style='color:#fff; margin-top:10px; border-bottom:1px solid #333; padding-bottom:10px;'>{name}</h3>{papers_html}</div>"
    time.sleep(1)

time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
big_titles_json = json.dumps(big_titles)
category_counts_json = json.dumps(category_counts)

# --- HTML (다크 모드 & 글래스모피즘 디자인) ---
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Intelligence Terminal</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Apple SD Gothic Neo', 'Consolas', sans-serif; background-color:#0f172a; color:#cbd5e1; margin:0; padding:20px; line-height:1.6; }}
        .container {{ max-width: 1100px; margin: auto; }}
        /* 글래스모피즘 (유리 질감) 스타일 */
        .glass-panel {{ background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 25px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5); }}
        header {{ text-align:center; padding:40px; margin-bottom:30px; }}
        .grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px; }}
        h2 {{ color:#38bdf8; font-size:1.2em; margin-top:0; letter-spacing: 1px; text-transform: uppercase; }}
        a:hover {{ color: #38bdf8 !important; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header class="glass-panel">
            <h1 style="margin:0; font-size:2.5em; color:#fff; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);">GI INTELLIGENCE TERMINAL</h1>
            <p style="color:#94a3b8; font-size:1.1em; margin-top:10px;">Automated PubMed Scraping & Trend Analysis Board</p>
            <div style="margin-top:20px;"><span style="background:rgba(56, 189, 248, 0.2); color:#38bdf8; padding:6px 18px; border-radius:20px; border: 1px solid #38bdf8; font-family:monospace;">SYS.UPDATE: {time_label} KST</span></div>
        </header>

        <div class="grid">
            <div class="glass-panel">
                <h2>📈 Keyword Frequency (Last 100)</h2>
                <div style="position: relative; height:280px; width:100%;">
                    <canvas id="barChart"></canvas>
                </div>
            </div>
            
            <div class="glass-panel">
                <h2>🍩 Sector Activity</h2>
                <div style="position: relative; height:280px; width:100%; display:flex; justify-content:center;">
                    <canvas id="doughnutChart"></canvas>
                </div>
            </div>
        </div>

        <div class="glass-panel">
            <h2>📑 Daily Filtered Publications</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">
                {sections_html}
            </div>
        </div>

        <footer class="glass-panel" style="margin-top:30px; border-left: 5px solid #a855f7;">
            <h3 style="color:#c084fc; margin-top:0;">🚀 MedProductive: Prompt of the Day</h3>
            <p style="font-size: 0.9em; color:#94a3b8;">전공의 퇴원요약지 작성 자동화를 위한 GPT 프롬프트 (복사해서 사용하세요)</p>
            <div style="background:#000; padding:15px; border-radius:8px; font-family:monospace; color:#10b981; font-size:0.9em; overflow-x:auto;">
                > System: 당신은 소화기내과 전문의입니다.<br>
                > User: 다음 EMR 경과기록을 바탕으로 SOAP 형식의 간결한 퇴원요약지를 작성해 줘. 주요 랩 수치(Hb, AST/ALT)의 변화 추이를 반드시 포함할 것.
            </div>
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

        // 다크 모드 차트 설정
        Chart.defaults.font.family = "'Apple SD Gothic Neo', 'Consolas', sans-serif";
        Chart.defaults.color = '#94a3b8';

        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Frequency',
                    data: dataValues,
                    backgroundColor: 'rgba(56, 189, 248, 0.8)',
                    borderColor: '#38bdf8',
                    borderWidth: 1,
                    borderRadius: 4
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ 
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, 
                    y: {{ grid: {{ display: false }} }} 
                }}
            }}
        }});

        new Chart(document.getElementById('doughnutChart'), {{
            type: 'doughnut',
            data: {{
                labels: Object.keys(categoryCounts),
                datasets: [{{
                    data: Object.values(categoryCounts),
                    backgroundColor: ['#f43f5e', '#eab308', '#10b981'], 
                    borderWidth: 0,
                    hoverOffset: 10
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }}
            }}
        }});
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
