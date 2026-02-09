# NEXUS - Her Projede Hızlı Kurulum Kılavuzu

> **Yeni bir projeye başladığında 5 dakikada kalite sistemini kur**

---

## 🔥 Hızlı Başlangıç (5 dakika)

### Adım 1: Projeyi Oluştur ve NEXUS'i Kur

```bash
# Yeni proje oluştur
mkdir my-new-project
cd my-new-project
git init

# NEXUS'i zaten kurulu varsayıyorum (~/.claude/ altında)
# Değilse: git clone https://github.com/turtir-ai/nexus-v3-5.git
```

### Adım 2: Proje Kalite Dosyası Oluştur

```bash
# Proje dizininde kalite profilini oluştur
cat > .claude/QUALITY.md << 'EOF'
# Proje Kalite Profili

## Kalite Kuralları
- Kod yazmadan önce mevcut dosyaları oku
- Değişiklikten sonra test/lint çalıştır
- Sadece kanıtlanmış sonuçları raporla

## Gerekli Kontroller
```bash
# Her değişiklik sonrası
ruff check .
python3 -m pytest tests/ -v
```

## Görev Takibi
```bash
# Görev başlat
nexus task start "görev-tanımı"

# Görev bitir
nexus task close --success
```
EOF
```

### Adım 3: Proje-Spesifik Settings

```bash
# Proje için NEXUS ayarları
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

### Adım 4: İlk Test

```bash
# Kalite kapısını test et
echo "def bad(): pass" > test_bad.py
python3 ~/.claude/hooks/quality_gate.py < <(cat <<'JSON'
{
  "tool_name": "Write",
  "tool_input": {"file_path": "test_bad.py"},
  "tool_response": {"success": true},
  "cwd": "."
}
JSON
)
# Beklenen: Ruff hatası ve rollback
```

---

## 📋 Standart Proje Yapısı

```
my-new-project/
├── .claude/
│   ├── QUALITY.md              # Proje kalite kuralları
│   └── settings.local.json     # Proje NEXUS ayarları
├── src/                        # Proje kodu
├── tests/                      # Testler
└── README.md
```

---

## 🎯 Proje Tipine Göre Kurulum

### Python Projesi

```bash
# pyproject.tomx oluştur
cat > pyproject.toml << 'EOF'
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
EOF

# NEXUS quality gate için bu yeterli
```

### Node.js Projesi

```bash
# package.json oluştur
npm init -y

# NEXUS quality gate otomatik npm test çalıştırır
```

### TypeScript Projesi

```bash
# tsconfig.json + package.json
npm install -D typescript @types/node
```

---

## ⚡ Günlük Akış

### 1. Yeni Görev Başlat

```bash
cd my-project
nexus task start "Kullanıcı girişi ekle"
```

### 2. Kod Yaz ve Test Et

```bash
# Kod yaz
# Claude Code ile çalış

# Quality gate otomatik çalışır
# Hatalı kod → Rollback → Incident → Fix task
```

### 3. Görevi Bitir

```bash
nexus task close --success --note "JWT kullanıldı"
```

---

## 🔍 Kalite Raporu

```bash
# Her gün çalıştır
python3 ~/.claude/generate_quality_report.py

# Sonuçları gör
cat ~/.claude/state/quality_report.json | jq '.quality_score'
```

---

## 🛠️ Sorun Giderme

### Quality Gate Çalışmıyorsa

```bash
# 1. Hook yolunu kontrol et
cat ~/.claude/settings.json | grep quality_gate

# 2. Python script çalıştırılabilir mi
chmod +x ~/.claude/hooks/quality_gate.py

# 3. Manuel test
echo '{}' | python3 ~/.claude/hooks/quality_gate.py
```

### Test Başarısız Olursa

```bash
# Fix queue'u kontrol et
nexus fix stats

# Bir fix işle
nexus fix process-one
```

---

## 📊 İlerleme Takibi

```bash
# Günlük durum
nexus status

# Haftalık rapor
python3 ~/.claude/generate_quality_report.py | jq '{
  quality_score,
  tasks_completed,
  incidents_total,
  fixes_completed
}'
```

---

## 🎓 Öğrenilen Pattern'ler

```bash
# Pattern learning dosyası
cat ~/.claude/state/learning_patterns.json | jq '.patterns | keys'
```

---

## 🚀 Sonraki Adım

```bash
# Integration test çalıştır
cd ~/.claude
./scripts/nexus_integration_test.sh

# Tüm testler geçmeli
```

---

## 💡 İpuçları

1. **Her projede aynı structure** - `.claude/QUALITY.md` standardı
2. **Task takibi zorunlu** - `nexus task start` unutma
3. **Quality gate'e güven** - Hatalı kodu yakalar
4. **Fix queue'u kontrol et** - Düzenli olarak `nexus fix stats`

---

**Özet:** Yeni proje = 5 dakika kurulum + `.claude/` dizini + standard kalite profil'i
