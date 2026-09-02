---
title: 배포 소유 Operating-Intent 출처
translation_of: operating-intent-source.md
translation_source_sha: 4dc0872831dddcf3a84b76ccd7b4cd73f2ee173f
translation_revised: 2026-09-03
---
# 배포 소유 Operating-Intent 출처

`ServiceObjective`, `RecoveryObjective`, `CostObjective`, `ArchitectureConstraint`, `Ownership`,
`ChangeWindow`는 Forseti와 risk gate가 보호 대상 objective 및 constraint로 읽는 여섯 개
operating-intent ObjectType입니다. 이 타입들은 `Resource` 인스턴스만 담아도 되는 일반
`FDAI_OPERATING_MODEL_PATH` 스냅샷이 아니라 별도의 배포 소유 출처가 공급합니다. 이 문서는 그
바인딩을 소유합니다. 고정된 신원, fail closed 승인, 승인을 계속 최신으로 유지하는 유계 재검증,
replica 사이의 투영을 직렬화하는 잠금이 여기에 속합니다.

> **권한 경계:** 이 출처는 *intent의 형태*를 공급합니다. 투영은 유지보수·승인·실행 권한을 부여하지
> 않으며 타입이 지정된 objective와 constraint를 읽을 수 있게 만들 뿐입니다. 모든 상태 변경은
> [operating-ontology-ko.md](operating-ontology-ko.md)의 타입이 지정된 ActionType, risk, 승인, 실행,
> 검증, 복구 경계를 그대로 거칩니다.

## 고정된 신원

파일은 `provenance` 블록(`source_url`, `resolved_ref`, `retrieved_at`) 하나를 반드시 포함하고,
운영자는 검토 후 `FDAI_OPERATING_INTENT_SOURCE_REVISION`과 `FDAI_OPERATING_INTENT_SOURCE_SHA256`을
out-of-band로 한 번 고정합니다. 이는 고정된 `configuration_drift` 기준선 선례를 따릅니다. 이 digest는
provenance를 포함한 문서 전체를 덮으므로, provenance 필드를 고쳐 쓰거나 신선도 검사를 회피하려고
조회 시각을 미래로 당겨 적으면 objective를 수정한 것과 똑같이 고정값 검사에서 실패합니다.

Core 이미지는 승인된 일반 출처를 `/app/config/operating-intent/generic-source.json`에 함께
제공합니다. Terraform 호출부가 그 경로, 개정 번호, digest, 타입별 개수를 기본으로 고정하며, 배포는
이 값들을 함께 재정의하거나 바인딩을 비활성화합니다. 자리표시자 참조와 의도적으로 유효하지 않은
change window 때문에 이 출처를 바인딩해도 권한은 부여되지 않습니다.

## Fail closed 승인

투영 전에 런타임은 다음 경우 사유를 기록하고 이미 durable하게 owned된 그래프를 보존하며 fail
closed합니다.

| 결함 | 조건 |
|------|------|
| cross-release | `source_revision`, `provenance.resolved_ref` 또는 문서 전체 digest가 바인딩과 불일치합니다. |
| missing | 필수 타입의 인스턴스가 0개입니다. |
| duplicate | 타입 개수가 `FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON`(기본 타입별 1개)을 초과합니다. |
| incomplete | 같은 고정 개수에 미달하므로, 승인된 objective가 조용히 사라지지 않습니다. |
| stale | 인스턴스가 유효 구간을 벗어났거나, 출처가 인스턴스가 선언한 `freshness_seconds`를 초과했습니다. |

Stale 판정은 혼동해서는 안 되는 독립적인 두 축을 씁니다. 유효 구간(`effective_from`,
`effective_to`)은 *선언된 intent가 적용되는 기간*입니다. `freshness_seconds`는 *출처를 얼마나 최근에
관측했는지*이며 `effective_from`이 아니라 `provenance.retrieved_at` 기준으로 측정합니다. 따라서 방금
읽은 장수명 objective는 신선하고, 오래된 조회로 다시 게시한 갓 유효해진 objective는 stale이며, 미래
`retrieved_at`은 신뢰할 수 없는 관측 시각으로 보아 거부합니다.

## 지속적 승인

승인은 특정 시점에 대한 증명이며 상시 부여가 아닙니다. 시작 시점에 완전하고 신선했던 출처도 이후에
유효 구간을 벗어나거나, 선언한 신선도를 초과하거나, 개정 번호가 바뀌거나, 배포 마운트에서
사라지거나, 접근할 수 없게 될 수 있습니다.

그래서 유계 재검증 worker가
`FDAI_OPERATING_INTENT_SOURCE_REVALIDATE_SECONDS`(기본 300초, Terraform 필드
`operating_intent_source.revalidate_seconds`, 범위 1~28800초)마다 동일한 fail closed 검사를 다시
수행합니다. 각 재검증은 고정된 개정 번호, 문서 전체 digest, 검증 시각, 그리고 그 승인이 권한을
뒷받침할 수 있는 유효 기간을 담은 durable한 승인 기록을 남깁니다. 유효 기간은 재검증 간격의
배수이므로 한 번 늦은 재검증이 곧바로 권한을 회수하지는 않지만, 멈추었거나 계속 실패하는 worker는
추가 조치 없이 승인을 만료시킵니다.

실패한 재검증은 삭제가 아니라 격리입니다. 투영된 객체는 증거와 이력으로 계속 읽을 수 있고 intent
권한만 회수됩니다. 이후 유효한 갱신이 오면 재시작 없이 다시 승인하며, 변경 없이 이미 투영된 문서를
다시 승인할 때는 그래프를 다시 쓰지 않고 기록만 갱신합니다.

권한 소비자는 투영된 객체를 그대로 신뢰하지 않고 판단 시각의 승인 기록을 확인합니다. `ChangeWindow`
유지보수 권한은 격리·만료·이용 불가·형식 오류 승인에서 거부합니다. 실패한 출처가 공급한 window만이
아니라 모든 window를 거부하는데, 투영된 그래프는 각 window를 어느 출처가 보증했는지 기록하지 않으므로
개별 window가 여전히 뒷받침된다는 것을 증명할 수 없기 때문입니다. 기록이 아예 없다는 것은 배포 소유
intent 출처를 바인딩하지 않았다는 뜻이므로 아무것도 보류하지 않고 기존
`FDAI_OPERATING_MODEL_PATH` 동작을 그대로 둡니다.

## Replica 직렬화

매니페스트 확인, 중단된 적용 복구, 투영은 모두 고정된 `operating-intent-source:apply` 식별자로 배포
전역 리소스 잠금 안에서 수행합니다. 이 식별자는 상수인데, 잠금이 배포 전역 매니페스트 하나를
직렬화하기 때문입니다. 또한 두 출처가 서로 다른 매니페스트를 소유하므로 지속형 operating-model
worker의 키와도 분리되어 있습니다. 시작 경로도 같은 잠금을 잡습니다.

잠금이 없으면 동시에 시작한 replica가 상대의 진행 중 `applying` 매니페스트를 중단된 적용으로 잘못
읽고, 상대가 아직 쓰고 있는 하위 그래프를 삭제합니다. 잠금을 획득하지 못하면 `unavailable`을 기록하고
아무것도 투영하지 않으므로, 잠금 백엔드에 접근할 수 없을 때 경쟁하지 않고 fail closed합니다.

## 관련 문서

| 알아볼 내용 | 읽을 문서 |
|-------------|-----------|
| 구현 상태 및 남은 작업 | [Operating-intent source](operating-intent-source.md#implementation-status) |
| 이 출처가 채우는 운영 온톨로지 | [운영 온톨로지](operating-ontology-ko.md) |
| 동일한 env 바인딩의 로컬·배포 동등성 | [dev-and-deploy-parity](../deployment/dev-and-deploy-parity-ko.md) |
| 모듈 위치 | [코드 지도](code-map-ko.md) |
