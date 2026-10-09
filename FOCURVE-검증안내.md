# FOCURVE EXT-02 개인 검증용 전달

이 브랜치는 다운로드 전달용입니다. 팀 저장소 PR #17 수정/병합이나 EXT-02 완료를 뜻하지 않습니다.

`focurve-extension-review-local-20261009.zip`을 다운로드·압축해제하고 manifest.json이 있는 `extension` 폴더를 Chrome에 로드하세요. 기존 설치를 삭제하거나 DB를 초기화하지 말고 기존 로드 경로에 최신 파일을 반영한 뒤 새로고침하세요.

팀 저장소 기준 HEAD: e79ef3034e3951a20c735de714debab830006284 + 미커밋 제품 수정. 이 개인 저장소 커밋은 검증 제품을 전달하는 커밋이며 팀 소스의 최종 승인 SHA가 아닙니다.

제품 식별 SHA256: 2ae196a83b5177dfd496a65d18da9da7c28c6786c4964f46aa28bf08da66aa2a. ZIP 안 product-identity.json에 파일별 SHA256이 있습니다.

로컬 모의 테스트79/79, 모의 UI16항목 통과. 최신 실제 Chrome·회원 인증/명령/보고·Server reconcile·실제quota·HTTP 통합은 미검증/차단입니다. 해당 기준이 모두 통과하기 전 팀 저장소 Commit/Push/PR 갱신/병합은 보류합니다.

실제 방문 host별 target_key와 matched_policy_host 기록을 수정했습니다. www 유지, 마지막 점 제거, Snapshot1.2 MOST_SPECIFIC_HOST는 유지합니다.

Chrome 버전/OS/로드 파일 hash와 사이트 CRUD·시작/차단/기록/종료/해제·설정 변경/다음 세션·Worker 복구 결과를 남겨주세요. chzzk.naver.com → www.naver.com → chzzk.naver.com → www.naver.com 순서의 성공 탐색은 전체4/반복2이며 각 host 순위1,1,2,2입니다. 회원/Server 통합 성공으로 확대하지 않습니다.
