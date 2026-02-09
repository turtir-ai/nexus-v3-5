#!/usr/bin/env bash
# NEXUS - Yeni Proje Kurulum Script'i
# Kullanım: ./new_project_setup.sh <proje-adi> [python|node|typescript|generic]

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default values
PROJECT_TYPE="${2:-generic}"
PROJECT_NAME="$1"

if [[ -z "$PROJECT_NAME" ]]; then
    echo "Kullanım: $0 <proje-adi> [python|node|typescript|generic]"
    exit 1
fi

echo -e "${BLUE}🚀 NEXUS Proje Kurulumu${NC}"
echo "Proje: $PROJECT_NAME"
echo "Tip: $PROJECT_TYPE"
echo ""

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Initialize git
git init -q
git config user.email "nexus@local"
git config user.name "NEXUS Setup"

# Create .claude directory
mkdir -p .claude

echo -e "${GREEN}✓ Proje dizini oluşturuldu${NC}"

# Create QUALITY.md based on project type
case "$PROJECT_TYPE" in
    python)
        cat > .claude/QUALITY.md << 'EOF'
# Python Proje Kalite Profili

## Kalite Kuralları
- Type hints kullan (PEP 484)
- Docstring'ler Google style
- Maksimum 100 karakter satır uzunluğu

## Gerekli Kontroller
```bash
# Her değişiklik sonrası
ruff check .
ruff format --check .
python3 -m pytest tests/ -v
python3 -m mypy src/ 2>/dev/null || true
```

## Python Standartları
- `ruff` için lint + format
- `pytest` için test
- `mypy` opsiyonel type check

## Task Takibi
```bash
nexus task start "görev-tanımı"
# ... kod yaz ...
nexus task close --success
```
EOF
        ;;

    node|typescript)
        cat > .claude/QUALITY.md << 'EOF'
# Node.js/TypeScript Proje Kalite Profili

## Kalite Kuralları
- TypeScript için strict mode
- ESLint + Prettier format
- Jest test coverage

## Gerekli Kontroller
```bash
# Her değişiklik sonrası
npm run lint
npm run test
npm run build 2>/dev/null || true
```

## Standartlar
- ESLint için Airbnb config
- Jest için minimum %80 coverage

## Task Takibi
```bash
nexus task start "görev-tanımı"
# ... kod yaz ...
nexus task close --success
```
EOF
        ;;

    *)
        cat > .claude/QUALITY.md << 'EOF'
# Proje Kalite Profili

## Kalite Kuralları
- Küçük, targeted değişiklikler
- Her edit sonrası test
- Kanıt tabanlı raporlama

## Gerekli Kontroller
```bash
# Proje tipine göre test komutu
# Örnek: make test, npm test, pytest, vb.
```

## Task Takibi
```bash
nexus task start "görev-tanımı"
# ... kod yaz ...
nexus task close --success
```
EOF
        ;;
esac

echo -e "${GREEN}✓ QUALITY.md oluşturuldu${NC}"

# Create settings.local.json
cat > .claude/settings.local.json << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOME/.claude/hooks/quality_gate.py"
          }
        ]
      }
    ]
  },
  "rules": [
    ".claude/QUALITY.md"
  ]
}
EOF

echo -e "${GREEN}✓ settings.local.json oluşturuldu${NC}"

# Create project-specific files based on type
case "$PROJECT_TYPE" in
    python)
        cat > pyproject.toml << 'EOF'
[project]
name = ""
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
EOF

        mkdir -p src tests
        touch src/__init__.py tests/__init__.py

        echo -e "${GREEN}✓ Python proje yapısı oluşturuldu${NC}"
        ;;

    node)
        cat > package.json << 'EOF'
{
  "name": "",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "test": "echo \"Test tanımlanmadı\"",
    "lint": "echo \"Lint tanımlanmadı\""
  }
}
EOF

        mkdir -p src tests

        echo -e "${GREEN}✓ Node.js proje yapısı oluşturuldu${NC}"
        ;;

    typescript)
        cat > package.json << 'EOF'
{
  "name": "",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "test": "echo \"Test tanımlanmadı\"",
    "lint": "echo \"Lint tanımlanmadı\""
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/node": "^20.0.0"
  }
}
EOF

        cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "node",
    "strict": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules"]
}
EOF

        mkdir -p src tests

        echo -e "${GREEN}✓ TypeScript proje yapısı oluşturuldu${NC}"
        ;;

    *)
        mkdir -p src tests
        echo -e "${GREEN}✓ Generic proje yapısı oluşturuldu${NC}"
        ;;
esac

# Create .gitignore
cat > .gitignore << 'EOF'
# NEXUS state (optional, commit if you want)
.claude/state/

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.venv/

# Node
node_modules/
dist/
*.log

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF

echo -e "${GREEN}✓ .gitignore oluşturuldu${NC}"

# Create README.md
cat > README.md << EOF
# $PROJECT_NAME

Proje NEXUS kalite sistemi ile kuruldu.

## Kalite Kontrolü

\`\`\`bash
# Kalite profili
cat .claude/QUALITY.md

# NEXUS durumu
nexus status
\`\`\`

## İlk Görev

\`\`\`bash
nexus task start "İlk görevi tanımla"
\`\`\`

---

Generated by NEXUS V3.5.0
EOF

echo -e "${GREEN}✓ README.md oluşturuldu${NC}"

# Initial commit
git add -A
git commit -m "Initial commit: NEXUS quality setup" -q

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Proje kurulumu tamamlandı!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "Sonraki adımlar:"
echo "  cd $PROJECT_NAME"
echo "  nexus task start \"İlk görevi tanımla\""
echo ""
echo "Kalite profili:"
echo "  cat .claude/QUALITY.md"
echo ""
