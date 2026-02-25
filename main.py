import urllib.request
import re
import datetime
import json

def get_pubmed_papers():
    # 검색어: Gastroenterology (소화기내과) / 최신순 5개
    query = "Gastroenterology"
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax=5&sort=pub+date&retmode=json"
    
    try:
        # 1. 논문 ID 리스트 가져오기
        with urllib.request.urlopen(search_url) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            ids = search_data['esearchresult']['idlist']
        
        if not ids:
            return "<li>검색된 최신 논문이 없습니다.</li>"

        # 2. 각 ID별 상세 정보 가져오기
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        with urllib.request.urlopen(summary_url) as res:
            summary_data = json.loads(res.read().decode('utf-8'))
            
        papers_html = ""
        for pmid in ids:
            title = summary_data['result'][pmid].get('title', 'No Title')
            pubdate = summary_data['result'][pmid].get('pubdate', 'No Date')
            # HTML 리스트 항목 생성
            papers_html += f"""
            <li style="background: white; margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); list-style: none;">
                <span style="color: #e67e22; font-weight: bold; font-size: 0.85em;">{pubdate}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.1em;">{title}</a>
            </li>"""
        return papers_html

    except Exception as e:
        return f"<li>데이터를 가져오는 중 오류 발생: {e}</li>"

# 시간 설정 (KST)
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

# 논문 데이터 생성
paper_list = get_pubmed_papers()

# 최종 웹사이트 코드
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI 최신 논문 브리핑</title>
</head>
<body style="font-family: sans-serif; background-color: #f4f7f6; padding: 20px; max-width: 700px; margin: auto;">
    <header style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c3e50;">🏥 GI 최신 논문 브리핑</h1>
        <p style="color: #7f8c8d;">업데이트: {time_label} (KST)</p>
    </header>
    <main>
        <ul style="padding: 0;">
            {paper_list}
        </ul>
    </main>
    <footer style="text-align: center; margin-top: 50px; color: #bdc3c7; font-size: 0.8em;">
        <p>본 페이지는 GitHub Actions를 통해 PubMed 데이터를 자동으로 수집합니다.</p>
    </footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
