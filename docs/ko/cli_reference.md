# CLI Reference (Korean)

`vectordb` 커맨드 라인 인터페이스(CLI)는 서버 관리 및 설정 확인을 위한 도구입니다.

## 기본 명령어

```bash
python -m vectordb [GROUP] [COMMAND] --option value
```

## 1. Config 그룹

설정 파일을 관리하고 확인합니다.

### `config show`
현재 로드된 설정을 JSON 형태로 출력합니다.

```bash
# 기본(개발) 설정 확인
python -m vectordb config show

# 프로덕션 설정 확인
python -m vectordb config show --env production
```

## 2. Server 그룹

VectorDB 서버를 실행합니다.

### `server start`
FastAPI 서버(Uvicorn)를 구동합니다.

**옵션:**
- `--port`: 포트 번호 (기본값: `config/defaults.yaml`의 `server.port`)
- `--env`: 실행 환경 (`development` / `production`)

**예제:**
```bash
# 개발 모드 (8000포트, Hot Reload)
python -m vectordb server start --env development

# 프로덕션 모드 (9090포트, 최적화)
python -m vectordb server start --env production --port 9090
```

> [!IMPORTANT]
> `--env production`을 사용하면 `config/production.yaml`의 설정(Workers=8, Debug=False)이 적용됩니다.
