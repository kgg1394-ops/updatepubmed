import urllib.request
import re
import datetime

def get_pubmed_papers():
    # 'Gastroenterology' 키워드로 최신 논문 검색 (PubMed API)
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=Gastroenterology&retmax=5&sort=pub+date"
    with urllib.request.urlopen(search_url) as response:
        xml = response.read().decode('utf-8')
    
    # 논문 ID(PMID)들 추출
    ids = re.findall(r'<Id>(\d+)</Id>', xml)
    
    papers = []
    for pmid in ids:
        # 각 논문의 상세 정보(제목) 가져오기
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        with urllib.request.urlopen(summary_url) as res:
            import json
            data = json.loads(res.read().decode('utf-8'))
            title = data['result'][pmid]['title']
            pubdate = data['result'][pmid]['pubdate']
            papers.append(f"<li><strong>[{pubdate}]</strong> {title} <a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/' target='_blank'>[Link]</a></li>")
    
    return "".join(papers)

# 시간 설정
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

# 논문 리스트 가져오기
paper_list_html = get_pubmed_papers()

# 최종 HTML 생성
html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GI Latest Papers</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; padding: 20px; color: #333; max-width: 800px; margin: auto; background-color: #f9f9f9; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }}
        .update-time {{ color: #7f8c8d; font-size: 0.9em; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ background: white; margin-bottom: 15px; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>🏥 GI 최신 논문 브리핑</h1>
    <p class="update-time">마지막 업데이트 (KST): {time_label}</p>
    <ul>
        {paper_list_html}
    </ul>
    <p style="margin-top:30px; font-size:0.8em; color:#999;">이 페이지는 매일 아침 GitHub Actions에 의해 자동으로 업데이트됩니다.</p>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
