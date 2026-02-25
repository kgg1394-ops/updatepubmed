import urllib.request
import urllib.parse
import re
import datetime
import json

def get_pubmed_papers(query, limit=3):
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmax={limit}&sort=date&retmode=json"
    
    # 봇 차단을 막기 위해 일반 브라우저처럼 위장 (User-Agent 추가)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # 1. 논문 ID 검색
        req_search = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req_search) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            ids = search_data.get('esearchresult', {}).get('idlist', [])
        
        if not ids:
            return "<p style='color:#999; padding-left:20px;'>최근 검색된 논문이 없습니다.</p>"

        # 2. 논문 상세 정보 요청
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        req_summary = urllib.request.Request(summary_url, headers=headers)
        with urllib.request.urlopen(req_summary) as res:
            summary_raw = json.loads(res.read().decode('utf-8'))
            summary_result = summary_raw.get('result', {})
            
        papers_html = ""
        for pmid in ids:
            info = summary_result.get(pmid, {})
            title = info.get('title', '제목을 불러올 수 없습니다 (클릭하여 확인)')
            pubdate = info.get('pubdate', 'Recent')
            
            papers_html += f"""
            <div style="background: white; margin-bottom: 15px; padding: 18px; border-radius: 10px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="color: #3498db; font-weight: bold; font-size: 0.85em;">📅 {pubdate}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.05em; line-height:1.5; display: block; margin-top: 5px;">{title}</a>
            </div>"""
        return papers_html
    
    except Exception as e:
        return f"<p style='color:#e74c3c; padding-left:20px;'>데이터 로딩 실패 (PubMed 서버 응답 지연)</p>"

# 3. 분과별 검색어 (PubMed 최적화)
keywords = {
    "🍎 위장관 (GI)": "Gastroenterology",
    "🍺 간 (Liver)": "Hepatology",
    "🧬 췌담관 (Pancreas & Biliary)": "Pancreas OR Biliary"
}

all_sections_html = ""
for display_name, search_term in keywords.items():
    all_sections_html += f"""
    <h2 style="color: #2c3e50; margin-top: 40px; border-bottom: 3px solid #3498db; padding-bottom: 8px; display: inline-block;">{display_name}</h2>
    <div style="margin-top: 15px;">{get_pubmed_papers(search_term)}</div>"""

# 시간 설정 (KST)
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI/Liver/Biliary Dashboard</title>
</head>
<body style="font-family: sans-serif; background-color: #f0f4f7; padding: 20px; max-width: 850px; margin: auto; line-height: 1.6;">
    <header style="text-align: center; padding: 40px 0; background: white; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px;">
        <h1 style="color: #2c3e50; margin: 0; font-size: 2.2em;">🏥 소화기내과 최신 지견 포털</h1>
        <p style="color: #7f8c8d; margin-top: 10px; font-size: 1.1em;">GI · 간 · 췌담관 실시간 논문 브리핑</p>
        <div style="display: inline-block; background: #ebf5ff; color: #007bff; padding: 8px 20px; border-radius: 50px; font-weight: bold; font-size: 0.9em; margin-top: 15px;">Last Update: {time_label} (KST)</div>
    </header>
    <main>{all_sections_html}</main>
    <section style="margin-top: 70px; padding: 35px; background: linear-gradient(135deg, #2c3e50, #4ca1af); border-radius: 20px; color: white;">
        <h3 style="margin-top: 0; color: #00d2ff; font-size: 1.6em;">🚀 Project: MedProductive</h3>
        <p style="font-size: 1.1em; opacity: 0.95;">의료 현장의 비효율을 AI로 해결합니다.</p>
    </section>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
