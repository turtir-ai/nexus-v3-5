# NEXUS V3.5.0 - Tam Entegrasyon Rehberi

> **Her projede kalite sistemi kurmak için-complete guide**

---

## 🎯 Amaç

Bu rehber, **yeni bir projeye başladığında** NEXUS kalite sistemini **5 dakika içinde** nasıl kuracağını gösterir.

---

## 📋 Ön Koşullar

NEXUS'in zaten kurulu olduğunu varsayar (~/.claude/ altında):

```bash
# Kontrol et
ls -la ~/.claude/hooks/quality_gate.py
ls -la ~/.claude/nexus_cli.py

# Eğer yoksa, kur:
git clone https://github.com/turtir-ai/nexus-v3-5.git
cd nexus-v3-5
bash scripts/install_to_claude.sh
```

---

## 🚀 Yöntem 1: Otomatik Kurulum Script'i (Önerilen)

### Tek Komutla Proje Oluştur

```bash
# Python projesi
./new_project_setup.sh my-python-app python

# Node.js projesi
./new_project_setup.sh my-node-app node

# TypeScript projesi
./new_project_setup.sh my-ts-app typescript

# Generic projesi
./new_project_setup.sh my-generic-app generic
```

### Script Ne Yapar?

1. ✅ Proje dizinini oluşturur
2. ✅ Git'i başlatır
3. ✅ `.claude/QUALITY.md` oluşturur (proje tipine göre)
4. ✅ `.claude/settings.local.json` oluşturur
5. ✅ Proje yapısını oluşturur (pyproject.toml, package.json, vb.)
6. ✅ `.gitignore` ekler
7. ✅ `README.md` oluşturur
8. ✅ İlk commit'i yapar

---

## 🛠️ Yöntem 2: Manuel Kurulum

### Adım 1: Proje Dizinini Oluştur

```bash
mkdir my-project
cd my-project
git init
```

### Adım 2: `.claude/` Dizinini Oluştur

```bash
mkdir -p .claude
```

### Adım 3: QUALITY.md Oluştur

```bash
cat > .claude/QUALITY.md << 'EOF'
# Proje Kalite Profili

## Kalite Kuralları
- Küçük, targeted değişiklikler
- Her edit sonrası test
- Kanıt tabanlı raporlama

## Gerekli Kontroller
```bash
# Proje tipine göre
make test  # veya
pytest      # veya
npm test
```

## Task Takibi
```bash
nexus task start "görev-tanımı"
nexus task close --success
```
EOF
```

### Adım 4: settings.local.json Oluştur

```bash
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
```

### Adım 5: Proje Dosyalarını Oluştur

```bash
# Python için
cat > pyproject.toml << 'EOF'
[project]
name = "my-project"
version = "0.1.0"

[tool.ruff]
line-length = 100
EOF

mkdir -p src tests
touch src/__init__.py tests/__init__.py
```

---

## ✅ Kurulum Doğrulama

### Test 1: NEXUS Durumu

```bash
nexus status
```

Beklenen çıktı:
```json
{
  "status": "active",
  "runtime_version": "3.5.0",
  ...
}
```

### Test 2: Quality Gate

```bash
# Hatalı kod yaz
echo "def bad(:" > test.py

# Quality gate çalıştır
echo '{"tool_name":"Write","tool_input":{"file_path":"test.py"},"tool_response":{"success":true},"cwd":"."}' | \
  python3 ~/.claude/hooks/quality_gate.py
```

Beklenen: Ruff hatası ve rollback

### Test 3: İlk Görev

```bash
nexus task start "Kurulum testi"
nexus task close --success --note "Kurulum başarılı"
```

---

## 📁 Proje Tipine Göre Kalite Profilleri

### Python Projesi

```markdown
# .claude/QUALITY.md

## Kalite Kuralları
- Type hints kullan (PEP 484)
- Docstring'ler Google style
- Maksimum 100 karakter satır uzunluğu

## Gerekli Kontroller
```bash
ruff check .
ruff format --check .
pytest tests/ -v
```
```

### Node.js Projesi

```markdown
# .claude/QUALITY.md

## Kalite Kuralları
- ESLint + Prettier format
- Jest test coverage
- Semver versioning

## Gerekli Kontroller
```bash
npm run lint
npm test
npm run build
```
```

### TypeScript Projesi

```markdown
# .claude/QUALITY.md

## Kalite Kuralları
- Strict mode enabled
- No implicit any
- Interface over type

## Gerekli Kontroller
```bash
npm run build
npm run lint
npm test
```
```

---

## 🔄 Günlük Akış

### Sabah Başlangıcı

```bash
cd my-project

# 1. NEXUS durumu kontrol et
nexus status

# 2. Yeni görev başlat
nexus task start "Bugün yapılacaklar"
```

### Kodlama Sırası

```bash
# Claude Code ile çalış
# Quality gate otomatik çalışır
# - Hatalı kod → Rollback → Incident
# - İyi kod → Pass → Progress
```

### Gün Sonu

```bash
# 1. Görevi kapat
nexus task close --success --note "Bitti"

# 2. Kalite raporu
python3 ~/.claude/generate_quality_report.py

# 3. Fix queue kontrol
nexus fix stats
```

---

## 📊 İlerleme Takibi

### Haftalık Rapor

```bash
python3 ~/.claude/generate_quality_report.py | jq '{
  quality_score,
  tasks_completed,
  incidents_total,
  fixes_completed,
  patterns: .metrics.patterns
}'
```

### Pattern Learning

```bash
# Öğrenilen pattern'ları gör
cat ~/.claude/state/learning_patterns.json | jq '.patterns | keys'
```

### Incident History

```bash
# Son 5 incident
tail -5 ~/.claude/state/incidents.jsonl | jq '{id, incident_class, status}'
```

---

## 🛡️ Quality Gate Davranışı

### Başarısız Olursa

```
1. Incident oluşturulur (incidents.jsonl)
2. Fix task eklenir (fix_queue.jsonl)
3. Pattern öğrenilir (learning_patterns.json)
4. Rollback yapılır (git checkout)
5. Exit code 2 ile çıkar
```

### Başarılı Olursa

```
1. Pattern öğrenilir (quality_gate_pass)
2. Metrics güncellenir (runs++)
3. Active task varsa progress++
4. Exit code 0 ile devam eder
```

---

## 🔧 Sorun Giderme

### Quality Gate Çalışmıyorsa

```bash
# 1. Hook yolunu kontrol et
cat ~/.claude/settings.json | grep quality_gate

# 2. Script executable mi
ls -la ~/.claude/hooks/quality_gate.py

# 3. Manuel test
echo '{}' | python3 ~/.claude/hooks/quality_gate.py
```

### Task CLI Çalışmıyorsa

```bash
# 1. CLI dosyası var mı
ls -la ~/.claude/nexus_cli.py

# 2. Python script mi
file ~/.claude/nexus_cli.py

# 3. Manuel çalıştır
python3 ~/.claude/nexus_cli.py status
```

### Fix Queue Boşsa

```bash
# Durum
nexus fix stats

# Manuel incident oluştur
echo '{"tool_name":"Bash","tool_input":{"command":"false"},"tool_response":{"success":false,"exit_code":1},"cwd":"."}' | \
  python3 ~/.claude/hooks/nexus_self_heal.py

# İşle
nexus fix process-one
```

---

## 📚 Referanslar

| Dokümantasyon | Dosya |
|---------------|-------|
| Ana README | `README.md` |
| Proje Dokümantasyonu | `NEXUS_PROJECT_DOCUMENTATION.md` |
| Hızlı Başlangıç | `QUICK_START_GUIDE.md` |
| Kalite Profili | `CLAUDE_ZAI_QUALITY_PROFILE.md` |
| Türkçe Dokümantasyon | `README_TR.md` |
| Değişiklik Günlüğü | `CHANGELOG.md` |
| Kanıtlar | `EVIDENCE_*.md` |

---

## 🎓 Best Practices

1. **Her projede aynı structure**
   - `.claude/QUALITY.md` standardı
   - `nexus task start` ile başla
   - `nexus task close` ile bitir

2. **Quality gate'e güven**
   - Hatalı kodu yakalar
   - Rollback yapar
   - Incident oluşturur

3. **Düzenli kontrol**
   - Haftalık kalite raporu
   - Aylık pattern learning review
   - Fix queue temizliği

4. **Kanıt tabanlı yaklaşım**
   - "Çalışıyor" deme, kanıt göster
   - Test sonuçlarını raporla
   - Metrics ile takip et

---

**Sonuç:** 5 dakikada yeni proje + kalite sistemi hazır! 🚀
