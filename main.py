import urllib.request
import re
import datetime
import json

def get_pubmed_papers():
    query = "Gastroenterology"
    # sort=date로 최신순 정렬
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
            
            # 날짜 추출 로직 강화: pubdate가 없으면 sortdate 사용
            display_date = paper_info.get('pubdate', paper_info.get('sortdate', 'Recent'))
            
            papers_html += f"""
            <li style="background: white; margin-bottom: 15px; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); list-style: none; border-left: 5px solid #3498db;">
                <span style="color: #3498db; font-weight: bold; font-size: 0.9em;">📅 {display_date}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.1em; line-height:1.5; display: block; margin-top: 5px;">{title}</a>
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
<body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #f8f9fa; padding: 20px; max-width: 800px; margin: auto; color: #333;">
    <header style="text-align: center; margin-bottom: 40px; padding: 20px 0;">
        <h1 style="color: #2c3e50; font-size: 2em; margin-bottom: 10px;">🏥 GI 최신 논문 브리핑</h1>
        <p style="color: #7f8c8d; font-size: 1em;">자동 업데이트: <strong>{time_label}</strong> (KST)</p>
    </header>

    <main>
        <ul style="padding: 0;">
            {paper_list}
        </ul>
    </main>

    <section style="margin-top: 60px; padding: 30px; background: linear-gradient(135deg, #3498db, #2980b9); border-radius: 15px; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.1);">
        <h2 style="margin-top: 0; font-size: 1.5em;">🚀 MedProductive Project</h2>
        <p style="font-size: 1.1em; line-height: 1.6; opacity: 0.9;">
            AI를 활용한 의료 생산성 혁신 시스템을 개발하고 있습니다.<br>
            <b>Vol 1. 전공의를 위한 업무 자동화 가이드</b> (준비 중)
        </p>
        <div style="margin-top: 20px;">
            <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-size: 0.9em; margin-right: 10px;">#GI_Fellow</span>
            <span style="background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; font-size: 0.9em;">#AI_Efficiency</span>
        </div>
    </section>

    <footer style="text-align: center; margin-top: 40px; color: #bdc3c7; font-size: 0.85em;">
        <p>본 사이트는 GitHub Actions를 통해 매일 PubMed 데이터를 자동으로 수집합니다.</p>
    </footer>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)
