import urllib.request
import re
import datetime
import json

def get_pubmed_papers():
    # 검색어 설정: Gastroenterology
    # sort=date (최근 등록 순) 옵션을 사용하여 엉뚱한 미래 날짜가 먼저 나오지 않게 합니다.
    query = "Gastroenterology"
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax=5&sort=date&retmode=json"
    
    try:
        with urllib.request.urlopen(search_url) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            ids = search_data['esearchresult']['idlist']
        
        if not ids:
            return "<li>검색된 최근 논문이 없습니다.</li>"

        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        with urllib.request.urlopen(summary_url) as res:
            summary_data = json.loads(res.read().decode('utf-8'))
            
        papers_html = ""
        for pmid in ids:
            paper_info = summary_data['result'][pmid]
            title = paper_info.get('title', 'No Title')
            
            # 정식 출판일 대신 시스템 등록일(sortdate)을 사용하면 더 정확한 '최근성'을 보여줍니다.
            raw_date = paper_info.get('sortdate', 'No Date')
            clean_date = raw_date.split(' ')[0] if ' ' in raw_date else raw_date
            
            papers_html += f"""
            <li style="background: white; margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); list-style: none;">
                <span style="color: #3498db; font-weight: bold; font-size: 0.85em;">📅 등록일: {clean_date}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.1em; line-height:1.4;">{title}</a>
            </li>"""
        return papers_html

    except Exception as e:
        return f"<li>데이터 로딩 오류: {e}</li>"

# 시간 설정 (KST)
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

paper_list = get_pubmed_papers()

html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI 최신 논문 브리핑</title>
</head>
<body style="font-family: 'Malgun Gothic', sans-serif; background-color: #f0f2f5; padding: 20px; max-width: 700px; margin: auto;">
    <header style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">🏥 GI 최신 논문 브리핑</h1>
        <p style="color: #7f8c8d;">자동 갱신 시간: {time_label} (KST)</p>
    </header>
    <main>
        <ul style="padding: 0;">
            {paper_list}
        </ul>
    </main>
    <footer style="text-align: center; margin-top: 50px; color: #bdc3c7; font-size: 0.8em;">
        <p>PubMed API를 통해 실시간 데이터를 수집합니다.</p>
    </footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
