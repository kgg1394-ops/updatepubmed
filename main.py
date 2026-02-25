import urllib.request
import re
import datetime
import json

def get_pubmed_papers(query, limit=3):
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query.replace(' ', '+')}&retmax={limit}&sort=date&retmode=json"
    try:
        with urllib.request.urlopen(search_url) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            ids = search_data['esearchresult']['idlist']
        
        if not ids:
            return "<p style='color:#999; padding-left:20px;'>최근 등록된 논문이 없습니다.</p>"

        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
        with urllib.request.urlopen(summary_url) as res:
            summary_data = json.loads(res.read().decode('utf-8'))
            
        papers_html = ""
        for pmid in ids:
            paper_info = summary_data['result'][pmid]
            title = paper_info.get('title', 'No Title')
            pubdate = paper_info.get('pubdate', 'Recent')
            
            papers_html += f"""
            <div style="background: white; margin-bottom: 15px; padding: 18px; border-radius: 10px; border-left: 5px solid #3498db; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <span style="color: #3498db; font-weight: bold; font-size: 0.85em;">📅 {pubdate}</span><br>
                <a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank" style="text-decoration: none; color: #2c3e50; font-weight: bold; font-size: 1.05em; line-height:1.5; display: block; margin-top: 5px;">{title}</a>
            </div>"""
        return papers_html
    except:
        return "<p style='color:red;'>데이터 로딩 중 오류 발생</p>"

# 키워드 설정
keywords = {
    "🍎 위장관 (GI)": "Gastrointestinal Tract",
    "🍺 간 (Liver)": "Liver Diseases",
    "🧬 췌담관 (Pancreas & Biliary)": "Pancreas OR Biliary Tract"
}

all_sections_html = ""
for display_name, search_term in keywords.items():
    all_sections_html += f"""
    <h2 style="color: #2c3e50; margin-top: 45px; border-bottom: 3px solid #3498db; padding-bottom: 8px; display: inline-block;">{display_name}</h2>
    <div style="margin-top: 15px;">
        {get_pubmed_papers(search_term)}
    </div>
    """

now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

# HTML 템플릿 - 마지막의 따옴표 3개 확인 필수!
html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <meta
