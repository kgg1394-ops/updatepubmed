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

# --- 데이터 수집 ---
big_trend_ids, big_trend_data = get_pubmed_data("Gastroenterology OR Hepatology OR Pancreas OR Endoscopy", limit=100)
big_titles = [big_trend_data.get(pid, {}).get('title', '') for pid in big_trend_ids]
time.sleep(1)

categories = {
    "🍎 위장관 (GI)": "Gastrointestinal Diseases",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas & Biliary)": "Pancreas OR Biliary"
}

sections_html = ""
daily_titles = []

for name, query in categories.items():
    ids, data = get_pubmed_data(query, limit=3)
    papers_html = ""
    for pid in ids:
        info = data.get(pid, {})
        t_en = info.get('title', 'No Title')
        daily_titles.append(t_en)
        d = info.get('pubdate', 'Recent')
        papers_html += f"""
        <div style="background:white; margin-bottom:10px; padding:12px; border-radius:8px; border-left:4px solid #3498db; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
            <small style="color:#3498db;">📅 {d}</small><br>
            <a href="https://pubmed.ncbi.nlm.nih.gov/{pid}/" target="_blank" style="text-decoration:none; color:#2c3e50; font-weight:bold; font-size:0.9em;">{t_en}</a>
        </div>"""
    sections_html += f"<h3>{name}</h3>{papers_html}"
    time.sleep(1)

# --- 시간 및 JSON 변환 ---
time_label = (datetime.datetime.now() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")
big_titles_json = json.dumps(big_titles)
daily_titles_json = json.dumps(daily_titles)

# --- HTML 템플릿 (금지어 사전 대폭 강화) ---
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Professional Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/wordcloud@1.2.2/src/wordcloud2.min.js"></script>
    <style>
        body {{ font-family: sans-serif; background:#f4f7f6; color:#333; margin:0; padding:20px; }}
        .container {{ max-width: 1000px; margin: auto; }}
        header {{ text-align:center; padding:30px; background:white; border-radius:15px; box-shadow:0 2px 10px rgba(0,0,0,0.05); margin-bottom:20px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .card {{ background:white; padding:20px; border-radius:15px; box-shadow:0 2px 10px rgba(0,0,0,0.05); }}
        h2 {{ color:#2c3e50; border-bottom:2px solid #3498db; padding-bottom:10px; font-size:1.2em; }}
        canvas {{ width: 100%; height: 250px; }}
        @media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1 style="margin:0;">🏥 GI/Liver/Biliary Trend Portal</h1>
            <p style="color:#7f8c8d; margin:10px 0;">최신 논문 빅데이터 기반 트렌드 분석</p>
            <small style="background:#34495e; color:white; padding:5px 15px; border-radius:20px;">Last Update: {time_label} (KST)</small>
        </header>

        <div class="grid">
            <div class="card">
                <h2>📈 Macro Trend (Last 100 Papers)</h2>
                <p style="font-size:0.8em; color:#999;">소화기 전체 분야의 거시적 흐름</p>
                <canvas id="canvas-big"></canvas>
            </div>
            <div class="card">
                <h2>🔥 Daily Hot Topics</h2>
                <p style="font-size:0.8em; color:#999;">오늘 수집된 주요 논문 내 핵심 키워드</p>
                <canvas id="canvas-daily"></canvas>
            </div>
        </div>

        <div class="card" style="margin-top:20px;">
            <h2>📄 Latest Research Briefing</h2>
            <div class="grid">
                {sections_html}
            </div>
        </div>

        <footer style="margin-top:40px; text-align:center; padding:30px; background:#2c3e50; color:white; border-radius:15px;">
            <h3>🚀 MedProductive Project</h3>
            <p>의료 생산성 혁신을 위한 AI 시스템을 구축합니다.</p>
        </footer>
    </div>

    <script>
        // 선생님의 피드백을 반영하여 쓸데없는 연구 용어들을 싹 다 쳐냈습니다!
        const stopWords = [
            "the", "of", "and", "a", "in", "to", "for", "with", "on", "as", "by", "an", "is", "at", "from", 
            "study", "clinical", "trial", "patient", "patients", "treatment", "analysis", "results", "using", 
            "versus", "vs", "comparing", "compared", "comparison", "relation", "relationship", "between", "among", 
            "after", "during", "before", "diagnostic", "diagnosis", "probe", "targeted", "target", "healthy", 
            "accuracy", "specific", "quantitative", "implications", "evidence", "predict", "predicting", "predictive", 
            "takes", "fractions", "methodological", "interpretative", "considerations", "retrospective", "prospective", 
            "cohort", "multicenter", "impact", "yield", "survival", "outcomes", "outcome", "associated", "association", 
            "risk", "factors", "factor", "development", "validation", "model", "models", "efficacy", "safety", 
            "systematic", "review", "meta-analysis", "disease", "diseases", "case", "report", "system", "role", 
            "effect", "effects", "evaluation", "evaluating", "based", "new", "novel", "approach", "approaches", 
            "management", "use", "utility", "changes", "expression", "levels", "level", "related", "group", "groups", 
            "high", "low", "significant", "significance", "increase", "decreased", "increased", "decrease", "activity", 
            "therapy", "therapies", "characteristics", "features", "human", "mice", "mouse", "cell", "cells", 
            "protein", "proteins", "gene", "genes", "pathway", "pathways", "mechanism", "mechanisms", "type", "types", 
            "data", "methods", "method", "conclusion", "conclusions", "background", "objective", "aim", "introduction",
            "through", "which", "that", "this", "these", "those"
        ];
        
        function drawCloud(canvasId, titles, color) {{
            // 특수문자 제거 및 소문자 변환
            const words = titles.join(" ").toLowerCase().replace(/[.,/#!$%^&*;:{{}}==_`~()?'"]/g,"").split(/\s+/);
            const freqMap = {{}};
            
            words.forEach(w => {{
                // 길이가 3자 이하이거나 금지어 사전에 있는 단어는 무시
                if (w.length > 3 && !stopWords.includes(w)) {{
                    freqMap[w] = (freqMap[w] || 0) + 1;
                }}
            }});
            
            // 빈도수 기반 크기 설정
            const list = Object.entries(freqMap).map(([t, s]) => [t, s * 8]);
            
            WordCloud(document.getElementById(canvasId), {{ 
                list: list, 
                color: color, 
                backgroundColor: '#fff', 
                weightFactor: 1.2, 
                rotateRatio: 0.3,
                minSize: 8 // 너무 작은 단어는 그리지 않음
            }});
        }}

        drawCloud('canvas-big', {big_titles_json}, '#2c3e50');
        drawCloud('canvas-daily', {daily_titles_json}, '#e74c3c'); // Daily는 눈에 띄게 붉은 계열로 변경
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
