import urllib.request
import re
import datetime
import json

def get_pubmed_papers(query, limit=3):
    # 키워드별 검색 (한 섹션당 3개씩, 최신순)
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query.replace(' ', '+')}&retmax={limit}&sort=date&retmode=json"
    
    try:
        with urllib.request.urlopen(search_url) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            ids = search_data['esearchresult']['idlist']
        
        if not ids:
            return "<p style='color:#999; padding-left:20px;'>최근 24시간 내 등록된 논문이 없습니다.</p>"

        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        with urllib.request.urlopen(summary_url) as res:
            summary_data = json.loads(res.read().decode('utf-8'))
            
        papers_html = ""
        for pmid in ids:
            paper_info = summary_data['result'][pmid]
            title = paper_info.get('title', 'No Title')
            # 날짜가 길 경우 연도/월만 추출하여 깔끔하게 표시
            pubdate = paper_info.get('pubdate', 'Recent')
            
            papers_html += f"""
            <div style="background: white; margin-bottom: 15px; padding: 18px; border-radius: 10px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="color: #3498db; font-weight: bold; font-size: 0.85em;">📅 {pubdate}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.05em; line-height:1.5; display: block; margin-top: 5px;">{title}</a>
            </div>"""
        return papers_html
    except:
        return "<p style='color:red;'>데이터를 가져오는 중 오류가 발생했습니다.</p>"

# 1. 선생님이 요청하신 3대 분과 키워드 설정
keywords = {
    "🍎 위장관 (GI)": "Gastrointestinal Tract",
    "🍺 간 (Liver)": "Liver Diseases",
    "🧬 췌담관 (Pancreas & Biliary)": "Pancreas OR Biliary Tract"
}

# 2. 각 키워드별 결과 생성
all_sections_html = ""
for display_name, search_term in keywords.items():
    all_sections_html += f"""
    <h2 style="color: #2c3e50; margin-top: 45px; border-bottom: 3px solid #3498db; padding-bottom: 8px; display: inline-block;">{display_name}</h2>
    <div style="margin-top: 15px;">
        {get_pubmed_papers(search_term)}
    </div>
    """

# 3. 시간 설정 (KST)
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

# 4. 전체 HTML 템플릿
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI/Liver/Biliary Dashboard</title>
</head>
<body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background-color: #f0f4f7; padding: 20px; max-width: 850px; margin: auto; color: #333; line-height: 1.6;">
    <header style="text-align: center; padding: 40px 0; background: white; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 30px;">
        <h1 style="color: #2c3e50;
