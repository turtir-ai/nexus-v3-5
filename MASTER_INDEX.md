# NEXUS V3.5.0 - Master Index

> **Tüm dokümantasyon, script'ler ve rehberler için ana indeks**

---

## 📚 Dokümantasyon Dosyaları

| Dosya | Açıklama | Kimler İçin |
|-------|----------|------------|
| **README.md** | Ana projeREADME | Herkes |
| **README_TR.md** | Türkçe dokümantasyon | Türkçe konuşanlar |
| **NEXUS_PROJECT_DOCUMENTATION.md** | Teknik detaylar | Geliştiriciler |
| **QUICK_START_GUIDE.md** | 5 dakikabaşlangıç | Yeni kullanıcılar |
| **INTEGRATION_GUIDE.md** | Her projeye entegrasyon | Proje sahipleri |
| **CLAUDE_ZAI_QUALITY_PROFILE.md** | Kalite profili | Claude Code kullanıcıları |
| **EVIDENCE_BASELINE.md** | Önce durum kanıtları | Test edecekler |
| **EVIDENCE_AFTER.md** | Sonra durum kanıtları | Test edecekler |
| **CHANGELOG.md** | Sürüm geçmişi | Versiyon takibi |

---

## 🔧 Script'ler ve Araçlar

| Script | Konum | Açıklama |
|--------|-------|----------|
| **Integration Test** | `scripts/nexus_integration_test.sh` | 7/7 test çalıştırır |
| **New Project Setup** | `scripts/new_project_setup.sh` | Yeni proje oluşturur |
| **Install to Claude** | `scripts/install_to_claude.sh` | ~/.claude'a kurar |
| **NEXUS CLI** | `~/.claude/nexus_cli.py` | Task/fix/status komutları |
| **Quality Report** | `~/.claude/generate_quality_report.py` | Kalite skoru üretir |
| **Agent Runtime** | `~/.claude/agent_runtime.py` | Multi-agent runtime |

---

## 🎯 Hızlı Başlangıç Senaryoları

### Senaryo 1: Yeni Python Projesi

```bash
# 1. Proje oluştur
./new_project_setup.sh my-python-app python

# 2. Proje dizinine git
cd my-python-app

# 3. İlk görev başlat
nexus task start "Proje kurulumu"

# 4. Kod yaz...

# 5. Görevi bitir
nexus task close --success
```

### Senaryo 2: Mevcut Projeye Kalite Ekleme

```bash
cd existing-project

# .claude dizini oluştur
mkdir -p .claude

# QUALITY.md kopyala
cp ~/.claude/CLAUDE_ZAI_QUALITY_PROFILE.md .claude/QUALITY.md

# settings.local.json oluştur
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
  }
}
EOF

# Test et
nexus status
```

### Senaryo 3: Kalite Raporu Oluşturma

```bash
# Rapor çalıştır
python3 ~/.claude/generate_quality_report.py

# Sonuçları gör
cat ~/.claude/state/quality_report.json | jq '{
  quality_score,
  tasks_completed,
  incidents_total
}'
```

### Senaryo 4: Integration Test Çalıştırma

```bash
# Tüm testler
./scripts/nexus_integration_test.sh

# Sadece S1 (Quality Gate)
./scripts/nexus_integration_test.sh --scenario S1

# Sadece S3 (Task Metrics)
./scripts/nexus_integration_test.sh --scenario S3
```

---

## 📊 Günlük Kullanım Komutları

### Sabah

```bash
# NEXUS durumu
nexus status

# Yeni gün, yeni görev
nexus task start "Günlük planlama"
```

### Kodlama Sırası

```bash
# Quality gate otomatik çalışır (PostToolUse hook)
# Hata varsa → Rollback → Incident → Fix task
# Hata yoksa → Pass → Progress
```

### Gün Sonu

```bash
# Görevi kapat
nexus task close --success --note "Gün tamamlandı"

# Kalite raporu
python3 ~/.claude/generate_quality_report.py

# Fix queue kontrol
nexus fix stats
```

---

## 🔍 State Dosyaları

| Dosya | Konum | İçeriği |
|-------|-------|---------|
| **Performance Metrics** | `~/.claude/state/performance_metrics.json` | runs, rollbacks, tasks_completed |
| **Learning Patterns** | `~/.claude/state/learning_patterns.json` | 157 pattern, 29 tip |
| **Incidents** | `~/.claude/state/incidents.jsonl` | 9 incident kaydı |
| **Fix Queue** | `~/.claude/state/fix_queue.jsonl` | 11 fix task |
| **Tasks** | `~/.claude/state/tasks.jsonl` | Görev yaşam döngüsü |
| **MSV** | `~/.claude/state/msv.json` | Meta-bilişsel durum vektörü |
| **Mental Model** | `~/.claude/state/mental_model.json` | Proje bilgisi |
| **Quality Report** | `~/.claude/state/quality_report.json` | Kalite skoru |

---

## 🎓 Öğrenme Kaynakları

### Konu Başına Göre Dokümantasyon

| Konu | Dokümantasyon |
|------|---------------|
| **Sistem nedir?** | README.md, NEXUS_PROJECT_DOCUMENTATION.md |
| **Nasıl kurulum?** | QUICK_START_GUIDE.md |
| **Her projeye nasıl?** | INTEGRATION_GUIDE.md |
| **Kalite profili** | CLAUDE_ZAI_QUALITY_PROFILE.md |
| **Test sonuçları** | EVIDENCE_*.md |
| **Türkçe bilgi** | README_TR.md |
| **Sürüm geçmişi** | CHANGELOG.md |

### Beceri Seviyesine Göre

| Seviye | Başla |
|--------|-------|
| **Yeni başlayan** | QUICK_START_GUIDE.md |
| **Orta seviye** | INTEGRATION_GUIDE.md |
| **İleri seviye** | NEXUS_PROJECT_DOCUMENTATION.md |
| **Test edecekler** | scripts/nexus_integration_test.sh |

---

## 🔧 Troubleshooting

| Sorun | Çözüm | Dokümantasyon |
|-------|--------|---------------|
| **Quality gate çalışmıyor** | Hook yolunu kontrol et | INTEGRATION_GUIDE.md → Sorun Giderme |
| **Task CLI hata veriyor** | Python script mi kontrol et | INTEGRATION_GUIDE.md → Sorun Giderme |
| **Test başarısız** | Prerequisites kontrol et | scripts/nexus_integration_test.sh |
| **Pattern learning boş** | Hook chain sırası | NEXUS_PROJECT_DOCUMENTATION.md |

---

## 📈 Kalite Skoru Bileşenleri

```
┌─────────────────────────────────────────┐
│         NEXUS Kalite Skoru              │
├─────────────────────────────────────────┤
│ State Persistence    20/20  ██████████ │
│ Pattern Learning     20/20  ██████████ │
│ Agent Communication  15/15  ██████████ │
│ Quality Gate         20/20  ██████████ │
│ Task Execution       15/15  ██████████ │
│ Self-Healing         10/10  ██████████ │
├─────────────────────────────────────────┤
│ TOTAL               100/100  ██████████ │
└─────────────────────────────────────────┘
```

---

## 🚀 Önerilen Akış

### İlk Kurulum (Yeni Bilgisayar)

```bash
# 1. Repo'yu klonla
git clone https://github.com/turtir-ai/nexus-v3-5.git
cd nexus-v3-5

# 2. Kur
bash scripts/install_to_claude.sh

# 3. Test
python3 ~/.claude/tests/run_all.py
./scripts/nexus_integration_test.sh
```

### Her Yeni Proje

```bash
# 1. Proje oluştur
./new_project_setup.sh my-project python

# 2. Başla
cd my-project
nexus task start "İlk görev"
```

### Haftalık Bakım

```bash
# 1. Kalite raporu
python3 ~/.claude/generate_quality_report.py

# 2. Pattern review
cat ~/.claude/state/learning_patterns.json | jq '.patterns | keys'

# 3. Fix queue temizliği
nexus fix stats
nexus fix process-one
```

---

## 📞 Destek

| Konu | Kaynak |
|------|--------|
| **GitHub Issues** | https://github.com/turtir-ai/nexus-v3-5/issues |
| **E-posta** | tncrtimur@gmail.com |
| **Z.ai Güvenlik** | tcsec@aminer.cn |

---

## 📝 Özet

NEXUS V3.5.0 = **Kalite First + Kanıt Tabanlı** AI coding framework

- ✅ 100/100 kalite skoru
- ✅ 7/7 integration test passing
- ✅ 157 pattern öğrenildi
- ✅ 9 incident, 11 fix task
- ✅ 5 dakikada yeni proje kurulumu

**Ana felsefe:** "Eğer bir şey 'çalışıyor' deniyorsa, kanıt göstermek zorundasın."

---

**Son güncelleme:** 2026-02-09
**Sürüm:** 3.5.0
**Durum:** Production Ready ✅
