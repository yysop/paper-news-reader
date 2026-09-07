# 오늘의 지면 — 완전자동화 버전

## 현재 자동화
- 동아일보 공개 지면 목차 자동 수집
- 매일경제 오늘의 매경 A/B/C 섹션 자동 수집
- 매일 오전 7:30 KST GitHub Actions 자동 실행
- 최근 15일 데이터를 `data/YYYY-MM-DD.json`으로 저장
- 웹에서 날짜/신문사/섹션/면 선택 가능

## 적용 방법
이 압축의 파일을 기존 `paper-news-reader` 저장소 루트에 전부 덮어쓴 뒤:

```powershell
git add .
git commit -m "feat: 지면 뉴스 완전 자동화"
git push
```

그리고 GitHub → Actions → `Update daily newspaper metadata` → Run workflow를 한 번만 수동 실행해 테스트합니다.
그 뒤부터는 매일 07:30 KST 자동 실행됩니다.

## 주의
신문사 HTML 구조가 바뀌면 해당 수집기 유지보수가 필요할 수 있습니다.
유료벽/로그인을 우회하지 않으며 기사 전문을 저장하지 않습니다.
