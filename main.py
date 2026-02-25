import datetime

# 1. 정보 준비 (나중에는 여기서 논문을 검색합니다)
now = datetime.datetime.now() + datetime.timedelta(hours=9)
time_label = now.strftime("%Y-%m-%d %H:%M")

# 2. 웹사이트 화면 디자인 (HTML)
content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>My Daily Bio</title></head>
<body style="text-align:center; padding:50px; font-family:sans-serif;">
    <h1>🏥 오늘의 의학 뉴스 브리핑</h1>
    <p style="color:gray;">마지막 업데이트: {time_label}</p>
    <div style="border:1px solid #ddd; padding:20px; border-radius:10px;">
        <h3>현재 논문 수집 로봇이 가동 중입니다.</h3>
        <p>GitHub Actions가 매일 아침 자동으로 이 페이지를 갱신합니다.</p>
    </div>
</body>
</html>
"""

# 3. 파일로 저장
with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
